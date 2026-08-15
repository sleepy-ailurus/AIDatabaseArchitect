"""AI schema review - the LLM layer on top of rule-based lint (feature 5)."""
from __future__ import annotations

import json

from app.services.llm_service import LLMSettings, complete_json
from app.services.schema_parser import ParsedSchema


def _schema_summary(schema: ParsedSchema) -> list[dict]:
    return [
        {
            "name": t.name,
            "comment": t.comment,
            "columns": [
                {
                    "name": c.name,
                    "type": c.data_type,
                    "pk": c.is_primary_key,
                    "unique": c.is_unique,
                    "nullable": c.nullable,
                    "comment": c.comment,
                }
                for c in t.columns
            ],
            "foreign_keys": [
                {
                    "column": fk.get("source_column"),
                    "references": f"{fk.get('target_table')}.{fk.get('target_column')}",
                }
                for fk in t.foreign_keys or []
            ],
        }
        for t in schema.tables
    ]


def ai_review_schema(
    schema: ParsedSchema,
    lint_findings: list[dict],
    settings: LLMSettings,
) -> list[dict]:
    """Ask the LLM for business-level architecture review findings."""
    payload = complete_json(
        settings,
        system_prompt=(
            "你是一个资深数据库架构师。基于数据库 Schema 元数据和规则检查结果，"
            "从业务建模合理性、范式化、字段冗余、命名一致性、扩展性等角度给出评审建议。"
            "只输出 JSON：{\"findings\":[{\"severity\":\"fatal|warning|suggestion\","
            "\"category\":\"类别\",\"target\":\"涉及的表或字段\",\"message\":\"问题描述\","
            "\"suggestion\":\"改进建议\"}]}，不要输出其他文字。"
        ),
        user_prompt=(
            "数据库 Schema：\n"
            f"{json.dumps(_schema_summary(schema), ensure_ascii=False)}\n\n"
            "规则检查结果（可能为空）：\n"
            f"{json.dumps(lint_findings, ensure_ascii=False)}\n\n"
            "请输出 3~8 条最有价值的评审意见。"
        ),
    )
    items = payload.get("findings") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity") or "suggestion").lower()
        if severity not in ("fatal", "warning", "suggestion"):
            severity = "suggestion"
        out.append(
            {
                "severity": severity,
                "category": str(item.get("category") or "综合评审"),
                "target": str(item.get("target") or ""),
                "message": str(item.get("message") or ""),
                "suggestion": str(item.get("suggestion") or ""),
            }
        )
    return out
