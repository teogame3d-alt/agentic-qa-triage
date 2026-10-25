from agentic_qa_triage import repository
from agentic_qa_triage.database import build_engine, build_session_factory, initialize_database


def test_known_incident_search_is_deterministic() -> None:
    engine = build_engine("sqlite+pysqlite:///:memory:")
    initialize_database(engine)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repository.seed_known_incidents(session)
        matches = repository.search_known_incidents(
            session,
            "expired login cookie redirects API 401",
            limit=2,
        )

    assert matches
    assert matches[0].component == "Authentication / session middleware"
    engine.dispose()


def test_search_returns_no_false_match_for_unrelated_text() -> None:
    engine = build_engine("sqlite+pysqlite:///:memory:")
    initialize_database(engine)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repository.seed_known_incidents(session)
        matches = repository.search_known_incidents(session, "purple spaceship", limit=3)

    assert matches == []
    engine.dispose()
