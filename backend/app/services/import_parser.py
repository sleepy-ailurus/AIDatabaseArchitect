"""Parse DDL text / DBML files into a ParsedSchema without a database connection.

- DDL (MySQL / PostgreSQL CREATE TABLE) is parsed with sqlglot (modern, actively
  maintained SQL parser) so legacy regex-based parsing is avoided.
- DBML (dbdiagram.io format) is parsed with a small dedicated parser.
"""
from __future__ import annotations

import re
from typing import Any

import sqlglot

from app.services.schema_parser import ParsedColumn, ParsedSchema, ParsedTable, _base_type, _extract_length


class ImportParseError(Exception):
    """Raised when the provided DDL / DBML cannot be understood."""


# ---------------------------------------------------------------------------
# Small AST helpers (sqlglot)
# ---------------------------------------------------------------------------
def _id_name(node: Any) -> str:
    if node is None:
        return ""
    if hasattr(node, "name") and node.name:
        return node.name
    if hasattr(node, "this") and node.this is not None and node.this is not node:
        return _id_name(node.this)
    return str(node)


def _unwrap_column_constraint(c) -> Any:
    """ColumnConstraint wraps the actual constraint in its `kind` arg."""
    if isinstance(c, sqlglot.exp.ColumnConstraint) and c.args.get("kind") is not None:
        return c.args["kind"]
    return c


def _literal_text(node: Any) -> str | None:
    if node is None:
        return None
    if isinstance(node, sqlglot.exp.Null):
        return None
    if isinstance(node, sqlglot.exp.Literal):
        val = node.this
        return None if val is None else str(val)
    if isinstance(node, sqlglot.exp.Var):
        return node.name
    if hasattr(node, "sql"):
        return node.sql()
    return str(node)


def _expr_columns(expr: Any) -> list[str]:
    """Extract column names from PrimaryKey / Unique / Index / ForeignKey nodes."""
    cols: list[str] = []
    for item in expr.args.get("expressions") or []:
        name = _id_name(item)
        if name:
            cols.append(name)
    return cols


def _ref_columns(ref: Any) -> list[str]:
    """Extract referenced columns from a Reference node (table columns live on ref.this)."""
    if ref is None:
        return []
    if isinstance(ref.this, sqlglot.exp.Schema):
        return _expr_columns(ref.this)
    return _expr_columns(ref)


# ---------------------------------------------------------------------------
# DDL parsing
# ---------------------------------------------------------------------------
def _parse_column(col_def) -> ParsedColumn:
    name = _id_name(col_def.args.get("this"))
    kind = col_def.args.get("kind")
    type_str = kind.sql(dialect="mysql") if kind is not None else ""
    nullable = True
    default_value: str | None = None
    comment: str | None = None

    for c in col_def.args.get("constraints") or []:
        k = _unwrap_column_constraint(c)
        if isinstance(k, sqlglot.exp.NotNullColumnConstraint):
            nullable = False
        elif isinstance(k, sqlglot.exp.DefaultColumnConstraint):
            default_value = _literal_text(k.args.get("this"))
        elif isinstance(k, sqlglot.exp.CommentColumnConstraint):
            comment = _literal_text(k.args.get("this"))

    return ParsedColumn(
        name=name,
        data_type=_base_type(type_str),
        length=_extract_length(type_str),
        nullable=nullable,
        default_value=default_value,
        is_primary_key=False,
        is_unique=False,
        comment=comment,
    )


