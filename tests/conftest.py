import pytest
from fastapi.testclient import TestClient

from agentic_qa_triage.api import create_app
from agentic_qa_triage.config import Settings
from agentic_qa_triage.database import build_engine


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        agent_provider="demo",
        max_agent_turns=3,
        max_input_chars=5_000,
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    engine = build_engine(test_settings.database_url)
    app = create_app(settings=test_settings, engine=engine)
    with TestClient(app) as test_client:
        yield test_client
