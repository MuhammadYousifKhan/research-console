import httpx

from app.core.config import settings
from app.schemas.research import Observation, ResearchTask, Source


class SearchWebTool:
    async def run(self, task: ResearchTask) -> Observation:
        if not settings.tavily_api_key:
            source = Source(
                title="Search tool not configured",
                url="https://docs.tavily.com/",
                snippet="Add TAVILY_API_KEY to enable live web search.",
                reliability="unknown",
            )
            return Observation(
                task_id=task.id,
                task=task.description,
                tool=task.tool,
                result=f"Search skipped for '{task.input}' because TAVILY_API_KEY is missing.",
                sources=[source],
            )

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": task.input,
                    "search_depth": "basic",
                    "max_results": 5,
                },
            )
            response.raise_for_status()
            data = response.json()

        sources = [
            Source(
                title=item.get("title", "Untitled"),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                reliability="unknown",
            )
            for item in data.get("results", [])
            if item.get("url")
        ]
        result = "\n".join(f"- {source.title}: {source.snippet}" for source in sources)
        return Observation(
            task_id=task.id,
            task=task.description,
            tool=task.tool,
            result=result or "No search results found.",
            sources=sources,
            metadata={"query": task.input},
        )
