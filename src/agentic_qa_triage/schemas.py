from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["low", "medium", "high", "critical"]
Category = Literal["bug", "performance", "security", "data", "integration", "ux", "unknown"]


class IncidentCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=20, max_length=10_000)
    environment: str = Field(default="Not provided", max_length=300)
    reporter: str = Field(default="Unspecified", max_length=120)


class TriageDecision(BaseModel):
    severity: Severity
    category: Category
    summary: str = Field(min_length=10, max_length=800)
    suspected_component: str = Field(min_length=2, max_length=200)
    reproduction_steps: list[str] = Field(min_length=1, max_length=8)
    test_plan: list[str] = Field(min_length=1, max_length=8)
    missing_information: list[str] = Field(default_factory=list, max_length=8)
    confidence: float = Field(ge=0, le=1)
    similar_incident_ids: list[int] = Field(default_factory=list, max_length=5)


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    model: str
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    tool_calls: int
    duration_ms: int
    estimated_cost_usd: float | None
    created_at: datetime


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    environment: str
    reporter: str
    status: str
    source: str
    severity: str | None
    category: str | None
    summary: str | None
    suspected_component: str | None
    reproduction_steps: list[str]
    test_plan: list[str]
    missing_information: list[str]
    similar_incident_ids: list[int]
    confidence: float | None
    created_at: datetime
    approved_at: datetime | None
    runs: list[AgentRunRead] = Field(default_factory=list)


class TriageResponse(BaseModel):
    incident: IncidentRead
    run: AgentRunRead


class MetricsRead(BaseModel):
    incidents: int
    approved_incidents: int
    runs: int
    completion_rate: float = Field(ge=0, le=1)
    approval_rate: float = Field(ge=0, le=1)
    average_latency_ms: float | None = Field(default=None, ge=0)
    last_activity_at: datetime | None = None
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    estimated_cost_usd: float | None
    provider_breakdown: dict[str, int]


class HealthRead(BaseModel):
    status: Literal["ok"] = "ok"
    provider: str
    database: str
    model: str
