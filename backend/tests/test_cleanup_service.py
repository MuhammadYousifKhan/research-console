from app.schemas.research import Observation, Source
from app.services.research_cleanup import ResearchCleanupService


def test_clean_observations_deduplicates_sources_and_assigns_citations():
    service = ResearchCleanupService()
    source_a = Source(
        title="NIH Overview",
        url="https://www.nih.gov/health-information",
        snippet="AI improves diagnosis and workflow efficiency.",
    )
    source_b = Source(
        title="Duplicate NIH Overview",
        url="https://www.nih.gov/health-information",
        snippet="Duplicate snippet should map to same citation.",
    )
    source_c = Source(
        title="University report",
        url="https://example.edu/research/ai-healthcare",
        snippet="University analysis on clinical outcomes.",
    )

    observations = [
        Observation(task_id=1, task="task-1", tool="search_web", result="raw-1", sources=[source_a, source_c]),
        Observation(task_id=2, task="task-2", tool="search_web", result="raw-2", sources=[source_b]),
    ]

    cleaned_observations, numbered_sources = service.clean_observations(observations)

    assert len(numbered_sources) == 2
    assert numbered_sources[0].citation_id == 1
    assert numbered_sources[1].citation_id == 2
    assert all(source.reliability in {"high", "medium", "low", "unknown"} for source in numbered_sources)

    first_observation_citations = {source.citation_id for source in cleaned_observations[0].sources}
    second_observation_citations = {source.citation_id for source in cleaned_observations[1].sources}

    assert 1 in first_observation_citations
    assert 1 in second_observation_citations
    assert cleaned_observations[0].result.startswith("- [")


def test_classify_source_uses_domain_reliability():
    service = ResearchCleanupService()

    assert service.classify_source("https://www.cdc.gov/some-report") == ("government", "high")
    assert service.classify_source("https://research.example.edu/paper") == ("academic", "high")
    assert service.classify_source("https://www.reuters.com/world") == ("news", "medium")
    assert service.classify_source("https://insights.substack.com/p/health") == ("news", "low")
    assert service.classify_source("not-a-valid-url") == ("unknown", "unknown")
