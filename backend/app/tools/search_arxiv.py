import httpx
from bs4 import BeautifulSoup

from app.schemas.research import Observation, ResearchTask, Source

# arXiv exposes a free, key-less Atom (XML) search API.
ARXIV_API_URL = "https://export.arxiv.org/api/query"
MAX_RESULTS = 5


class SearchArxivTool:
    """Search arXiv preprints for a query.

    arXiv returns an Atom XML feed, parsed here with bs4's ``xml`` parser
    (lxml) for reliable handling of the namespaced feed. We read the fields we
    need: title, summary, authors, published date, and the abstract URL.

    Honest-state principle: API failures and empty result sets are reported
    explicitly; nothing is fabricated.
    """

    async def run(self, task: ResearchTask) -> Observation:
        params = {
            "search_query": f"all:{task.input}",
            "start": 0,
            "max_results": MAX_RESULTS,
            "sortBy": "relevance",
        }
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(ARXIV_API_URL, params=params)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "xml")
        sources: list[Source] = []
        for entry in soup.find_all("entry"):
            title_tag = entry.find("title")
            summary_tag = entry.find("summary")
            id_tag = entry.find("id")
            url = id_tag.get_text(strip=True) if id_tag else ""
            if not url:
                continue
            authors = [
                name.get_text(strip=True)
                for author in entry.find_all("author")
                if (name := author.find("name")) is not None
            ]
            published = entry.find("published")
            year = published.get_text(strip=True)[:4] if published else ""
            snippet = " ".join((summary_tag.get_text(" ", strip=True) if summary_tag else "").split())
            author_label = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
            sources.append(
                Source(
                    title=title_tag.get_text(" ", strip=True) if title_tag else "Untitled",
                    url=url,
                    snippet=" — ".join(part for part in (author_label, year, snippet) if part),
                    reliability="high",
                    source_type="academic",
                )
            )

        result = "\n".join(f"- {source.title}: {source.snippet}" for source in sources)
        return Observation(
            task_id=task.id,
            task=task.description,
            tool=task.tool,
            result=result or f"No arXiv papers found for '{task.input}'.",
            sources=sources,
            metadata={"query": task.input, "provider": "arxiv"},
        )
