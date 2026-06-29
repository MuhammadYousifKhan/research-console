import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.evaluator import ResearchEvaluator
from app.agents.executor import ResearchExecutor
from app.agents.planner import ResearchPlanner
from app.agents.synthesizer import ResearchSynthesizer
from app.core.config import settings
from app.core.database import Base, get_db
from app.models.research_run import ResearchRun
from app.schemas.research import Evaluation, Observation, ResearchPlan, ResearchTask, Source


def _parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.strip().split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data:"):
                events.append(json.loads(line[5:].strip()))
    return events


def test_research_stream_emits_steps_then_complete(tmp_path, monkeypatch):
    assert ResearchRun is not None  # ensure the model is registered before create_all
    db_file = tmp_path / "test_stream.db"
    test_engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    from app import main as main_module

    main_module.engine = test_engine

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def fake_create_plan(self, query, max_tasks):
        return ResearchPlan(
            tasks=[ResearchTask(id=1, description=f"research {query}", tool="search_web", input=query, priority="high")]
        )

    async def fake_execute(self, tasks):
        task = tasks[0]
        return [
            Observation(
                task_id=task.id,
                task=task.description,
                tool=task.tool,
                result="Evidence [1]",
                sources=[Source(title="CDC", url="https://www.cdc.gov/x", snippet="evidence")],
            )
        ]

    async def fake_create_answer(self, query, observations, citation_context="", evidence_text=None):
        return "Answer [1]"

    async def fake_evaluate(self, query, answer, observations):
        return Evaluation(is_supported=True, confidence="high", missing_evidence=[], notes="ok")

    # Keep the test hermetic: skip the real Chroma index / embedding-model download.
    monkeypatch.setattr(settings, "rag_enabled", False)
    monkeypatch.setattr(ResearchPlanner, "create_plan", fake_create_plan)
    monkeypatch.setattr(ResearchExecutor, "execute", fake_execute)
    monkeypatch.setattr(ResearchSynthesizer, "create_answer", fake_create_answer)
    monkeypatch.setattr(ResearchEvaluator, "evaluate", fake_evaluate)

    main_module.app.dependency_overrides[get_db] = override_get_db
    client = TestClient(main_module.app)

    try:
        response = client.post("/research/stream", json={"query": "AI in healthcare", "max_tasks": 1})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        events = _parse_sse(response.text)
        step_names = [e["step"]["name"] for e in events if e["type"] == "step"]
        assert step_names == [
            "planning",
            "tool_execution",
            "cleanup",
            "retrieval",
            "synthesis",
            "evaluation",
        ]

        complete = [e for e in events if e["type"] == "complete"]
        assert len(complete) == 1
        run = complete[0]["run"]
        assert run["answer"] == "Answer [1]"
        assert run["research_id"] is not None

        # The streamed run was persisted and is retrievable.
        fetched = client.get(f"/research/{run['research_id']}")
        assert fetched.status_code == 200
    finally:
        main_module.app.dependency_overrides.clear()
