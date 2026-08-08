"""Pydantic v2 schemas for request validation and response serialization."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageOut(BaseModel):
    message: str
    detail: str | None = None


class ErrorOut(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None


class ProjectOut(ORMModel):
    id: int
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    tables: int = 0
    relations: int = 0
    suggestions: int = 0
    db_type: str | None = None


# ---------------------------------------------------------------------------
# Database connections
# ---------------------------------------------------------------------------
class SSLConfig(BaseModel):
    enabled: bool = False
    ca: str | None = None
    cert: str | None = None
    key: str | None = None


class ConnectionCreate(BaseModel):
    project_id: int
    db_type: str = "mysql"
    host: str = Field(min_length=1)
    port: int = Field(default=3306, ge=1, le=65535)
    database_name: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str | None = None
    ssl_config: SSLConfig | None = None
    timeout: int = Field(default=30, ge=1, le=600)
    save_credentials: bool = True


class ConnectionTest(BaseModel):
    """Schema for testing a connection without persisting it (no project_id required)."""
    db_type: str = "mysql"
    host: str = Field(min_length=1)
    port: int = Field(default=3306, ge=1, le=65535)
    database_name: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str | None = None
    ssl_config: SSLConfig | None = None
    timeout: int = Field(default=30, ge=1, le=600)


class ConnectionOut(ORMModel):
    id: int
    project_id: int
    db_type: str
    host: str
    port: int
    database_name: str
    username: str
    ssl_config: dict | None = None
    timeout: int
    created_at: datetime
    has_password: bool = False


class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    db_version: str | None = None
    table_count: int | None = None
    elapsed_ms: int | None = None
    checks: list[dict] | None = None


# ---------------------------------------------------------------------------
# Schema parsing
# ---------------------------------------------------------------------------
class ColumnOut(ORMModel):
    id: int
    column_name: str
    data_type: str
    length: int | None
    nullable: bool
    default_value: str | None
    is_primary_key: bool
    is_unique: bool
    comment: str | None


class TableOut(ORMModel):
    id: int
    table_name: str
    comment: str | None
    engine: str | None
    columns: list[ColumnOut] = []


class SnapshotOut(ORMModel):
    id: int
    project_id: int
    version: int
    created_at: datetime
    table_count: int = 0


class SchemaSyncResult(BaseModel):
    success: bool
    message: str
    snapshot_id: int | None = None
    table_count: int = 0
    relationship_count: int = 0


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------
Cardinality = Literal[
    "one-to-one", "one-to-many", "many-to-one", "many-to-many", "1:1", "1:N", "N:N"
]
SourceType = Literal["database_constraint", "ai_suggestion", "manual"]
RelationStatus = Literal["confirmed", "suggested", "rejected", "manual", "outdated"]


class RelationshipCreate(BaseModel):
    source_table: str
    source_column: str | None = None
    target_table: str
    target_column: str | None = None
    cardinality: str = "many-to-one"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_type: str = "manual"
    status: str = "manual"
    reason: list[str] | None = None
    constraint_name: str | None = None


class RelationshipUpdate(BaseModel):
    cardinality: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    status: str | None = None
    source_type: str | None = None
    reason: list[str] | None = None


class RelationshipOut(ORMModel):
    id: int
    project_id: int
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    cardinality: str
    confidence: float
    source_type: str
    status: str
    reason: list[str] | None
    constraint_name: str | None
    created_at: datetime
    cardinality_display: str | None = None
    source_data_type: str | None = None
    target_data_type: str | None = None
    type_match: bool | None = None


# ---------------------------------------------------------------------------
# ER models
# ---------------------------------------------------------------------------
class ERModelData(BaseModel):
    nodes: list[dict] = []
    edges: list[dict] = []
    viewport: dict | None = None


class ERModelOut(ORMModel):
    id: int
    project_id: int
    model_data: dict | None
    created_at: datetime
    updated_at: datetime


class ERModelVersionOut(ORMModel):
    id: int
    model_id: int
    version_number: int
    version_data: dict | None
    created_at: datetime


# ---------------------------------------------------------------------------
# LLM configs
# ---------------------------------------------------------------------------
class LLMConfigCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider: str = "openai"
    base_url: str = Field(min_length=1)
    api_key: str | None = None
    model: str = Field(min_length=1)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    max_retries: int = Field(default=2, ge=0, le=10)
    usage: list[str] | None = None
    usage_list: list[str] | None = None
    is_default: bool = False


class LLMConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    provider: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    timeout_seconds: int | None = Field(default=None, ge=1, le=600)
    max_retries: int | None = Field(default=None, ge=0, le=10)
    usage: list[str] | None = None
    usage_list: list[str] | None = None
    is_default: bool | None = None


class LLMConfigOut(ORMModel):
    id: int
    name: str
    provider: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    timeout_seconds: int
    max_retries: int
    usage: list[str] | None
    usage_list: list[str] | None = None
    is_default: bool
    last_test_ok: bool | None = None
    created_at: datetime
    api_key_masked: str | None = None
    status_ok: bool | None = None


class LLMTestRequest(BaseModel):
    config_id: int | None = None
    provider: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = None
    timeout_seconds: int | None = None
    max_retries: int | None = None


class LLMTestResult(BaseModel):
    success: bool
    message: str
    elapsed_ms: int | None = None
    model: str | None = None


# ---------------------------------------------------------------------------
# Analysis tasks
# ---------------------------------------------------------------------------
class AnalysisTaskCreate(BaseModel):
    llm_config_id: int | None = None
    run_llm: bool = True


class AnalysisTaskOut(ORMModel):
    id: int
    project_id: int
    status: str
    progress: int
    llm_config_id: int | None
    result: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
class ExportCreate(BaseModel):
    format: str = "markdown"


class ExportOut(ORMModel):
    id: int
    project_id: int
    format: str
    content: str
    created_at: datetime
