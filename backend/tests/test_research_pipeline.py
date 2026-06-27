import pytest

from app.agents.executor import ResearchExecutor
from app.agents.planner import ResearchPlanner
from app.memory.research_memory import ResearchMemory
from app.schemas.research import Observation, ResearchTask
from app.services.llm import LLMClient, LLMError


def test_fallback_plan_creates_capped_tasks():
    plan = ResearchPlanner.fallback_plan("AI in healthcare", max_tasks=2)

    assert len(plan.tasks) == 2
    assert plan.tasks[0].tool == "search_web"


def test_fallback_plan_respects_max_tasks():
    plan = ResearchPlanner.fallback_plan("AI in healthcare", max_tasks=1)

    assert len(plan.tasks) == 1


@pytest.mark.asyncio
async def test_create_plan_raises_without_api_key():
    client = LLMClient()
    client.api_key = ""  # force the unconfigured path deterministically
    planner = ResearchPlanner(llm=client)

    with pytest.raises(LLMError):
        await planner.create_plan("AI in healthcare", max_tasks=2)


@pytest.mark.asyncio
async def test_executor_records_tool_failure_without_aborting():
    class BoomTool:
        async def run(self, task: ResearchTask) -> Observation:
            raise RuntimeError("network down")

    memory = ResearchMemory()
    executor = ResearchExecutor(tools={"search_web": BoomTool()}, memory=memory)
    task = ResearchTask(
        id=1,
        description="research",
        tool="search_web",
        input="AI in healthcare",
        priority="high",
    )

    observations = await executor.execute([task])

    assert len(observations) == 1
    assert observations[0].metadata.get("error")
    assert "network down" in observations[0].result
    assert len(memory.observations) == 1
