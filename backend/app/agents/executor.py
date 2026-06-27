from app.memory.research_memory import ResearchMemory
from app.schemas.research import Observation, ResearchTask


class ResearchExecutor:
    def __init__(self, tools: dict[str, object], memory: ResearchMemory) -> None:
        self.tools = tools
        self.memory = memory

    async def execute(self, tasks: list[ResearchTask]) -> list[Observation]:
        observations: list[Observation] = []
        for task in tasks:
            tool = self.tools.get(task.tool)
            if tool is None:
                observation = Observation(
                    task_id=task.id,
                    task=task.description,
                    tool=task.tool,
                    result=f"Tool not found: {task.tool}",
                    metadata={"error": f"unknown tool '{task.tool}'"},
                )
            else:
                try:
                    observation = await tool.run(task)
                except Exception as error:
                    # A single tool failure (timeout, 4xx/5xx, bad URL) must not
                    # abort the whole research run — record it and move on.
                    observation = Observation(
                        task_id=task.id,
                        task=task.description,
                        tool=task.tool,
                        result=f"Tool '{task.tool}' failed for input {task.input!r}: {error}",
                        metadata={"error": f"{type(error).__name__}: {error}"},
                    )

            self.memory.add_observation(observation)
            observations.append(observation)

        return observations
