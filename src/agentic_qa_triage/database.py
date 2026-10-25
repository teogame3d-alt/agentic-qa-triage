from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base


def build_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine for PostgreSQL or the SQLite fallback."""

    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url:
            kwargs["poolclass"] = StaticPool
    return create_engine(database_url, **kwargs)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def initialize_database(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)


async def session_dependency(request: Request) -> AsyncIterator[Session]:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
