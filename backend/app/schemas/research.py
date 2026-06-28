from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    query: str = Field(min_length=3)
    max_tasks: int = Field(default=4, ge=1, le=8)


class ResearchTask(BaseModel):
    id: int
    description: str
    tool: Literal["search_web", "scrape_page", "search_arxiv", "search_scholar"]
    input: str
    priority: Literal["low", "medium", "high"] = "medium"


class ResearchPlan(BaseModel):
    tasks: list[ResearchTask]


class Source(BaseModel):
    citation_id: int | None = None
    title: str
    url: str
    snippet: str = ""
    reliability: Literal["unknown", "low", "medium", "high"] = "unknown"
    source_type: Literal["academic", "government", "industry", "news", "organization", "unknown"] = "unknown"


class Observation(BaseModel):
    task_id: int
    task: str
    tool: str
    result: str
    sources: list[Source] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Evaluation(BaseModel):
    is_supported: bool
    confidence: Literal["low", "medium", "high"]
    missing_evidence: list[str] = Field(default_factory=list)
    notes: str = ""


class ExecutionStep(BaseModel):
    name: str
    status: Literal["completed", "failed"]
    detail: str


class ResearchResponse(BaseModel):
    research_id: int | None = None
    query: str
    plan: list[ResearchTask]
    steps: list[ExecutionStep]
    sources: list[Source]
    observations: list[Observation]
    answer: str
    evaluation: Evaluation


class ResearchRunSummary(BaseModel):
    research_id: int
    query: str
    created_at: datetime


class ResearchRunListResponse(BaseModel):
    items: list[ResearchRunSummary]


CitationStyle = Literal["apa", "mla", "ieee", "harvard", "chicago", "bibtex"]


class CitationItem(BaseModel):
    citation_id: int | None = None
    title: str
    url: str = ""
    text: str


class CitationsResponse(BaseModel):
    research_id: int
    accessed: str
    styles: dict[CitationStyle, list[CitationItem]]
