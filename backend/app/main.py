from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.agents.executor import ResearchExecutor
from app.agents.planner import ResearchPlanner
from app.agents.synthesizer import ResearchSynthesizer
from app.agents.evaluator import ResearchEvaluator
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.memory.research_memory import ResearchMemory
from app.models.research_run import ResearchRun
from app.schemas.research import (
    CitationsResponse,
    Evaluation,
    ExecutionStep,
    Observation,
    ResearchRequest,
    ResearchResponse,
    ResearchRunListResponse,
    ResearchRunSummary,
    ResearchTask,
    Source,
)
from app.services.citations import CitationFormatter
from app.services.llm import LLMClient, LLMError
from app.services.research_cleanup import ResearchCleanupService
from app.tools.scrape_page import ScrapePageTool
from app.tools.search_web import SearchWebTool


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

allowed_origins = [origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_research_response(run: ResearchRun) -> ResearchResponse:
    return ResearchResponse(
        research_id=run.id,
        query=run.query,
        plan=[ResearchTask.model_validate(item) for item in run.plan],
        steps=[ExecutionStep.model_validate(item) for item in run.steps],
        sources=[Source.model_validate(item) for item in run.sources],
        observations=[Observation.model_validate(item) for item in run.observations],
        answer=run.answer,
        evaluation=Evaluation.model_validate(run.evaluation),
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest, db: Session = Depends(get_db)) -> ResearchResponse:
    llm = LLMClient()
    memory = ResearchMemory()
    cleanup = ResearchCleanupService()
    steps: list[ExecutionStep] = []

    planner = ResearchPlanner(llm=llm)
    executor = ResearchExecutor(
        tools={
            "search_web": SearchWebTool(),
            "scrape_page": ScrapePageTool(),
        },
        memory=memory,
    )
    synthesizer = ResearchSynthesizer(llm=llm)
    evaluator = ResearchEvaluator(llm=llm)

    try:
        plan = await planner.create_plan(request.query, max_tasks=request.max_tasks)
        steps.append(
            ExecutionStep(
                name="planning",
                status="completed",
                detail=f"Created {len(plan.tasks)} research tasks.",
            )
        )
    except LLMError as error:
        plan = ResearchPlanner.fallback_plan(request.query, request.max_tasks)
        steps.append(
            ExecutionStep(
                name="planning",
                status="failed",
                detail=f"Planner LLM call failed; used heuristic plan instead. {error}",
            )
        )

    raw_observations = await executor.execute(plan.tasks)
    failed_tools = sum(1 for obs in raw_observations if obs.metadata.get("error"))
    steps.append(
        ExecutionStep(
            name="tool_execution",
            status="failed" if failed_tools else "completed",
            detail=(
                f"Executed {len(raw_observations)} tool calls"
                + (f" ({failed_tools} failed)." if failed_tools else ".")
            ),
        )
    )

    observations, sources = cleanup.clean_observations(raw_observations)
    steps.append(
        ExecutionStep(
            name="cleanup",
            status="completed",
            detail=f"Normalized {len(sources)} unique sources and assigned citations.",
        )
    )

    try:
        answer = await synthesizer.create_answer(
            request.query,
            observations,
            citation_context=cleanup.citation_context(sources),
        )
        steps.append(
            ExecutionStep(
                name="synthesis",
                status="completed",
                detail="Generated a cited research answer from cleaned evidence.",
            )
        )
    except LLMError as error:
        answer = (
            "Synthesis could not be completed because the language model call failed. "
            "The gathered sources above are still valid; see the synthesis step detail "
            "for the underlying cause."
        )
        steps.append(
            ExecutionStep(
                name="synthesis",
                status="failed",
                detail=f"Synthesis LLM call failed: {error}",
            )
        )

    try:
        evaluation = await evaluator.evaluate(request.query, answer, observations)
        steps.append(
            ExecutionStep(
                name="evaluation",
                status="completed",
                detail=f"Support check completed with {evaluation.confidence} confidence.",
            )
        )
    except LLMError as error:
        evaluation = ResearchEvaluator.fallback_evaluation(observations)
        steps.append(
            ExecutionStep(
                name="evaluation",
                status="failed",
                detail=f"Evaluator LLM call failed; used heuristic evaluation instead. {error}",
            )
        )

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
    return response


@app.get("/research", response_model=ResearchRunListResponse)
def list_research_runs(limit: int = 20, db: Session = Depends(get_db)) -> ResearchRunListResponse:
    safe_limit = min(max(limit, 1), 100)
    runs = db.query(ResearchRun).order_by(ResearchRun.created_at.desc()).limit(safe_limit).all()
    return ResearchRunListResponse(
        items=[
            ResearchRunSummary(
                research_id=run.id,
                query=run.query,
                created_at=run.created_at,
            )
            for run in runs
        ]
    )


@app.get("/research/{research_id}", response_model=ResearchResponse)
def get_research_run(research_id: int, db: Session = Depends(get_db)) -> ResearchResponse:
    run = db.query(ResearchRun).filter(ResearchRun.id == research_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found")
    return _to_research_response(run)


@app.get("/research/{research_id}/citations", response_model=CitationsResponse)
def get_research_citations(research_id: int, db: Session = Depends(get_db)) -> CitationsResponse:
    run = db.query(ResearchRun).filter(ResearchRun.id == research_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found")

    sources = [Source.model_validate(item) for item in run.sources]
    formatter = CitationFormatter()
    return CitationsResponse(
        research_id=run.id,
        accessed=formatter.accessed.isoformat(),
        styles=formatter.format_all(sources),
    )
