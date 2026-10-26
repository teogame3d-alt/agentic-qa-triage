import re
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import AgentRun, Incident, KnownIncident
from .schemas import IncidentCreate, TriageDecision


def create_incident(session: Session, payload: IncidentCreate) -> Incident:
    incident = Incident(
        title=payload.title.strip(),
        description=payload.description.strip(),
        environment=payload.environment.strip() or "Not provided",
        reporter=payload.reporter.strip() or "Unspecified",
    )
    session.add(incident)
    session.flush()
    return incident


def apply_decision(
    incident: Incident,
    decision: TriageDecision,
    *,
    source: str,
) -> None:
    incident.source = source
    incident.severity = decision.severity
    incident.category = decision.category
    incident.summary = decision.summary
    incident.suspected_component = decision.suspected_component
    incident.reproduction_steps = decision.reproduction_steps
    incident.test_plan = decision.test_plan
    incident.missing_information = decision.missing_information
    incident.similar_incident_ids = decision.similar_incident_ids
    incident.confidence = decision.confidence


def add_run(
    session: Session,
    incident: Incident,
    *,
    provider: str,
    model: str,
    input_tokens: int,
    cached_input_tokens: int,
    output_tokens: int,
    tool_calls: int,
    duration_ms: int,
    estimated_cost_usd: float | None,
) -> AgentRun:
    run = AgentRun(
        incident=incident,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        output_tokens=output_tokens,
        tool_calls=tool_calls,
        duration_ms=duration_ms,
        estimated_cost_usd=estimated_cost_usd,
    )
    session.add(run)
    session.flush()
    return run


def get_incident(session: Session, incident_id: int) -> Incident | None:
    statement = (
        select(Incident).where(Incident.id == incident_id).options(selectinload(Incident.runs))
    )
    return session.scalar(statement)


def list_incidents(session: Session, limit: int = 30) -> list[Incident]:
    statement = (
        select(Incident)
        .options(selectinload(Incident.runs))
        .order_by(Incident.created_at.desc())
        .limit(limit)
    )
    return list(session.scalars(statement).all())


def approve_incident(session: Session, incident_id: int) -> Incident | None:
    incident = get_incident(session, incident_id)
    if incident is None:
        return None
    if incident.status == "approved":
        return incident
    if incident.status != "draft":
        return None
    incident.status = "approved"
    incident.approved_at = datetime.now(UTC)
    session.flush()
    return incident


def _keywords(value: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9ăâîșț]+", value.lower()) if len(word) >= 4}


def search_known_incidents(
    session: Session,
    query: str,
    limit: int = 3,
) -> list[KnownIncident]:
    """Small deterministic retrieval layer used by both the tool and demo provider."""

    query_words = _keywords(query)
    incidents = list(session.scalars(select(KnownIncident)).all())
    scored: list[tuple[float, KnownIncident]] = []
    for incident in incidents:
        document_words = _keywords(
            f"{incident.title} {incident.symptoms} {incident.component} {incident.resolution}"
        )
        overlap = len(query_words & document_words)
        score = overlap / max(len(query_words), 1)
        if overlap:
            scored.append((score, incident))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    return [incident for _, incident in scored[: max(1, min(limit, 5))]]


def metrics(session: Session) -> dict[str, object]:
    incidents = list(session.scalars(select(Incident)).all())
    runs = list(session.scalars(select(AgentRun)).all())
    costs = [run.estimated_cost_usd for run in runs if run.estimated_cost_usd is not None]
    approved_incidents = sum(item.status == "approved" for item in incidents)
    completion_rate = len(runs) / len(incidents) if incidents else 0.0
    approval_rate = approved_incidents / len(incidents) if incidents else 0.0
    average_latency_ms = (
        round(sum(run.duration_ms for run in runs) / len(runs), 1) if runs else None
    )
    activity_dates = [item.created_at for item in incidents]
    activity_dates.extend(run.created_at for run in runs)
    return {
        "incidents": len(incidents),
        "approved_incidents": approved_incidents,
        "runs": len(runs),
        "completion_rate": round(completion_rate, 4),
        "approval_rate": round(approval_rate, 4),
        "average_latency_ms": average_latency_ms,
        "last_activity_at": max(activity_dates) if activity_dates else None,
        "input_tokens": sum(run.input_tokens for run in runs),
        "cached_input_tokens": sum(run.cached_input_tokens for run in runs),
        "output_tokens": sum(run.output_tokens for run in runs),
        "estimated_cost_usd": round(sum(costs), 8) if costs else None,
        "provider_breakdown": dict(Counter(run.provider for run in runs)),
    }


def seed_known_incidents(session: Session) -> None:
    if session.scalar(select(KnownIncident.id).limit(1)) is not None:
        return

    session.add_all(
        [
            KnownIncident(
                title="Login loop after session expiry",
                symptoms=(
                    "Users are redirected between /login and /dashboard after an expired cookie. "
                    "The API returns 401 repeatedly."
                ),
                component="Authentication / session middleware",
                severity="high",
                resolution="Clear the stale cookie and refresh the token only once before logout.",
            ),
            KnownIncident(
                title="CSV import rejects Romanian diacritics",
                symptoms=(
                    "CSV upload fails for names containing ă, â, î, ș or ț and reports an "
                    "encoding error."
                ),
                component="Data import pipeline",
                severity="medium",
                resolution="Decode as UTF-8 with BOM detection and validate the header separately.",
            ),
            KnownIncident(
                title="Dashboard latency grows with incident count",
                symptoms=(
                    "The incident dashboard becomes slow after thousands of rows because related "
                    "runs are loaded one query at a time."
                ),
                component="Incident query / database access",
                severity="medium",
                resolution="Add pagination and eager-load the latest run in a bounded query.",
            ),
        ]
    )
    session.commit()
