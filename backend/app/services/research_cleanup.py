import re
from urllib.parse import urlparse

from app.schemas.research import Observation, Source


class ResearchCleanupService:
    def clean_observations(self, observations: list[Observation]) -> tuple[list[Observation], list[Source]]:
        cleaned_observations: list[Observation] = []
        sources_by_url: dict[str, Source] = {}

        for observation in observations:
            cleaned_sources = [self.clean_source(source) for source in observation.sources]
            for source in cleaned_sources:
                if source.url and source.url not in sources_by_url:
                    sources_by_url[source.url] = source

            cleaned_result = self.build_observation_result(cleaned_sources, observation.result)
            cleaned_observations.append(
                observation.model_copy(
                    update={
                        "result": cleaned_result,
                        "sources": cleaned_sources,
                    }
                )
            )

        numbered_sources = []
        for citation_id, source in enumerate(sources_by_url.values(), start=1):
            numbered_sources.append(source.model_copy(update={"citation_id": citation_id}))

        citation_by_url = {source.url: source.citation_id for source in numbered_sources}
        final_observations = []
        for observation in cleaned_observations:
            numbered_observation_sources = [
                source.model_copy(update={"citation_id": citation_by_url.get(source.url)})
                for source in observation.sources
            ]
            final_observations.append(
                observation.model_copy(
                    update={
                        "sources": numbered_observation_sources,
                        "result": self.build_observation_result(
                            numbered_observation_sources,
                            observation.result,
                        ),
                    }
                )
            )

        return final_observations, numbered_sources

    def citation_context(self, sources: list[Source]) -> str:
        lines = []
        for source in sources:
            lines.append(
                f"[{source.citation_id}] {source.title}\n"
                f"URL: {source.url}\n"
                f"Reliability: {source.reliability}\n"
                f"Evidence: {source.snippet}"
            )
        return "\n\n".join(lines)

    def clean_source(self, source: Source) -> Source:
        title = self.clean_text(source.title, limit=140)
        snippet = self.clean_text(source.snippet, limit=500)
        source_type, reliability = self.classify_source(source.url)
        return source.model_copy(
            update={
                "title": title or "Untitled source",
                "snippet": snippet,
                "source_type": source_type,
                "reliability": reliability,
            }
        )

    def build_observation_result(self, sources: list[Source], fallback: str) -> str:
        if not sources:
            return self.clean_text(fallback, limit=1200)

        lines = []
        for source in sources:
            prefix = f"[{source.citation_id}] " if source.citation_id else ""
            lines.append(f"- {prefix}{source.title}: {source.snippet}")
        return "\n".join(lines)

    def clean_text(self, text: str, limit: int) -> str:
        cleaned = text or ""
        cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", cleaned)
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
        cleaned = re.sub(r"https?://\S+", " ", cleaned)
        cleaned = re.sub(r"\*\*|__|`|#+", " ", cleaned)
        cleaned = re.sub(r"\b(Image|Cookie|Maximum Storage Duration|Type):?\b.*", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if len(cleaned) <= limit:
            return cleaned

        truncated = cleaned[:limit].rsplit(" ", 1)[0].strip()
        return f"{truncated}..."

    def classify_source(self, url: str) -> tuple[str, str]:
        domain = urlparse(url).netloc.lower()
        if not domain:
            return "unknown", "unknown"

        trusted_government_domains = [
            "nih.gov",
            "ncbi.nlm.nih.gov",
            "who.int",
            "fda.gov",
            "cdc.gov",
            "europa.eu",
            "data.gov",
        ]
        trusted_academic_domains = [
            "nature.com",
            "sciencedirect.com",
            "springer.com",
            "thelancet.com",
            "nejm.org",
            "jamanetwork.com",
            "arxiv.org",
            "frontiersin.org",
            "ieee.org",
            "acm.org",
        ]
        institutional_organization_domains = [
            "oecd.org",
            "worldbank.org",
            "weforum.org",
            "un.org",
            "wto.org",
            "imf.org",
            "aha.org",
        ]
        major_news_domains = [
            "reuters.com",
            "apnews.com",
            "bbc.com",
            "wsj.com",
            "nytimes.com",
            "economist.com",
            "ft.com",
        ]
        commercial_industry_domains = [
            "bcg.com",
            "mckinsey.com",
            "deloitte.com",
            "gartner.com",
            "forrester.com",
            "menlovc.com",
        ]

        if any(part in domain for part in trusted_government_domains):
            return "government", "high"

        if domain.endswith(".gov"):
            return "government", "high"
        if domain.endswith(".edu"):
            return "academic", "high"
        if any(part in domain for part in trusted_academic_domains):
            return "academic", "high"

        if any(part in domain for part in institutional_organization_domains):
            return "organization", "high"
        if domain.endswith(".org"):
            return "organization", "medium"

        if any(part in domain for part in commercial_industry_domains):
            return "industry", "medium"
        if any(part in domain for part in major_news_domains):
            return "news", "medium"
        if any(part in domain for part in ["magazine", "dive.com", "news", "blog", "substack"]):
            return "news", "low"

        if domain.endswith(".com"):
            return "news", "medium"

        return "unknown", "unknown"
