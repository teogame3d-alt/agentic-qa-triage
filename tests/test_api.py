import pytest
from fastapi.testclient import TestClient

from agentic_qa_triage.api import create_app
from agentic_qa_triage.config import Settings
from agentic_qa_triage.database import build_engine

SAMPLE_INCIDENT = {
    "title": "Login loop after session expiry",
    "description": (
        "After the session expires, the browser redirects between /login and /dashboard. "
        "The API returns 401 every time. Expected: show the login page after one refresh attempt."
    ),
    "environment": "Windows 11, Chrome, staging 0.9.4",
    "reporter": "QA portfolio test",
}


def test_health_exposes_runtime_without_secrets(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "provider": "demo",
        "database": "sqlite",
        "model": "deterministic-demo-v1",
    }


def test_triage_creates_reviewable_draft_and_metrics(client: TestClient) -> None:
    response = client.post("/api/incidents/triage", json=SAMPLE_INCIDENT)

    assert response.status_code == 201
    payload = response.json()
    assert payload["incident"]["status"] == "draft"
    assert payload["incident"]["severity"] == "high"
    assert payload["incident"]["source"] == "demo"
    assert payload["run"]["tool_calls"] == 1
    assert payload["run"]["input_tokens"] == 0

    metrics = client.get("/api/metrics").json()
    assert metrics["incidents"] == 1
    assert metrics["runs"] == 1
    assert metrics["approved_incidents"] == 0
    assert metrics["provider_breakdown"] == {"demo": 1}


def test_human_approval_is_a_separate_write(client: TestClient) -> None:
    incident = client.post("/api/incidents/triage", json=SAMPLE_INCIDENT).json()["incident"]

    response = client.post(f"/api/incidents/{incident['id']}/approve")

    assert response.status_code == 200
    approved = response.json()
    assert approved["status"] == "approved"
    assert approved["approved_at"] is not None


def test_invalid_report_is_rejected_before_the_agent(client: TestClient) -> None:
    response = client.post(
        "/api/incidents/triage",
        json={"title": "Bug", "description": "Too short"},
    )

    assert response.status_code == 422
    assert client.get("/api/incidents").json() == []


def test_input_budget_is_rejected_before_the_provider(client: TestClient) -> None:
    response = client.post(
        "/api/incidents/triage",
        json={
            **SAMPLE_INCIDENT,
            "description": "x" * 5_000,
        },
    )

    assert response.status_code == 422
    assert "character budget" in response.json()["detail"]


def test_missing_openai_key_is_reported_as_provider_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        agent_provider="openai",
    )
    engine = build_engine(settings.database_url)
    app = create_app(settings=settings, engine=engine)

    with TestClient(app) as openai_client:
        response = openai_client.post("/api/incidents/triage", json=SAMPLE_INCIDENT)

    assert response.status_code == 503
    assert response.json()["detail"] == ("OPENAI_API_KEY is required when AGENT_PROVIDER=openai.")