def parse_ddl(ddl_text: str, db_type: str = "mysql") -> ParsedSchema:
    """Parse CREATE TABLE statements into a ParsedSchema."""
    if not ddl_text or not ddl_text.strip():
        raise ImportParseError("DDL 内容为空")
    try:
        read_dialect = "postgres" if str(db_type).lower() == "postgresql" else "mysql"
        expressions = sqlglot.parse(ddl_text, read=read_dialect)
    except Exception as exc:
        raise ImportParseError(f"DDL 解析失败: {exc}") from exc

    schema = ParsedSchema(database_name="imported")
    dialect = "mysql" if str(db_type).lower() == "mysql" else "postgresql"

    for expr in expressions:
        if expr is None or not isinstance(expr, sqlglot.exp.Create):
            continue
        kind = expr.args.get("kind")
        if kind is not None and str(kind) != "TABLE":
            continue
        table_schema = expr.this
        table_name = _id_name(table_schema.args.get("this"))
        if not table_name:
            continue

        ptable = ParsedTable(name=table_name)
        pk_cols: set[str] = set()
        unique_cols: set[str] = set()
        inline_refs: list[dict] = []

        # Table-level properties: ENGINE / COMMENT
        for prop in (expr.args.get("properties").expressions if expr.args.get("properties") else []) or []:
            if isinstance(prop, sqlglot.exp.EngineProperty):
                ptable.engine = _literal_text(prop.args.get("this"))
            elif isinstance(prop, sqlglot.exp.SchemaCommentProperty):
                ptable.comment = _literal_text(prop.args.get("this"))

        for item in table_schema.args.get("expressions") or []:
            if isinstance(item, sqlglot.exp.ColumnDef):
                col = _parse_column(item)
                # inline FK reference: user_id INT REFERENCES users(id)
                for c in item.args.get("constraints") or []:
                    k = _unwrap_column_constraint(c)
                    if isinstance(k, sqlglot.exp.Reference):
                        ref = k
                        if ref is not None:
                            ref_cols = _ref_columns(ref)
                            inline_refs.append(
                                {
                                    "source_column": col.name,
                                    "target_table": _id_name(ref.args.get("this")),
                                    "target_column": ref_cols[0] if ref_cols else "",
                                }
                            )
                ptable.columns.append(col)
            elif isinstance(item, sqlglot.exp.PrimaryKey):
                pk_cols.update(_expr_columns(item))
            elif isinstance(item, sqlglot.exp.UniqueColumnConstraint):
                idx_name = _id_name(item.args.get("this"))
                cols_source = item.this if isinstance(item.this, sqlglot.exp.Schema) else item
                idx_cols = _expr_columns(cols_source)
                ptable.indexes.append({"name": idx_name, "columns": idx_cols, "unique": True})
                if len(idx_cols) == 1:
                    unique_cols.add(idx_cols[0])
            elif isinstance(item, sqlglot.exp.IndexColumnConstraint):
                idx_name = _id_name(item.args.get("this"))
                idx_cols = _expr_columns(item)
                ptable.indexes.append({"name": idx_name, "columns": idx_cols, "unique": False})
            elif isinstance(item, sqlglot.exp.Constraint):
                constraint_name = _id_name(item.args.get("this"))
                for inner in item.args.get("expressions") or []:
                    if isinstance(inner, sqlglot.exp.ForeignKey):
                        fk_cols = _expr_columns(inner)
                        ref = inner.args.get("reference")
                        target_table = _id_name(ref.args.get("this")) if ref is not None else ""
                        target_cols = _ref_columns(ref)
                        for i, fk_col in enumerate(fk_cols):
                            ptable.foreign_keys.append(
                                {
                                    "name": constraint_name,
                                    "source_column": fk_col,
                                    "target_table": target_table,
                                    "target_column": (target_cols[i] if i < len(target_cols) else (target_cols[0] if target_cols else "")),
                                    "constraint_name": constraint_name,
                                }
                            )

        # Inline references append after explicit FKs.
        for ref in inline_refs:
            if ref["target_table"]:
                ptable.foreign_keys.append(
                    {
                        "name": None,
                        "source_column": ref["source_column"],
                        "target_table": ref["target_table"],
                        "target_column": ref["target_column"],
                        "constraint_name": None,
                    }
                )

        for col in ptable.columns:
            if col.name in pk_cols:
                col.is_primary_key = True
            if col.name in unique_cols:
                col.is_unique = True

        schema.tables.append(ptable)

    # Apply standalone COMMENT ON statements (PostgreSQL / MySQL syntax) so
    # comments written after CREATE TABLE are preserved.
    tables_by_name = {t.name.lower(): t for t in schema.tables}
    for expr in expressions:
        if expr is None or not isinstance(expr, sqlglot.exp.Comment):
            continue
        text = _literal_text(expr.args.get("expression"))
        if not text:
            continue
        target = expr.args.get("this")
        parts = getattr(target, "parts", None) or []
        if isinstance(target, sqlglot.exp.Column) and len(parts) >= 2:
            table = tables_by_name.get(str(parts[0].name).lower())
            if table is not None:
                col = next((c for c in table.columns if c.name == parts[-1].name), None)
                if col is not None:
                    col.comment = text
        else:
            table = tables_by_name.get(str(_id_name(target)).lower())
            if table is not None:
                table.comment = text

    if not schema.tables:
        raise ImportParseError("未解析到任何 CREATE TABLE 语句")
    return schema


# ---------------------------------------------------------------------------
# DBML parsing
# ---------------------------------------------------------------------------
_DBML_TYPE_RE = re.compile(r"^(\S+?)\s+(.+)$")


def _dbml_settings(text: str) -> dict[str, Any]:
    """Parse DBML column settings: [pk, unique, not null, default: 'x', ref: > t.c, note: '...']"""
    settings: dict[str, Any] = {
        "pk": False,
        "unique": False,
        "not null": False,
        "default": None,
        "ref": None,
        "note": None,
    }
    text = text.strip()
    if not (text.startswith("[") and text.endswith("]")):
        return settings
    body = text[1:-1]
    parts: list[str] = []
    buf = ""
    quote = None
    for ch in body:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            buf += ch
        elif ch == ",":
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())

    for part in parts:
        low = part.lower()
        if low == "pk":
            settings["pk"] = True
        elif low == "unique":
            settings["unique"] = True
        elif low == "not null":
            settings["not null"] = True
        elif low.startswith("default:"):
            settings["default"] = part.split(":", 1)[1].strip().strip("'\"")
        elif low.startswith("ref:"):
            settings["ref"] = part.split(":", 1)[1].strip()
        elif low.startswith("note:"):
            settings["note"] = part.split(":", 1)[1].strip().strip("'\"")
    return settings


