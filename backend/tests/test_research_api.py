from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.evaluator import ResearchEvaluator
from app.agents.executor import ResearchExecutor
from app.agents.planner import ResearchPlanner
from app.agents.synthesizer import ResearchSynthesizer
from app.core.database import Base, get_db
from app.models.research_run import ResearchRun
from app.schemas.research import Evaluation, Observation, ResearchPlan, ResearchTask, Source


def test_research_endpoints_persist_and_retrieve_runs(tmp_path, monkeypatch):
    assert ResearchRun is not None
    db_file = tmp_path / "test_research.db"
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
            tasks=[
                ResearchTask(
                    id=1,
                    description=f"research {query}",
                    tool="search_web",
                    input=query,
                    priority="high",
                )
            ]
        )

    async def fake_execute(self, tasks):
        task = tasks[0]
        return [
            Observation(
                task_id=task.id,
                task=task.description,
                tool=task.tool,
                result="Evidence from source [1]",
                sources=[
                    Source(
                        title="CDC report",
                        url="https://www.cdc.gov/ai-healthcare",
                        snippet="AI supports diagnosis and triage.",
                    )
                ],
            )
        ]

    async def fake_create_answer(self, query, observations, citation_context=""):
        return "Summary with evidence [1]"

    async def fake_evaluate(self, query, answer, observations):
        return Evaluation(
            is_supported=True,
            confidence="high",
            missing_evidence=[],
            notes="Looks supported.",
        )

    monkeypatch.setattr(ResearchPlanner, "create_plan", fake_create_plan)
    monkeypatch.setattr(ResearchExecutor, "execute", fake_execute)
    monkeypatch.setattr(ResearchSynthesizer, "create_answer", fake_create_answer)
    monkeypatch.setattr(ResearchEvaluator, "evaluate", fake_evaluate)

    main_module.app.dependency_overrides[get_db] = override_get_db

    client = TestClient(main_module.app)

    try:
        create_response = client.post(
            "/research",
            json={"query": "Impact of AI in healthcare", "max_tasks": 1},
        )
        assert create_response.status_code == 200
        created = create_response.json()
        assert created["research_id"] is not None
        assert created["query"] == "Impact of AI in healthcare"

        research_id = created["research_id"]

        get_response = client.get(f"/research/{research_id}")
        assert get_response.status_code == 200
        retrieved = get_response.json()
        assert retrieved["research_id"] == research_id
        assert retrieved["answer"] == "Summary with evidence [1]"

        list_response = client.get("/research")
        assert list_response.status_code == 200
        items = list_response.json()["items"]
        assert len(items) == 1
        assert items[0]["research_id"] == research_id
        datetime.fromisoformat(items[0]["created_at"])

        missing_response = client.get("/research/999999")
        assert missing_response.status_code == 404
    finally:
        main_module.app.dependency_overrides.clear()
