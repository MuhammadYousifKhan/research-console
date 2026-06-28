import asyncio

from app.memory.research_memory import ResearchMemory
from app.schemas.research import Observation, ResearchTask


class ResearchExecutor:
    def __init__(self, tools: dict[str, object], memory: ResearchMemory) -> None:
        self.tools = tools
        self.memory = memory

    async def execute(self, tasks: list[ResearchTask]) -> list[Observation]:
        # Run all tool calls concurrently. asyncio.gather preserves input order,
        # so observations line up with their tasks regardless of finish order.
        observations = await asyncio.gather(*(self._run_one(task) for task in tasks))

        # Record into memory in deterministic task order, after all calls resolve.
        for observation in observations:
            self.memory.add_observation(observation)

        return list(observations)

    async def _run_one(self, task: ResearchTask) -> Observation:
        tool = self.tools.get(task.tool)
        if tool is None:
            return Observation(
                task_id=task.id,
                task=task.description,
                tool=task.tool,
                result=f"Tool not found: {task.tool}",
                metadata={"error": f"unknown tool '{task.tool}'"},
            )
        try:
            return await tool.run(task)
        except Exception as error:
            # A single tool failure (timeout, 4xx/5xx, bad URL) must not abort
            # the whole research run — record it and move on.
            return Observation(
                task_id=task.id,
                task=task.description,
                tool=task.tool,
                result=f"Tool '{task.tool}' failed for input {task.input!r}: {error}",
                metadata={"error": f"{type(error).__name__}: {error}"},
            )
