import httpx

from app.schemas.research import Observation, ResearchTask, Source

# Semantic Scholar's Graph API is free and key-less, but the unauthenticated
# tier is rate-limited (HTTP 429 under load).
SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,authors,year,url,externalIds"
MAX_RESULTS = 5


class SearchScholarTool:
    """Search Semantic Scholar for scholarly papers across disciplines.

    Returns clean JSON with authors and publication year. Honest-state
    principle: rate limiting (429), other API failures, and empty result sets
    are reported explicitly instead of being treated as success.
    """

    async def run(self, task: ResearchTask) -> Observation:
        params = {"query": task.input, "limit": MAX_RESULTS, "fields": FIELDS}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(SCHOLAR_API_URL, params=params)

        if response.status_code == 429:
            return self._empty(
                task,
                f"Semantic Scholar rate limit hit for '{task.input}'; no results retrieved.",
                error="rate_limited (HTTP 429)",
            )
        response.raise_for_status()
        data = response.json()

        sources: list[Source] = []
        for paper in data.get("data", []):
            url = paper.get("url") or self._doi_url(paper)
            if not url:
                continue
            authors = [author.get("name", "") for author in paper.get("authors", []) if author.get("name")]
            year = str(paper.get("year") or "")
            abstract = " ".join((paper.get("abstract") or "").split())
            author_label = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
            sources.append(
                Source(
                    title=paper.get("title") or "Untitled",
                    url=url,
                    snippet=" — ".join(part for part in (author_label, year, abstract) if part),
                    reliability="high",
                    source_type="academic",
                )
            )

        result = "\n".join(f"- {source.title}: {source.snippet}" for source in sources)
        return Observation(
            task_id=task.id,
            task=task.description,
            tool=task.tool,
            result=result or f"No Semantic Scholar papers found for '{task.input}'.",
            sources=sources,
            metadata={"query": task.input, "provider": "semantic_scholar"},
        )

    def _doi_url(self, paper: dict) -> str:
        doi = (paper.get("externalIds") or {}).get("DOI")
        return f"https://doi.org/{doi}" if doi else ""

    def _empty(self, task: ResearchTask, message: str, error: str) -> Observation:
        return Observation(
            task_id=task.id,
            task=task.description,
            tool=task.tool,
            result=message,
            sources=[],
            metadata={"query": task.input, "provider": "semantic_scholar", "error": error},
        )
