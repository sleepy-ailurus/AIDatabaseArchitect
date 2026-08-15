"""SQLAlchemy ORM models for the AI Database Architect platform.

All platform data is stored in SQLite. Sensitive fields (database passwords,
LLM API keys) are encrypted at rest using Fernet.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    db_type: Mapped[str] = mapped_column(String(32), nullable=False, default="mysql")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    connections: Mapped[list[DatabaseConnection]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list[SchemaSnapshot]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    relationships: Mapped[list[Relationship]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    er_models: Mapped[list[ERModel]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    concept_models: Mapped[list[ConceptModel]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    review_reports: Mapped[list[ReviewReport]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    comment_suggestions: Mapped[list[CommentSuggestion]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    sensitive_fields: Mapped[list[SensitiveField]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    domain_clusters: Mapped[list[DomainCluster]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    exports: Mapped[list[DocumentExport]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    db_type: Mapped[str] = mapped_column(String(32), nullable=False, default="mysql")
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=3306)
    database_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    ssl_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="connections")


class SchemaSnapshot(Base):
    __tablename__ = "schema_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="snapshots")
    tables: Mapped[list[SchemaTable]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class SchemaTable(Base):
    __tablename__ = "schema_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("schema_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    engine: Mapped[str | None] = mapped_column(String(64), nullable=True)

    snapshot: Mapped[SchemaSnapshot] = relationship(back_populates="tables")
    columns: Mapped[list[SchemaColumn]] = relationship(
        back_populates="table", cascade="all, delete-orphan"
    )


class SchemaColumn(Base):
    __tablename__ = "schema_columns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("schema_tables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(128), nullable=False)
    length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nullable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary_key: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_unique: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    table: Mapped[SchemaTable] = relationship(back_populates="columns")


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_table: Mapped[str] = mapped_column(String(255), nullable=False)
    source_column: Mapped[str] = mapped_column(String(255), nullable=False)
    target_table: Mapped[str] = mapped_column(String(255), nullable=False)
    target_column: Mapped[str] = mapped_column(String(255), nullable=False)
    cardinality: Mapped[str] = mapped_column(String(32), nullable=False, default="many-to-one")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    # database_constraint | ai_suggestion | manual
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    # confirmed | suggested | rejected | manual | outdated
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="suggested")
    reason: Mapped[list | None] = mapped_column(JSON, nullable=True)
    constraint_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="relationships")


class ERModel(Base):
    __tablename__ = "er_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # model_data holds: {nodes, edges, viewport}
    model_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="er_models")
    versions: Mapped[list[ERModelVersion]] = relationship(
        back_populates="model", cascade="all, delete-orphan"
    )


class ERModelVersion(Base):
    __tablename__ = "er_model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[int] = mapped_column(
        ForeignKey("er_models.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    model: Mapped[ERModel] = relationship(back_populates="versions")


class ConceptModel(Base):
    """ER concept model (Chen notation) derived from / linked to the physical model.

    model_data holds: {entities, relations, viewport}
    - entities:  [{id, name, table, comment, attributes: [{id, name, column,
      data_type, is_pk, is_fk, is_unique, nullable, comment}], position}]
    - relations: [{id, name, source_entity, target_entity, source_card,
      target_card, source_table, source_column, target_table, target_column,
      cardinality, attributes: [...], reason: [...]}]
    """

    __tablename__ = "concept_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="concept_models")


class ReviewReport(Base):
    """Schema review report: rule-based lint findings + optional AI findings."""

    __tablename__ = "review_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lint_findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    used_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="review_reports")


class CommentSuggestion(Base):
    """AI-generated table / column comment suggestion (feature 3)."""

    __tablename__ = "comment_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    column_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False, default="column")  # table | column
    suggested_comment: Mapped[str] = mapped_column(Text, nullable=False)
    # suggested | accepted | rejected | applied
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="suggested")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="comment_suggestions")


class SensitiveField(Base):
    """Sensitive / PII field detected by the sensitive data identifier (feature 10)."""

    __tablename__ = "sensitive_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    category_label: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    # high | medium | low
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    matched_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_hits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # detected | confirmed | false_positive | mitigated
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="detected")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="sensitive_fields")


class DomainCluster(Base):
    """Business-domain cluster derived from the FK graph (feature 9)."""

    __tablename__ = "domain_clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cluster_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tables: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [table_name]
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="domain_clusters")


class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="openai")
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    endpoint_path: Mapped[str] = mapped_column(String(255), nullable=False, default="/chat/completions")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=4096)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    rate_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    rate_unlimited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # relation_analysis | doc_generation | qa  (stored as JSON list of usages)
    usage: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class DocumentExport(Base):
    __tablename__ = "document_exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    format: Mapped[str] = mapped_column(String(32), nullable=False, default="markdown")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="exports")


class AnalysisTask(Base):
    """Tracks an AI relation-analysis workflow (Stage 2).

    Status transitions:
    pending -> parsing -> analyzing -> validating -> completed
                                            --> failed
                                            --> cancelled
    """

    __tablename__ = "analysis_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_config_id: Mapped[int | None] = mapped_column(
        ForeignKey("llm_configs.id", ondelete="SET NULL"), nullable=True
    )
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UserSettings(Base):
    """Global user preferences stored as a single-row config table."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # UI preferences
    theme: Mapped[str] = mapped_column(String(32), nullable=False, default="auto")
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="zh-CN")
    # AI analysis preferences
    show_confidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_check_high: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
