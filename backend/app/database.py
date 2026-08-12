"""SQLAlchemy engine, session factory and declarative Base for the platform DB."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# check_same_thread=False is required so FastAPI background tasks / threads can
# share the SQLite connection safely.
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def init_db() -> None:
    """Create all tables (idempotent)."""
    from app import models  # noqa: F401  - ensure models are registered

    Base.metadata.create_all(bind=engine)
    _migrate_llm_configs()
    _migrate_projects()


def _migrate_projects() -> None:
    """Add the db_type column to an existing projects table (idempotent)."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "projects" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("projects")}
    if "db_type" not in columns:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN db_type VARCHAR(32) NOT NULL DEFAULT 'mysql'"
            ))


def _migrate_llm_configs() -> None:
    """Add missing columns to existing llm_configs table."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("llm_configs")}
    if "is_active" not in columns:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE llm_configs ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
            ))
    if "rate_limit" not in columns:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE llm_configs ADD COLUMN rate_limit INTEGER NOT NULL DEFAULT 50"
            ))
    if "rate_unlimited" not in columns:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE llm_configs ADD COLUMN rate_unlimited BOOLEAN NOT NULL DEFAULT 0"
            ))
    if "endpoint_path" not in columns:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE llm_configs ADD COLUMN endpoint_path VARCHAR(255) NOT NULL DEFAULT '/chat/completions'"
            ))
            conn.execute(text(
                "UPDATE llm_configs SET endpoint_path = '/v1/chat/completions' WHERE provider = 'ollama'"
            ))
    else:
        # Migrate older Ollama configs from the native /api/chat endpoint to the
        # OpenAI-compatible /v1/chat/completions endpoint used by the app.
        with engine.begin() as conn:
            conn.execute(text(
                "UPDATE llm_configs SET endpoint_path = '/v1/chat/completions' WHERE provider = 'ollama' AND endpoint_path = '/api/chat'"
            ))


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
