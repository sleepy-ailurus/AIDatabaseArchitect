"""SQL lineage / impact analysis (feature 7) - parse SQL text and map table deps."""
from __future__ import annotations

from typing import Any

import sqlglot

from app.services.schema_parser import ParsedSchema


def _table_name(node) -> str:
    if node is None:
        return ""
    if isinstance(node, sqlglot.exp.Table):
        return node.name or ""
    cur = node
    while cur is not None and hasattr(cur, "this"):
        name = getattr(cur, "name", None)
        if name:
            return name
        cur = cur.this
    return ""


def _extract_tables(expr) -> list[str]:
    """Collect referenced table names from FROM / JOIN clauses of an expression."""
    tables: list[str] = []
    for node in expr.walk():
        if isinstance(node, sqlglot.exp.Table):
            name = _table_name(node)
            if name and name not in tables:
                tables.append(name)
    return tables


def _statement_info(idx: int, stmt) -> dict[str, Any]:
    """Extract {type, source_tables, target_table, sql} from a statement."""
    stype = type(stmt).__name__.lower().replace("expression", "")
    target_table = ""
    source_tables: list[str] = []

    if isinstance(stmt, sqlglot.exp.Insert):
        target_table = _table_name(stmt.args.get("this"))
        source_tables = _extract_tables(stmt)
        stype = "insert"
    elif isinstance(stmt, sqlglot.exp.Update):
        target_table = _table_name(stmt.args.get("this"))
        source_tables = _extract_tables(stmt)
        stype = "update"
    elif isinstance(stmt, sqlglot.exp.Delete):
        target_table = _table_name(stmt.args.get("this"))
        source_tables = _extract_tables(stmt)
        stype = "delete"
    elif isinstance(stmt, sqlglot.exp.Select):
        source_tables = _extract_tables(stmt)
        stype = "select"
    elif isinstance(stmt, sqlglot.exp.Create):
        target_table = _table_name(stmt.args.get("this"))
        source_tables = _extract_tables(stmt)
        stype = "create"
    else:
        source_tables = _extract_tables(stmt)

    # Remove target from source list for writes.
    if target_table:
        source_tables = [t for t in source_tables if t != target_table]
    return {
        "index": idx + 1,
        "type": stype,
        "source_tables": source_tables,
        "target_table": target_table,
        "sql": stmt.sql().strip()[:500],
    }


def analyze_sql_lineage(sql_text: str, schema: ParsedSchema | None = None) -> dict[str, Any]:
    """Parse SQL text into per-statement table dependencies.

    Returns {queries, edges, unresolved, known_tables}.
    """
    known = {t.name.lower() for t in schema.tables} if schema else set()
    try:
        statements = [
            s for s in sqlglot.parse(sql_text) if s is not None
        ]
    except Exception as exc:
        return {"queries": [], "edges": [], "unresolved": [], "known_tables": sorted(known), "error": str(exc)}

    queries: list[dict] = []
    edges: list[dict] = []
    unresolved: list[str] = []

    for idx, stmt in enumerate(statements):
        info = _statement_info(idx, stmt)
        queries.append(info)
        for src in info["source_tables"]:
            edges.append(
                {
                    "from": src,
                    "to": info["target_table"] or "",
                    "query_index": idx,
                    "type": "write" if info["target_table"] else "read",
                }
            )
            if known and src.lower() not in known:
                unresolved.append(src)
        if info["target_table"] and known and info["target_table"].lower() not in known:
            unresolved.append(info["target_table"])

    return {
        "queries": queries,
        "edges": edges,
        "unresolved": sorted(set(unresolved)),
        "known_tables": sorted(known),
    }


def compute_impact(result: dict[str, Any], table: str) -> dict[str, Any]:
    """Given an analysis result, find queries/tables depending on `table`."""
    key = table.lower()
    dependent_queries = [
        q for q in result.get("queries", [])
        if key in {t.lower() for t in q.get("source_tables", [])}
        or key == (q.get("target_table") or "").lower()
    ]
    downstream_tables: list[str] = []
    for edge in result.get("edges", []):
        if edge.get("from", "").lower() == key and edge.get("to"):
            downstream_tables.append(edge["to"])
    return {
        "table": table,
        "dependent_queries": dependent_queries,
        "downstream_tables": sorted(set(downstream_tables)),
    }
