"""MCP Server (feature 2) - expose schema/model knowledge to AI coding tools.

Transports:
  - stdio (local agents: `python run.py --mcp`)
  - Streamable HTTP (mounted at /mcp on the FastAPI app)

Tools are read-only by design: list projects, inspect tables/columns/
relationships, export ER diagrams and answer schema questions via the user's
configured LLM.
"""
from __future__ import annotations

import json
from typing import Any

from mcp.server.mcpserver import MCPServer

from app.database import SessionLocal
from app.models import LLMConfig, Project, Relationship, SchemaSnapshot, SchemaTable
from app.services.llm_service import complete_text, settings_from_config
from app.services.schema_parser import schema_from_dict

server = MCPServer(
    name="ai-database-architect",
    title="AI Database Architect",
    version="1.0.0",
    description=(
        "Read-only access to database schemas modeled in AI Database Architect: "
        "tables, columns, relationships, ER diagrams and AI-powered schema Q&A."
    ),
)


def _latest_snapshot(db, project_id: int) -> SchemaSnapshot | None:
    return (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.project_id == project_id)
        .order_by(SchemaSnapshot.version.desc())
        .first()
    )


def _get_project(db, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise ValueError(f"项目 {project_id} 不存在")
    return project


def _project_summary(db, p: Project) -> dict[str, Any]:
    snapshot = _latest_snapshot(db, p.id)
    table_count = 0
    if snapshot:
        table_count = db.query(SchemaTable).filter(SchemaTable.snapshot_id == snapshot.id).count()
    rel_count = db.query(Relationship).filter(Relationship.project_id == p.id).count()
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "db_type": p.db_type,
        "status": p.status,
        "tables": table_count,
        "relationships": rel_count,
    }


def _schema_of(db, project_id: int):
    snapshot = _latest_snapshot(db, project_id)
    if not snapshot or not snapshot.snapshot_data:
        raise ValueError("该项目尚无 Schema 快照，请先在应用中同步或导入")
    return schema_from_dict(snapshot.snapshot_data)


def _relationships_of(db, project_id: int) -> list[dict]:
    rels = db.query(Relationship).filter(Relationship.project_id == project_id).all()
    return [
        {
            "source_table": r.source_table,
            "source_column": r.source_column,
            "target_table": r.target_table,
            "target_column": r.target_column,
            "cardinality": r.cardinality,
            "source_type": r.source_type,
            "status": r.status,
            "confidence": r.confidence,
        }
        for r in rels
    ]


def _mermaid_er(schema, relationships: list[dict]) -> str:
    lines = ["erDiagram"]
    for t in schema.tables:
        safe = (t.name or "").replace("-", "_").upper() or "T"
        lines.append(f"    {safe} {{")
        for c in t.columns:
            attr = c.data_type.lower()
            tag = "PK" if c.is_primary_key else ""
            comment = f' "{c.comment}"' if c.comment else ""
            lines.append(f"        {attr} {c.name} {tag}{comment}".rstrip())
        lines.append("    }")
    for r in relationships:
        src = (r["source_table"] or "").replace("-", "_").upper()
        tgt = (r["target_table"] or "").replace("-", "_").upper()
        if not src or not tgt:
            continue
        if r["cardinality"] == "one-to-one":
            sym = "||--||"
        elif r["cardinality"] == "many-to-many":
            sym = "}o--o{"
        else:
            sym = "||--o{"
        label = f"{r.get('source_column', '')}_{r.get('target_column', '')}".replace(" ", "_")
        lines.append(f"    {tgt} {sym} {src} : {label}")
    return "\n".join(lines)


@server.tool(name="list_projects", description="List all projects with table/relationship counts")
def list_projects() -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        projects = db.query(Project).order_by(Project.updated_at.desc()).all()
        return [_project_summary(db, p) for p in projects]
    finally:
        db.close()


