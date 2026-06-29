import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.models.research_run import ResearchRun
from app.schemas.research import (
    CitationsResponse,
    Evaluation,
    ExecutionStep,
    Observation,
    ResearchRequest,
    ResearchResponse,
    ResearchRunListResponse,
    ResearchRunSummary,
    ResearchTask,
    Source,
)
from app.services.citations import CitationFormatter
from app.services.pipeline import run_research_pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

allowed_origins = [origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_research_response(run: ResearchRun) -> ResearchResponse:
    return ResearchResponse(
        research_id=run.id,
        query=run.query,
        plan=[ResearchTask.model_validate(item) for item in run.plan],
        steps=[ExecutionStep.model_validate(item) for item in run.steps],
        sources=[Source.model_validate(item) for item in run.sources],
        observations=[Observation.model_validate(item) for item in run.observations],
        answer=run.answer,
        evaluation=Evaluation.model_validate(run.evaluation),
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest, db: Session = Depends(get_db)) -> ResearchResponse:
    # Drain the shared pipeline; the streaming endpoint forwards the same events.
    final: ResearchResponse | None = None
    async for event in run_research_pipeline(request, db):
        if event["type"] == "complete":
            final = event["run"]
    assert final is not None  # the generator always ends with a "complete" event
    return final


@app.post("/research/stream")
async def research_stream(request: ResearchRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    """Run the pipeline and stream each stage as Server-Sent Events.

    Emits `data: {"type":"step", "step":{...}}` per stage, a final
    `data: {"type":"complete", "run":{...}}`, or `{"type":"error"}` on an
    unexpected failure. Clients should stop reading after `complete`/`error`.
    """

    async def event_stream():
        try:
            async for event in run_research_pipeline(request, db):
                if event["type"] == "step":
                    payload = {"type": "step", "step": event["step"].model_dump()}
                else:
                    payload = {"type": "complete", "run": event["run"].model_dump(mode="json")}
                yield f"data: {json.dumps(payload)}\n\n"
        except Exception as error:  # pragma: no cover - defensive; pipeline is failure-isolated
            payload = {"type": "error", "message": f"{type(error).__name__}: {error}"}
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/research", response_model=ResearchRunListResponse)
def list_research_runs(limit: int = 20, db: Session = Depends(get_db)) -> ResearchRunListResponse:
    safe_limit = min(max(limit, 1), 100)
    runs = db.query(ResearchRun).order_by(ResearchRun.created_at.desc()).limit(safe_limit).all()
    return ResearchRunListResponse(
        items=[
            ResearchRunSummary(
                research_id=run.id,
                query=run.query,
                created_at=run.created_at,
            )
            for run in runs
        ]
    )


@app.get("/research/{research_id}", response_model=ResearchResponse)
def get_research_run(research_id: int, db: Session = Depends(get_db)) -> ResearchResponse:
    run = db.query(ResearchRun).filter(ResearchRun.id == research_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found")
    return _to_research_response(run)


@app.get("/research/{research_id}/citations", response_model=CitationsResponse)
def get_research_citations(research_id: int, db: Session = Depends(get_db)) -> CitationsResponse:
    run = db.query(ResearchRun).filter(ResearchRun.id == research_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found")

    sources = [Source.model_validate(item) for item in run.sources]
    formatter = CitationFormatter()
    return CitationsResponse(
        research_id=run.id,
        accessed=formatter.accessed.isoformat(),
        styles=formatter.format_all(sources),
    )
