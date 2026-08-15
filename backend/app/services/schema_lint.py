"""Rule-based schema lint (feature 5, rule layer).

Each rule is a pure function over a ParsedSchema returning a list of findings:
  {id, severity: fatal|warning|suggestion, category, table, column, message, fix}
The AI layer (see reviews router) consumes these findings together with the
schema summary to produce deeper, business-oriented recommendations.
"""
from __future__ import annotations

import re
from typing import Any, Callable

from app.services.schema_parser import ParsedSchema, is_type_compatible


_RESERVED_WORDS = {
    "select", "insert", "update", "delete", "from", "where", "group", "order",
    "having", "join", "left", "right", "inner", "outer", "on", "as", "and",
    "or", "not", "null", "is", "in", "like", "between", "exists", "union",
    "all", "distinct", "limit", "offset", "case", "when", "then", "else", "end",
    "create", "alter", "drop", "table", "index", "key", "constraint", "primary",
    "foreign", "references", "unique", "default", "check", "values", "set",
    "add", "column", "to", "with", "by", "desc", "asc", "into", "values",
    "user", "order", "group", "desc", "asc", "database", "schema", "grant",
    "revoke", "role", "type", "status", "comment", "count", "sum", "avg",
}


def _finding(
    rule_id: str,
    severity: str,
    category: str,
    message: str,
    fix: str,
    table: str = "",
    column: str = "",
) -> dict[str, Any]:
    return {
        "id": rule_id,
        "severity": severity,
        "category": category,
        "table": table,
        "column": column,
        "message": message,
        "fix": fix,
    }


def _table_name_style(name: str) -> str:
    if name != name.lower():
        return "mixed_or_upper"
    return "ok"


def run_lint(schema: ParsedSchema) -> list[dict[str, Any]]:
    """Run every rule and return the aggregated findings."""
    findings: list[dict[str, Any]] = []
    findings.extend(_lint_no_pk(schema))
    findings.extend(_lint_fk_no_index(schema))
    findings.extend(_lint_fk_type(schema))
    findings.extend(_lint_naming(schema))
    findings.extend(_lint_reserved_words(schema))
    findings.extend(_lint_missing_comments(schema))
    findings.extend(_lint_engine_mismatch(schema))
    findings.extend(_lint_oversized(schema))
    findings.extend(_lint_money_float(schema))
    findings.extend(_lint_text_pk(schema))
    findings.extend(_lint_varchar_vs_text(schema))
    findings.extend(_lint_redundant_index(schema))
    return findings


def summarize_findings(findings: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"fatal": 0, "warning": 0, "suggestion": 0, "total": len(findings)}
    for f in findings:
        sev = str(f.get("severity") or "suggestion")
        if sev in summary:
            summary[sev] += 1
    return summary


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
def _lint_no_pk(schema: ParsedSchema) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in schema.tables:
        if not any(c.is_primary_key for c in t.columns):
            out.append(
                _finding(
                    "no_primary_key",
                    "fatal",
                    "主键",
                    f"表 {t.name} 没有主键",
                    "为表添加主键（建议自增 BIGINT 或业务唯一键）",
                    table=t.name,
                )
            )
    return out


def _indexed_cols(t) -> set[str]:
    cols: set[str] = set()
    for idx in t.indexes or []:
        for c in idx.get("columns") or []:
            cols.add(str(c).lower())
    return cols


def _lint_fk_no_index(schema: ParsedSchema) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in schema.tables:
        indexed = _indexed_cols(t)
        pk_cols = {c.name.lower() for c in t.columns if c.is_primary_key}
        for fk in t.foreign_keys or []:
            col = str(fk.get("source_column") or "").lower()
            if col and col not in indexed and col not in pk_cols:
                out.append(
                    _finding(
                        "fk_column_no_index",
                        "warning",
                        "索引",
                        f"外键列 {t.name}.{fk.get('source_column')} 没有索引",
                        f"为该列添加索引：CREATE INDEX idx_{t.name}_{fk.get('source_column')} ON {t.name} ({fk.get('source_column')});",
                        table=t.name,
                        column=str(fk.get("source_column") or ""),
                    )
                )
    return out


def _lint_fk_type(schema: ParsedSchema) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cols_by_table: dict[str, dict[str, Any]] = {}
    for t in schema.tables:
        cols_by_table[t.name.lower()] = {c.name.lower(): c for c in t.columns}
    for t in schema.tables:
        for fk in t.foreign_keys or []:
            target = cols_by_table.get(str(fk.get("target_table") or "").lower())
            if target is None:
                continue
            tc = target.get(str(fk.get("target_column") or "").lower())
            sc = next((c for c in t.columns if c.name.lower() == str(fk.get("source_column") or "").lower()), None)
            if sc is None or tc is None:
                continue
            if not is_type_compatible(sc.data_type, tc.data_type):
                out.append(
                    _finding(
                        "fk_type_incompatible",
                        "warning",
                        "外键",
                        f"外键类型不兼容：{t.name}.{sc.name} ({sc.data_type}) → {fk.get('target_table')}.{tc.name} ({tc.data_type})",
                        "统一两端字段类型，避免隐式转换影响索引命中",
                        table=t.name,
                        column=sc.name,
                    )
                )
    return out


def _lint_naming(schema: ParsedSchema) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in schema.tables:
        style = _table_name_style(t.name)
        if style != "ok":
            out.append(
                _finding(
                    "naming_case",
                    "warning",
                    "命名规范",
                    f"表名 {t.name} 未使用小写下划线风格（snake_case）",
                    f"建议重命名为 {t.name.lower().replace('-', '_')}",
                    table=t.name,
                )
            )
        for c in t.columns:
            if c.name != c.name.lower():
                out.append(
                    _finding(
                        "naming_case",
                        "warning",
                        "命名规范",
                        f"字段名 {t.name}.{c.name} 未使用小写风格",
                        f"建议重命名为 {c.name.lower().replace('-', '_')}",
                        table=t.name,
                        column=c.name,
                    )
                )
    return out


