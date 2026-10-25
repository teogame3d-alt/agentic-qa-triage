from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from . import repository
from .config import Settings, get_settings
from .database import (
    build_engine,
    build_session_factory,
    initialize_database,
    session_dependency,
)
from .schemas import (
    HealthRead,
    IncidentCreate,
    IncidentRead,
    MetricsRead,
    TriageResponse,
)
from .service import InputBudgetError, TriageProviderError, TriageService

STATIC_DIR = Path(__file__).parent / "static"
DatabaseSession = Annotated[Session, Depends(session_dependency)]


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_engine = engine or build_engine(resolved_settings.database_url)
    session_factory = build_session_factory(resolved_engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        initialize_database(resolved_engine)
        with session_factory() as session:
            repository.seed_known_incidents(session)
        yield
        resolved_engine.dispose()

    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        description="Cost-aware incident triage with human approval.",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.engine = resolved_engine
    app.state.session_factory = session_factory
    app.state.triage_service = TriageService(resolved_settings)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health", response_model=HealthRead)
    def health() -> HealthRead:
        database_name = (
            "postgresql" if resolved_settings.database_url.startswith("postgres") else "sqlite"
        )
        return HealthRead(
            provider=resolved_settings.agent_provider,
            database=database_name,
            model=(
                resolved_settings.openai_model
                if resolved_settings.agent_provider == "openai"
                else "deterministic-demo-v1"
            ),
        )

    @app.post(
        "/api/incidents/triage",
        response_model=TriageResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def triage_incident(
        payload: IncidentCreate,
        request: Request,
        session: DatabaseSession,
    ) -> TriageResponse:
        try:
            incident, run = await request.app.state.triage_service.triage(session, payload)
        except InputBudgetError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc
        except TriageProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        return TriageResponse(
            incident=IncidentRead.model_validate(incident),
            run=run,
        )

    @app.get("/api/incidents", response_model=list[IncidentRead])
    def incidents(
        session: DatabaseSession,
        limit: Annotated[int, Query(ge=1, le=100)] = 30,
    ) -> list[IncidentRead]:
        return [
            IncidentRead.model_validate(item) for item in repository.list_incidents(session, limit)
        ]

    @app.post("/api/incidents/{incident_id}/approve", response_model=IncidentRead)
    def approve(
        incident_id: int,
        session: DatabaseSession,
    ) -> IncidentRead:
        incident = repository.approve_incident(session, incident_id)
        if incident is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
        session.commit()
        session.refresh(incident)
        return IncidentRead.model_validate(incident)

    @app.get("/api/metrics", response_model=MetricsRead)
    def usage_metrics(session: DatabaseSession) -> MetricsRead:
        return MetricsRead.model_validate(repository.metrics(session))

    return app


app = create_app()
