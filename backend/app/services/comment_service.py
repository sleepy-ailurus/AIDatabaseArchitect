"""AI comment generation for tables / columns lacking comments (feature 3)."""
from __future__ import annotations

import json

from app.services.llm_service import LLMSettings, complete_json
from app.services.schema_parser import ParsedSchema


def _missing(schema: ParsedSchema) -> tuple[list[dict], list[dict]]:
    """Return (tables, columns) that are missing comments."""
    tables = [
        {"name": t.name, "comment": t.comment}
        for t in schema.tables
        if not (t.comment or "").strip()
    ]
    columns = [
        {
            "table": t.name,
            "column": c.name,
            "type": c.data_type,
            "comment": c.comment,
            "pk": c.is_primary_key,
            "fk": any(
                fk.get("source_column") == c.name for fk in (t.foreign_keys or [])
            ),
        }
        for t in schema.tables
        for c in t.columns
        if not (c.comment or "").strip()
    ]
    return tables, columns


def _prompt(tables: list[dict], columns: list[dict]) -> str:
    return (
        "为以下数据库表和字段生成简洁、准确的中文注释。\n"
        "要求：\n"
        "1. 表注释一句话概括该表业务含义（10~30 字）。\n"
        "2. 字段注释说明业务含义（5~25 字），避免照抄字段名。\n"
        "3. 只输出 JSON：{\"tables\":[{\"name\":\"表名\",\"comment\":\"注释\"}],"
        "\"columns\":[{\"table\":\"表名\",\"column\":\"字段名\",\"comment\":\"注释\"}]}\n"
        f"表：{json.dumps(tables, ensure_ascii=False)}\n"
        f"字段：{json.dumps(columns, ensure_ascii=False)}"
    )


def _merge_result(payload) -> tuple[dict[str, str], dict[tuple[str, str], str]]:
    tables: dict[str, str] = {}
    columns: dict[tuple[str, str], str] = {}
    if not isinstance(payload, dict):
        return tables, columns
    for item in payload.get("tables") or []:
        if isinstance(item, dict) and item.get("name") and item.get("comment"):
            tables[str(item["name"])] = str(item["comment"])[:200]
    for item in payload.get("columns") or []:
        if isinstance(item, dict) and item.get("table") and item.get("column") and item.get("comment"):
            columns[(str(item["table"]), str(item["column"]))] = str(item["comment"])[:200]
    return tables, columns


def generate_comment_suggestions(
    schema: ParsedSchema,
    settings: LLMSettings,
    table_chunk_size: int = 6,
    column_chunk_size: int = 40,
) -> dict:
    """Generate suggestions for missing comments in batched LLM calls.

    Returns {"tables": [{name, comment}], "columns": [{table, column, comment}],
             "errors": [str]}
    """
    missing_tables, missing_columns = _missing(schema)
    table_out: list[dict] = []
    column_out: list[dict] = []
    errors: list[str] = []

    for i in range(0, len(missing_tables), table_chunk_size):
        chunk = missing_tables[i : i + table_chunk_size]
        try:
            payload = complete_json(
                settings,
                system_prompt=(
                    "你是数据库文档专家。根据表名、字段名和类型推断业务含义，"
                    "生成简洁准确的中文注释。只输出 JSON。"
                ),
                user_prompt=_prompt(chunk, []),
            )
            tables, _ = _merge_result(payload)
            for item in chunk:
                if item["name"] in tables:
                    table_out.append({"name": item["name"], "comment": tables[item["name"]]})
        except Exception as exc:
            errors.append(f"表注释批次失败: {exc}")

    for i in range(0, len(missing_columns), column_chunk_size):
        chunk = missing_columns[i : i + column_chunk_size]
        try:
            payload = complete_json(
                settings,
                system_prompt=(
                    "你是数据库文档专家。根据表名、字段名、类型和主外键信息推断字段业务含义，"
                    "生成简洁准确的中文注释。只输出 JSON。"
                ),
                user_prompt=_prompt([], chunk),
            )
            _, columns = _merge_result(payload)
            for item in chunk:
                key = (item["table"], item["column"])
                if key in columns:
                    column_out.append(
                        {"table": item["table"], "column": item["column"], "comment": columns[key]}
                    )
        except Exception as exc:
            errors.append(f"字段注释批次失败: {exc}")

    return {"tables": table_out, "columns": column_out, "errors": errors}


def _escape_sql(value: str) -> str:
    return (value or "").replace("\\", "\\\\").replace("'", "''")


def build_writeback_sql(
    schema: ParsedSchema,
    accepted: list[dict],
    db_type: str = "mysql",
) -> list[str]:
    """Generate ALTER / COMMENT statements for accepted comment suggestions."""
    tables_by_name = {t.name.lower(): t for t in schema.tables}
    stmts: list[str] = []
    is_mysql = str(db_type).lower() == "mysql"

    for row in accepted or []:
        table = tables_by_name.get(str(row.get("table_name") or "").lower())
        if table is None:
            continue
        comment = str(row.get("suggested_comment") or "")
        if not comment:
            continue
        if row.get("target_type") == "table":
            if is_mysql:
                stmts.append(
                    f"ALTER TABLE `{table.name}` COMMENT = '{_escape_sql(comment)}';"
                )
            else:
                stmts.append(f'COMMENT ON TABLE "{table.name}" IS \'{_escape_sql(comment)}\';')
            continue

        col_name = str(row.get("column_name") or "")
        col = next((c for c in table.columns if c.name == col_name), None)
        if col is None:
            continue
        if is_mysql:
            nullable = "NULL" if col.nullable else "NOT NULL"
            type_str = col.data_type + (f"({col.length})" if col.length else "")
            default = ""
            if col.default_value and col.default_value.upper() not in ("NULL", "CURRENT_TIMESTAMP"):
                default = f" DEFAULT {col.default_value}"
            stmts.append(
                f"ALTER TABLE `{table.name}` MODIFY COLUMN `{col.name}` "
                f"{type_str} {nullable}{default} COMMENT '{_escape_sql(comment)}';"
            )
        else:
            stmts.append(
                f'COMMENT ON COLUMN "{table.name}"."{col.name}" IS \'{_escape_sql(comment)}\';'
            )
    return stmts
