from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.orm import Session

from app.agents.evaluator import ResearchEvaluator
from app.agents.executor import ResearchExecutor
from app.agents.planner import ResearchPlanner
from app.agents.synthesizer import ResearchSynthesizer
from app.memory.research_memory import ResearchMemory
from app.models.research_run import ResearchRun
from app.schemas.research import (
    ExecutionStep,
    ResearchRequest,
    ResearchResponse,
)
from app.services.citations import CitationFormatter  # noqa: F401  (kept for parity / future use)
from app.services.llm import LLMClient, LLMError
from app.services.research_cleanup import ResearchCleanupService
from app.tools.scrape_page import ScrapePageTool
from app.tools.search_arxiv import SearchArxivTool
from app.tools.search_scholar import SearchScholarTool
from app.tools.search_web import SearchWebTool

# Each event is one of:
#   {"type": "step", "step": ExecutionStep}      — emitted as a stage finishes
#   {"type": "complete", "run": ResearchResponse} — final, persisted run
PipelineEvent = dict[str, Any]


def _build_tools() -> dict[str, object]:
    return {
        "search_web": SearchWebTool(),
        "scrape_page": ScrapePageTool(),
        "search_arxiv": SearchArxivTool(),
        "search_scholar": SearchScholarTool(),
    }


async def run_research_pipeline(request: ResearchRequest, db: Session) -> AsyncIterator[PipelineEvent]:
    """Run the full research pipeline, yielding one event per completed stage.

    This is the single source of truth for the pipeline. ``POST /research``
    drains it and returns only the final run; ``POST /research/stream`` forwards
    each event to the client as Server-Sent Events. The honest-state principle
    holds throughout: per-stage failures are emitted as ``failed`` steps rather
    than aborting the run.
    """
    llm = LLMClient()
    memory = ResearchMemory()
    cleanup = ResearchCleanupService()
    steps: list[ExecutionStep] = []

    planner = ResearchPlanner(llm=llm)
    executor = ResearchExecutor(tools=_build_tools(), memory=memory)
    synthesizer = ResearchSynthesizer(llm=llm)
    evaluator = ResearchEvaluator(llm=llm)

    # --- planning -------------------------------------------------------
    try:
        plan = await planner.create_plan(request.query, max_tasks=request.max_tasks)
        step = ExecutionStep(
            name="planning",
            status="completed",
            detail=f"Created {len(plan.tasks)} research tasks.",
        )
    except LLMError as error:
        plan = ResearchPlanner.fallback_plan(request.query, request.max_tasks)
        step = ExecutionStep(
            name="planning",
            status="failed",
            detail=f"Planner LLM call failed; used heuristic plan instead. {error}",
        )
    steps.append(step)
    yield {"type": "step", "step": step}

    # --- tool execution -------------------------------------------------
    raw_observations = await executor.execute(plan.tasks)
    failed_tools = sum(1 for obs in raw_observations if obs.metadata.get("error"))
    step = ExecutionStep(
        name="tool_execution",
        status="failed" if failed_tools else "completed",
        detail=(
            f"Executed {len(raw_observations)} tool calls"
            + (f" ({failed_tools} failed)." if failed_tools else ".")
        ),
    )
    steps.append(step)
    yield {"type": "step", "step": step}

    # --- cleanup --------------------------------------------------------
    observations, sources = cleanup.clean_observations(raw_observations)
    step = ExecutionStep(
        name="cleanup",
        status="completed",
        detail=f"Normalized {len(sources)} unique sources and assigned citations.",
    )
    steps.append(step)
    yield {"type": "step", "step": step}

    # --- synthesis ------------------------------------------------------
    try:
        answer = await synthesizer.create_answer(
            request.query,
            observations,
            citation_context=cleanup.citation_context(sources),
        )
        step = ExecutionStep(
            name="synthesis",
            status="completed",
            detail="Generated a cited research answer from cleaned evidence.",
        )
    except LLMError as error:
        answer = (
            "Synthesis could not be completed because the language model call failed. "
            "The gathered sources above are still valid; see the synthesis step detail "
            "for the underlying cause."
        )
        step = ExecutionStep(
            name="synthesis",
            status="failed",
            detail=f"Synthesis LLM call failed: {error}",
        )
    steps.append(step)
    yield {"type": "step", "step": step}

    # --- evaluation -----------------------------------------------------
    try:
        evaluation = await evaluator.evaluate(request.query, answer, observations)
        step = ExecutionStep(
            name="evaluation",
            status="completed",
            detail=f"Support check completed with {evaluation.confidence} confidence.",
        )
    except LLMError as error:
        evaluation = ResearchEvaluator.fallback_evaluation(observations)
        step = ExecutionStep(
            name="evaluation",
            status="failed",
            detail=f"Evaluator LLM call failed; used heuristic evaluation instead. {error}",
        )
    steps.append(step)
    yield {"type": "step", "step": step}

    # --- persist + final event -----------------------------------------
    response = ResearchResponse(
        query=request.query,
        plan=plan.tasks,
        steps=steps,
        sources=sources,
        observations=observations,
        answer=answer,
        evaluation=evaluation,
    )

    research_run = ResearchRun(
        query=response.query,
        plan=[item.model_dump() for item in response.plan],
        steps=[item.model_dump() for item in response.steps],
        sources=[item.model_dump() for item in response.sources],
        observations=[item.model_dump() for item in response.observations],
        answer=response.answer,
        evaluation=response.evaluation.model_dump(),
    )
    db.add(research_run)
    db.commit()
    db.refresh(research_run)

    response.research_id = research_run.id
    yield {"type": "complete", "run": response}
