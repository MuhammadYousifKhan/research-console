import httpx
from bs4 import BeautifulSoup

from app.schemas.research import Observation, ResearchTask, Source


class ScrapePageTool:
    async def run(self, task: ResearchTask) -> Observation:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(task.input)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else task.input
        paragraphs = [
            paragraph.get_text(" ", strip=True)
            for paragraph in soup.find_all("p")
        ]
        content = " ".join(paragraphs)[:3000]
        source = Source(title=title, url=task.input, snippet=content[:300], reliability="unknown")

        return Observation(
            task_id=task.id,
            task=task.description,
            tool=task.tool,
            result=content or "No readable page text found.",
            sources=[source],
            metadata={"url": task.input},
        )