@server.tool(name="get_project", description="Get project metadata (tables/relationships counts)")
def get_project(project_id: int) -> dict[str, Any]:
    db = SessionLocal()
    try:
        return _project_summary(db, _get_project(db, project_id))
    finally:
        db.close()


@server.tool(name="list_tables", description="List table names of a project")
def list_tables(project_id: int) -> list[str]:
    db = SessionLocal()
    try:
        schema = _schema_of(db, project_id)
        return [t.name for t in schema.tables]
    finally:
        db.close()


@server.tool(name="get_table_schema", description="Get columns, types, keys and comments of one table")
def get_table_schema(project_id: int, table_name: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        schema = _schema_of(db, project_id)
        table = next((t for t in schema.tables if t.name.lower() == str(table_name).lower()), None)
        if table is None:
            raise ValueError(f"表 {table_name} 不存在")
        return {
            "name": table.name,
            "comment": table.comment,
            "engine": table.engine,
            "columns": [
                {
                    "name": c.name,
                    "type": c.data_type,
                    "length": c.length,
                    "nullable": c.nullable,
                    "default": c.default_value,
                    "primary_key": c.is_primary_key,
                    "unique": c.is_unique,
                    "comment": c.comment,
                }
                for c in table.columns
            ],
            "foreign_keys": table.foreign_keys,
            "indexes": table.indexes,
        }
    finally:
        db.close()


@server.tool(name="list_relationships", description="List relationships (FK, AI suggestions, manual)")
def list_relationships(project_id: int) -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        _get_project(db, project_id)
        return _relationships_of(db, project_id)
    finally:
        db.close()


@server.tool(
    name="export_er_diagram",
    description="Export the ER diagram as Mermaid or JSON for the given project",
)
def export_er_diagram(project_id: int, format: str = "mermaid") -> str:
    db = SessionLocal()
    try:
        schema = _schema_of(db, project_id)
        rels = _relationships_of(db, project_id)
        if str(format).lower() == "json":
            return json.dumps(
                {
                    "tables": [
                        {
                            "name": t.name,
                            "comment": t.comment,
                            "columns": [
                                {
                                    "name": c.name,
                                    "type": c.data_type,
                                    "primary_key": c.is_primary_key,
                                    "unique": c.is_unique,
                                    "comment": c.comment,
                                }
                                for c in t.columns
                            ],
                        }
                        for t in schema.tables
                    ],
                    "relationships": rels,
                },
                ensure_ascii=False,
            )
        return _mermaid_er(schema, rels)
    finally:
        db.close()


@server.tool(
    name="ask_schema",
    description="Ask a question about the schema (answered by the user's configured LLM)",
)
def ask_schema(project_id: int, question: str) -> str:
    db = SessionLocal()
    try:
        schema = _schema_of(db, project_id)
        config = (
            db.query(LLMConfig)
            .filter(LLMConfig.is_default.is_(True))
            .order_by(LLMConfig.id.asc())
            .first()
        ) or db.query(LLMConfig).order_by(LLMConfig.id.asc()).first()
        if not config:
            return "未配置 LLM，无法回答问题。请在应用的『设置 → LLM 配置』中添加模型。"
        summary = [
            {
                "name": t.name,
                "comment": t.comment,
                "columns": [
                    {"name": c.name, "type": c.data_type, "pk": c.is_primary_key, "comment": c.comment}
                    for c in t.columns
                ],
            }
            for t in schema.tables
        ]
        answer = complete_text(
            settings_from_config(config),
            system_prompt="你是数据库架构助手。基于给定 Schema 回答用户问题，简洁准确。",
            user_prompt=f"数据库 Schema：{json.dumps(summary, ensure_ascii=False)}\n\n问题：{question}",
            max_retries=1,
        )
        return str(answer)
    finally:
        db.close()


def run_stdio() -> None:
    """Run the MCP server over stdio (for local AI agents)."""
    import asyncio

    asyncio.run(server.run_stdio_async())
