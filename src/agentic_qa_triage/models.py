from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    environment: Mapped[str] = mapped_column(String(300), default="Not provided")
    reporter: Mapped[str] = mapped_column(String(120), default="Portfolio demo")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    source: Mapped[str] = mapped_column(String(30), default="demo")

    severity: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    suspected_component: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reproduction_steps: Mapped[list[str]] = mapped_column(JSON, default=list)
    test_plan: Mapped[list[str]] = mapped_column(JSON, default=list)
    missing_information: Mapped[list[str]] = mapped_column(JSON, default=list)
    similar_incident_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    runs: Mapped[list[AgentRun]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="AgentRun.id.desc()",
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    incident: Mapped[Incident] = relationship(back_populates="runs")


class KnownIncident(Base):
    __tablename__ = "known_incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    symptoms: Mapped[str] = mapped_column(Text)
    component: Mapped[str] = mapped_column(String(150))
    severity: Mapped[str] = mapped_column(String(30))
    resolution: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
