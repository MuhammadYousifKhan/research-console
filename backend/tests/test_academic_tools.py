import httpx
import pytest

from app.schemas.research import ResearchTask
from app.tools.search_arxiv import SearchArxivTool
from app.tools.search_scholar import SearchScholarTool

ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on attention.</summary>
    <published>2017-06-12T17:57:34Z</published>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
  </entry>
</feed>
"""

SCHOLAR_JSON = {
    "data": [
        {
            "title": "Attention Is All You Need",
            "abstract": "We propose the Transformer, based solely on attention.",
            "year": 2017,
            "url": "https://www.semanticscholar.org/paper/abc123",
            "authors": [{"name": "Ashish Vaswani"}, {"name": "Noam Shazeer"}],
            "externalIds": {"DOI": "10.5555/3295222.3295349"},
        }
    ]
}


def _task(tool: str) -> ResearchTask:
    return ResearchTask(id=1, description="d", tool=tool, input="attention", priority="high")


def _patch_get(monkeypatch, response: httpx.Response) -> None:
    async def fake_get(self, url, params=None):
        return response

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)


@pytest.mark.asyncio
async def test_arxiv_parses_papers(monkeypatch):
    _patch_get(monkeypatch, httpx.Response(200, text=ARXIV_FEED, request=httpx.Request("GET", "https://x")))

    observation = await SearchArxivTool().run(_task("search_arxiv"))

    assert len(observation.sources) == 1
    source = observation.sources[0]
    assert source.title == "Attention Is All You Need"
    assert source.url == "http://arxiv.org/abs/1706.03762v5"
    assert source.source_type == "academic"
    assert source.reliability == "high"
    assert "Ashish Vaswani" in source.snippet
    assert "2017" in source.snippet
    assert observation.metadata["provider"] == "arxiv"


@pytest.mark.asyncio
async def test_arxiv_reports_empty_results(monkeypatch):
    empty = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    _patch_get(monkeypatch, httpx.Response(200, text=empty, request=httpx.Request("GET", "https://x")))

    observation = await SearchArxivTool().run(_task("search_arxiv"))

    assert observation.sources == []
    assert "No arXiv papers found" in observation.result


@pytest.mark.asyncio
async def test_scholar_parses_papers(monkeypatch):
    _patch_get(monkeypatch, httpx.Response(200, json=SCHOLAR_JSON, request=httpx.Request("GET", "https://x")))

    observation = await SearchScholarTool().run(_task("search_scholar"))

    assert len(observation.sources) == 1
    source = observation.sources[0]
    assert source.source_type == "academic"
    assert source.reliability == "high"
    assert source.url == "https://www.semanticscholar.org/paper/abc123"
    assert "Ashish Vaswani" in source.snippet
    assert "2017" in source.snippet


@pytest.mark.asyncio
async def test_scholar_handles_rate_limit_honestly(monkeypatch):
    _patch_get(monkeypatch, httpx.Response(429, request=httpx.Request("GET", "https://x")))

    observation = await SearchScholarTool().run(_task("search_scholar"))

    assert observation.sources == []
    assert "rate_limited" in observation.metadata["error"]
    assert "rate limit" in observation.result.lower()