def _lint_reserved_words(schema: ParsedSchema) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in schema.tables:
        if t.name.lower() in _RESERVED_WORDS:
            out.append(
                _finding(
                    "reserved_word",
                    "warning",
                    "命名规范",
                    f"表名 {t.name} 是 SQL 保留字",
                    f"使用反引号引用或重命名，例如 {t.name}_table",
                    table=t.name,
                )
            )
        for c in t.columns:
            if c.name.lower() in _RESERVED_WORDS:
                out.append(
                    _finding(
                        "reserved_word",
                        "warning",
                        "命名规范",
                        f"字段名 {t.name}.{c.name} 是 SQL 保留字",
                        f"使用反引号引用或重命名为 {c.name}_col",
                        table=t.name,
                        column=c.name,
                    )
                )
    return out


def _lint_missing_comments(schema: ParsedSchema) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in schema.tables:
        missing_cols = [c.name for c in t.columns if not (c.comment or "").strip()]
        if not (t.comment or "").strip():
            out.append(
                _finding(
                    "missing_comment",
                    "suggestion",
                    "注释",
                    f"表 {t.name} 缺少注释",
                    "补充表注释，说明业务含义",
                    table=t.name,
                )
            )
        if missing_cols:
            preview = "、".join(missing_cols[:5]) + (" 等" if len(missing_cols) > 5 else "")
            out.append(
                _finding(
                    "missing_comment",
                    "suggestion",
                    "注释",
                    f"表 {t.name} 有 {len(missing_cols)} 个字段缺少注释（{preview}）",
                    "补充字段注释；可配合『AI 一键补齐注释』功能",
                    table=t.name,
                )
            )
    return out


def _lint_engine_mismatch(schema: ParsedSchema) -> list[dict[str, Any]]:
    engines = {t.engine for t in schema.tables if t.engine}
    if len(engines) > 1:
        return [
            _finding(
                "engine_mismatch",
                "warning",
                "一致性",
                f"表存储引擎不一致：{', '.join(sorted(engines))}",
                "统一存储引擎（推荐 InnoDB）以保持事务与外键行为一致",
            )
        ]
    return []


def _lint_oversized(schema: ParsedSchema) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in schema.tables:
        if len(t.columns) > 30:
            out.append(
                _finding(
                    "oversized_table",
                    "suggestion",
                    "结构",
                    f"表 {t.name} 有 {len(t.columns)} 个字段，建议拆分",
                    "按业务域拆分宽表（垂直拆分），或提取 JSON/子表存储扩展属性",
                    table=t.name,
                )
            )
    return out


_MONEY_NAMES = re.compile(r"(price|amount|money|cost|fee|balance|总额|金额|价格|费用|余额)", re.I)


def _lint_money_float(schema: ParsedSchema) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in schema.tables:
        for c in t.columns:
            if _MONEY_NAMES.search(c.name) and c.data_type.upper() in ("FLOAT", "DOUBLE", "REAL"):
                out.append(
                    _finding(
                        "money_as_float",
                        "warning",
                        "数据类型",
                        f"金额字段 {t.name}.{c.name} 使用 {c.data_type}，存在精度丢失风险",
                        "改为 DECIMAL(18,2) 或 DECIMAL(18,4)",
                        table=t.name,
                        column=c.name,
                    )
                )
    return out


def _lint_text_pk(schema: ParsedSchema) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    text_types = {"TEXT", "LONGTEXT", "MEDIUMTEXT", "TINYTEXT", "BLOB", "LONGBLOB"}
    for t in schema.tables:
        for c in t.columns:
            if c.is_primary_key and c.data_type.upper() in text_types:
                out.append(
                    _finding(
                        "text_as_pk",
                        "warning",
                        "主键",
                        f"主键 {t.name}.{c.name} 使用 {c.data_type}，性能与索引开销大",
                        "改用自增整数或 UUID 作为主键，文本列加唯一索引",
                        table=t.name,
                        column=c.name,
                    )
                )
    return out


def _lint_varchar_vs_text(schema: ParsedSchema) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in schema.tables:
        for c in t.columns:
            if c.data_type.upper() == "VARCHAR" and c.length and c.length >= 255:
                out.append(
                    _finding(
                        "varchar_vs_text",
                        "suggestion",
                        "数据类型",
                        f"字段 {t.name}.{c.name} 使用 VARCHAR({c.length})",
                        "长文本建议改用 TEXT 类型（MySQL 中 VARCHAR(255+) 与 TEXT 行内存储差异明显）",
                        table=t.name,
                        column=c.name,
                    )
                )
    return out


def _lint_redundant_index(schema: ParsedSchema) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in schema.tables:
        seen: dict[str, list[str]] = {}
        for idx in t.indexes or []:
            key = "|".join((idx.get("columns") or []))
            if not key:
                continue
            seen.setdefault(key, []).append(str(idx.get("name") or "unnamed"))
        for key, names in seen.items():
            if len(names) > 1:
                out.append(
                    _finding(
                        "redundant_index",
                        "suggestion",
                        "索引",
                        f"表 {t.name} 存在重复索引（{key}）：{', '.join(names)}",
                        "保留一个索引，删除其余重复索引以降低写入开销",
                        table=t.name,
                    )
                )
    return out
