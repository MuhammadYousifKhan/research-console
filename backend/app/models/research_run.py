from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy import JSON as JSONType
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    query: Mapped[str] = mapped_column(String(1000), nullable=False)
    plan: Mapped[list[dict]] = mapped_column(JSONType, nullable=False)
    steps: Mapped[list[dict]] = mapped_column(JSONType, nullable=False)
    sources: Mapped[list[dict]] = mapped_column(JSONType, nullable=False)
    observations: Mapped[list[dict]] = mapped_column(JSONType, nullable=False)
    answer: Mapped[str] = mapped_column(String, nullable=False)
    evaluation: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
