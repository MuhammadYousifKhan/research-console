from pydantic import ValidationError

from app.schemas.research import ResearchPlan
from app.services.llm import LLMClient, LLMError


class ResearchPlanner:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    @staticmethod
    def fallback_plan(query: str, max_tasks: int) -> ResearchPlan:
        tasks = [
            {
                "id": 1,
                "description": f"Find reliable background sources for: {query}",
                "tool": "search_web",
                "input": query,
                "priority": "high",
            },
            {
                "id": 2,
                "description": f"Find risks, limitations, or counterpoints for: {query}",
                "tool": "search_web",
                "input": f"{query} risks limitations criticism",
                "priority": "medium",
            },
        ][:max_tasks]
        return ResearchPlan.model_validate({"tasks": tasks})

    async def create_plan(self, query: str, max_tasks: int) -> ResearchPlan:
        data = await self.llm.complete_json(
            system=(
                "You are a research planning agent. Return strict JSON only. "
                "Create concise tool-ready research tasks.\n"
                "Available tools:\n"
                "- search_web: general web search (use for current events, news, "
                "products, opinions, broad context).\n"
                "- search_arxiv: search arXiv preprints (use for physics, math, CS, "
                "and other technical/scientific topics).\n"
                "- search_scholar: search Semantic Scholar (use for peer-reviewed "
                "academic papers across all disciplines).\n"
                "- scrape_page: fetch a specific URL (input must be a full URL).\n"
                "Prefer search_arxiv and search_scholar for scientific or technical "
                "questions; use search_web for everything else."
            ),
            user=(
                f"Query: {query}\n"
                f"Max tasks: {max_tasks}\n"
                "Return JSON with this shape: "
                '{"tasks":[{"id":1,"description":"...","tool":"search_web",'
                '"input":"...","priority":"high"}]}'
            ),
        )
        try:
            plan = ResearchPlan.model_validate(data)
        except ValidationError as error:
            raise LLMError(f"Planner returned an invalid task structure: {error}") from error

        # Honor the caller's cap even when the model ignores it.
        if len(plan.tasks) > max_tasks:
            plan = ResearchPlan(tasks=plan.tasks[:max_tasks])
        return plan