def _parse_ref_spec(spec: str) -> dict[str, str] | None:
    """Parse 'table.column > table.column' (also < and -)."""
    spec = spec.strip()
    for arrow in (">", "<", "-"):
        if arrow in spec:
            left, right = spec.split(arrow, 1)
            left_parts = left.strip().split(".")
            right_parts = right.strip().split(".")
            if len(left_parts) == 2 and len(right_parts) == 2:
                return {
                    "source_table": left_parts[0].strip(),
                    "source_column": left_parts[1].strip(),
                    "target_table": right_parts[0].strip(),
                    "target_column": right_parts[1].strip(),
                    "arrow": arrow,
                }
    return None


def parse_dbml(dbml_text: str) -> ParsedSchema:
    """Parse a DBML document into a ParsedSchema."""
    if not dbml_text or not dbml_text.strip():
        raise ImportParseError("DBML 内容为空")

    schema = ParsedSchema(database_name="imported")
    table_by_name: dict[str, ParsedTable] = {}
    refs: list[dict[str, str]] = []
    lines = dbml_text.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("//") or line.startswith("#"):
            continue

        # Table block: Table name { ... }
        table_match = re.match(r"^Table\s+([`\"']?)([^`\"'{\s]+)\1\s*\{", line)
        if table_match:
            tname = table_match.group(2)
            ptable = ParsedTable(name=tname)
            pk_cols: set[str] = set()
            unique_cols: set[str] = set()
            pending = line[table_match.end():]
            while i < n:
                if pending is not None and pending.strip():
                    inner = pending
                    pending = None
                else:
                    pending = None
                    inner = lines[i].strip()
                    i += 1
                if "}" in inner:
                    inner = inner.split("}", 1)[0]
                    if not inner.strip():
                        break
                inner = inner.strip()
                if not inner or inner.startswith("//"):
                    continue
                if "[" in inner:
                    name_type, _, settings_text = inner.partition("[")
                    settings = _dbml_settings("[" + settings_text)
                else:
                    name_type, settings = inner, _dbml_settings("")
                parts = name_type.strip().split(None, 1)
                if len(parts) < 2:
                    continue
                col_name, col_type = parts[0], parts[1]
                if settings["pk"]:
                    pk_cols.add(col_name)
                if settings["unique"]:
                    unique_cols.add(col_name)
                ptable.columns.append(
                    ParsedColumn(
                        name=col_name,
                        data_type=_base_type(col_type),
                        length=_extract_length(col_type),
                        nullable=not settings["not null"],
                        default_value=settings["default"],
                        is_primary_key=False,
                        is_unique=False,
                        comment=settings["note"],
                    )
                )
                if settings["ref"]:
                    parsed = _parse_ref_spec(settings["ref"])
                    if parsed is None and str(settings["ref"]).startswith(">"):
                        right = str(settings["ref"])[1:].strip().split(".")
                        if len(right) == 2:
                            parsed = {
                                "source_table": tname,
                                "source_column": col_name,
                                "target_table": right[0].strip(),
                                "target_column": right[1].strip(),
                                "arrow": ">",
                            }
                    if parsed:
                        parsed["source_table"] = tname
                        parsed["source_column"] = col_name
                        refs.append(parsed)
            for col in ptable.columns:
                col.is_primary_key = col.name in pk_cols
                col.is_unique = col.name in unique_cols
            table_by_name[tname] = ptable
            schema.tables.append(ptable)
            continue

        # Ref line: Ref: table.col > table.col
        if line.startswith("Ref:"):
            spec = line[len("Ref:"):].strip()
            # Ref: name [settings] form has no >/< arrow; skip those
            parsed = _parse_ref_spec(spec)
            if parsed:
                refs.append(parsed)
            continue

        # ignore enums / projects / other top-level blocks

    for ref in refs:
        src_t = table_by_name.get(ref["source_table"])
        if src_t is None:
            continue
        src_t.foreign_keys.append(
            {
                "name": None,
                "source_column": ref["source_column"],
                "target_table": ref["target_table"],
                "target_column": ref["target_column"],
                "constraint_name": None,
            }
        )

    if not schema.tables:
        raise ImportParseError("未解析到任何 Table 定义")
    return schema


def parse_schema_source(source: str, content: str, db_type: str = "mysql") -> ParsedSchema:
    """Dispatch on source: 'ddl' | 'dbml'."""
    src = str(source or "").lower()
    if src == "dbml":
        return parse_dbml(content)
    return parse_ddl(content, db_type=db_type)
