"""MySQL schema parsing using SQLAlchemy's reflection / inspect().

Connects to the *user's* MySQL database (not the platform SQLite) and reads
table/column/index/foreign-key metadata. Connection errors are classified so
the API can return meaningful messages to the user.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.services.crypto import decrypt


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class SchemaParseError(Exception):
    """Base error with a classified reason code."""

    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        self.detail = detail
        super().__init__(detail or reason)


# ---------------------------------------------------------------------------
# Normalized schema data structures
# ---------------------------------------------------------------------------
@dataclass
class ParsedColumn:
    name: str
    data_type: str
    length: int | None = None
    nullable: bool = True
    default_value: str | None = None
    is_primary_key: bool = False
    is_unique: bool = False
    comment: str | None = None


@dataclass
class ParsedTable:
    name: str
    comment: str | None = None
    engine: str | None = None
    columns: list[ParsedColumn] = field(default_factory=list)
    indexes: list[dict] = field(default_factory=list)
    foreign_keys: list[dict] = field(default_factory=list)


@dataclass
class ParsedSchema:
    database_name: str
    db_version: str | None = None
    tables: list[ParsedTable] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "database_name": self.database_name,
            "db_version": self.db_version,
            "tables": [
                {
                    "name": t.name,
                    "comment": t.comment,
                    "engine": t.engine,
                    "columns": [c.__dict__ for c in t.columns],
                    "indexes": t.indexes,
                    "foreign_keys": t.foreign_keys,
                }
                for t in self.tables
            ],
        }


# ---------------------------------------------------------------------------
# Connection string builder
# ---------------------------------------------------------------------------
def build_mysql_url(
    host: str,
    port: int | str,
    database: str,
    username: str,
    password: str | None,
    ssl: bool = False,
    timeout: int = 30,
) -> str:
    pwd = password or ""
    from urllib.parse import quote_plus

    encoded_pwd = quote_plus(pwd)
    port_int = int(port)
    url = f"mysql+pymysql://{username}:{encoded_pwd}@{host}:{port_int}/{database}?charset=utf8mb4"
    connect_args: dict[str, Any] = {"connect_timeout": min(timeout, 30)}
    if ssl:
        connect_args["ssl"] = {}
    return url, connect_args


def _classify_operational_error(exc: Exception) -> str:
    """Map a raw DBAPI error to a friendly reason code."""
    msg = str(exc).lower()
    if "timed out" in msg or "timeout" in msg or "can't connect" in msg:
        return "network_unreachable"
    if "access denied" in msg or "authentication" in msg or "password" in msg:
        return "auth_failed"
    if "unknown database" in msg or "1049" in msg:
        return "database_not_found"
    if "ssl" in msg:
        return "ssl_error"
    if "permission" in msg or "denied" in msg or "access" in msg:
        return "permission_denied"
    if "invalid literal" in msg or "nodename nor servname" in msg or "getaddrinfo" in msg or "connection refused" in msg:
        return "network_unreachable"
    return "connection_error"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def test_connection(
    host: str,
    port: int | str,
    database: str,
    username: str,
    password: str | None,
    ssl: bool = False,
    timeout: int = 30,
) -> dict:
    """Test a MySQL connection and return diagnostics.

    Returns a dict with: success, message, db_version, table_count, elapsed_ms,
    checks (list of {name, status, detail, time}).
    """
    checks: list[dict] = [
        {"name": "网络可达性", "status": "idle", "detail": "", "time": None},
        {"name": "账号认证", "status": "idle", "detail": "", "time": None},
        {"name": "数据库存在性", "status": "idle", "detail": "", "time": None},
        {"name": "权限检查（只读）", "status": "idle", "detail": "需要 SELECT 权限", "time": None},
        {"name": "SSL 握手（如启用）", "status": "idle", "detail": "", "time": None},
        {"name": "Schema 元数据读取", "status": "idle", "detail": "读取 INFORMATION_SCHEMA", "time": None},
    ]

    start = time.time()
    url, connect_args = build_mysql_url(host, port, database, username, password, ssl, timeout)

    try:
        engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "success": False,
            "message": f"连接配置无效: {exc}",
            "db_version": None,
            "table_count": None,
            "elapsed_ms": int((time.time() - start) * 1000),
            "checks": checks,
        }

    # Network + auth + db existence happen together at connect time, so we
    # mark them progressively based on the classified error.
    inspector = None
    try:
        with engine.connect() as conn:
            checks[0] = {"name": "网络可达性", "status": "passing", "detail": "已建立 TCP 连接", "time": _ms(start)}
            checks[1] = {"name": "账号认证", "status": "passing", "detail": "认证成功", "time": _ms(start)}
            checks[2] = {
                "name": "数据库存在性",
                "status": "passing",
                "detail": f"数据库 {database} 存在",
                "time": _ms(start),
            }
            version = ""
            try:
                version = conn.execute(text("SELECT VERSION()")).scalar() or ""
            except Exception:
                version = ""
            checks[3] = {"name": "权限检查（只读）", "status": "passing", "detail": "权限满足要求", "time": _ms(start)}
            checks[4] = {
                "name": "SSL 握手（如启用）",
                "status": "passing",
                "detail": "已建立加密连接" if ssl else "未启用 SSL",
                "time": _ms(start),
            }

            inspector = inspect(conn)
            table_names = inspector.get_table_names()
            checks[5] = {
                "name": "Schema 元数据读取",
                "status": "passing",
                "detail": f"发现 {len(table_names)} 张表",
                "time": _ms(start),
            }

            return {
                "success": True,
                "message": "连接成功",
                "db_version": version,
                "table_count": len(table_names),
                "elapsed_ms": int((time.time() - start) * 1000),
                "checks": checks,
            }
    except OperationalError as exc:
        reason = _classify_operational_error(exc)
        msg = str(exc.args[0]) if exc.args else str(exc)
        # Mark the appropriate check as failed based on the reason.
        idx_map = {
            "network_unreachable": 0,
            "auth_failed": 1,
            "database_not_found": 2,
            "ssl_error": 4,
            "permission_denied": 3,
        }
        idx = idx_map.get(reason, 0)
        checks[idx] = {"name": checks[idx]["name"], "status": "failed", "detail": _friendly(reason, msg), "time": _ms(start)}
        return {
            "success": False,
            "message": _friendly(reason, msg),
            "db_version": None,
            "table_count": None,
            "elapsed_ms": int((time.time() - start) * 1000),
            "checks": checks,
        }
    except SQLAlchemyError as exc:
        return {
            "success": False,
            "message": f"数据库错误: {exc}",
            "db_version": None,
            "table_count": None,
            "elapsed_ms": int((time.time() - start) * 1000),
            "checks": checks,
        }
    finally:
        if inspector is not None:
            try:
                inspector.dispose()
            except Exception:
                pass
        engine.dispose()


def _ms(start: float) -> int:
    return int((time.time() - start) * 1000)


def _friendly(reason: str, raw: str) -> str:
    mapping = {
        "network_unreachable": "网络不可达：无法连接到数据库主机，请检查地址、端口和网络是否正确，MySQL 服务是否已启动",
        "auth_failed": "认证失败：用户名或密码错误",
        "database_not_found": "数据库不存在：请确认数据库名称",
        "ssl_error": "SSL 配置错误：无法建立加密连接",
        "permission_denied": "权限不足：账号缺少必要权限",
        "connection_error": f"连接失败：{raw}",
    }
    return mapping.get(reason, raw)


def parse_schema(
    host: str,
    port: int | str,
    database: str,
    username: str,
    password: str | None,
    ssl: bool = False,
    timeout: int = 30,
) -> ParsedSchema:
    """Connect to MySQL and reflect the full schema as a ParsedSchema."""
    url, connect_args = build_mysql_url(host, port, database, username, password, ssl, timeout)
    try:
        engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    except Exception as exc:
        raise SchemaParseError("connection_error", f"连接配置无效: {exc}") from exc

    schema = ParsedSchema(database_name=database)
    try:
        with engine.connect() as conn:
            try:
                schema.db_version = conn.execute(text("SELECT VERSION()")).scalar()
            except Exception:
                schema.db_version = None

            inspector = inspect(conn)
            for table_name in inspector.get_table_names():
                ptable = ParsedTable(name=table_name)

                # Table comment + engine (MySQL specific via dialect options).
                try:
                    table_options = inspector.get_table_options(table_name) or {}
                    ptable.engine = table_options.get("mysql_engine")
                    ptable.comment = table_options.get("mysql_comment")
                except Exception:
                    pass

                # Foreign keys (explicit constraints) -> captured before columns.
                fk_columns: set[str] = set()
                for fk in inspector.get_foreign_keys(table_name):
                    referred_table = fk.get("referred_table")
                    constrained = fk.get("constrained_columns") or []
                    referred = fk.get("referred_columns") or []
                    source_col = constrained[0] if constrained else None
                    target_col = referred[0] if referred else None
                    if source_col:
                        fk_columns.add(source_col)
                    ptable.foreign_keys.append(
                        {
                            "name": fk.get("name"),
                            "source_column": source_col,
                            "target_table": referred_table,
                            "target_column": target_col,
                            "constraint_name": fk.get("name"),
                        }
                    )

                # Primary keys + unique indexes for column flags.
                # NOTE: Only single-column UNIQUE indexes qualify a column as "is_unique".
                # Multi-column (composite) UNIQUE indexes do NOT guarantee uniqueness of
                # each column independently — they should NOT contribute to is_unique.
                # e.g. UNIQUE(a,b,c) → a is not globally unique alone; only (a,b,c) tuple is.
                pk_cols = set(inspector.get_pk_constraint(table_name).get("constrained_columns") or [])
                unique_cols: set[str] = set()
                for idx in inspector.get_indexes(table_name):
                    idx_cols = list(idx.get("column_names") or [])
                    ptable.indexes.append(
                        {
                            "name": idx.get("name"),
                            "columns": idx_cols,
                            "unique": bool(idx.get("unique", False)),
                        }
                    )
                    if idx.get("unique") and len(idx_cols) == 1:
                        unique_cols.add(idx_cols[0])

                # Columns.
                for col in inspector.get_columns(table_name):
                    col_name = col.get("name", "")
                    type_obj = col.get("type")
                    type_str = str(type_obj) if type_obj is not None else ""
                    length = _extract_length(type_str)
                    base_type = _base_type(type_str)
                    ptable.columns.append(
                        ParsedColumn(
                            name=col_name,
                            data_type=base_type,
                            length=length,
                            nullable=bool(col.get("nullable", True)),
                            default_value=_stringify_default(col.get("default")),
                            is_primary_key=col_name in pk_cols,
                            is_unique=col_name in unique_cols,
                            comment=col.get("comment"),
                        )
                    )
                schema.tables.append(ptable)
        return schema
    except OperationalError as exc:
        raise SchemaParseError(_classify_operational_error(exc), _friendly(_classify_operational_error(exc), str(exc))) from exc
    except SQLAlchemyError as exc:
        raise SchemaParseError("connection_error", f"读取 Schema 失败: {exc}") from exc
    finally:
        engine.dispose()


def _stringify_default(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


_LENGTH_RE = re.compile(r"\((\d+)(?:,\s*\d+)?\)")


def _extract_length(type_str: str) -> int | None:
    m = _LENGTH_RE.search(type_str)
    return int(m.group(1)) if m else None


def _base_type(type_str: str) -> str:
    """Return the upper-case base type without length, e.g. VARCHAR(32) -> VARCHAR."""
    return re.split(r"[( ]", type_str, maxsplit=1)[0].upper()


def schema_from_dict(data: dict) -> ParsedSchema:
    """Reconstruct a ParsedSchema from a serialized snapshot dict."""
    schema = ParsedSchema(
        database_name=data.get("database_name", ""),
        db_version=data.get("db_version"),
    )
    for t in data.get("tables", []):
        ptable = ParsedTable(
            name=t.get("name", ""),
            comment=t.get("comment"),
            engine=t.get("engine"),
        )
        for c in t.get("columns", []):
            ptable.columns.append(
                ParsedColumn(
                    name=c.get("name", ""),
                    data_type=c.get("data_type", ""),
                    length=c.get("length"),
                    nullable=c.get("nullable", True),
                    default_value=c.get("default_value"),
                    is_primary_key=c.get("is_primary_key", False),
                    is_unique=c.get("is_unique", False),
                    comment=c.get("comment"),
                )
            )
        ptable.indexes = t.get("indexes", []) or []
        ptable.foreign_keys = t.get("foreign_keys", []) or []
        schema.tables.append(ptable)
    return schema


def is_type_compatible(a: str, b: str) -> bool:
    """Heuristic type compatibility check for candidate relation generation."""
    a = (a or "").upper()
    b = (b or "").upper()
    if not a or not b:
        return True
    if a == b:
        return True

    # Numeric families.
    int_types = {"INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT", "MEDIUMINT"}
    if a in int_types and b in int_types:
        return True
    if a in int_types and b in {"DECIMAL", "NUMERIC", "FLOAT", "DOUBLE"}:
        return True
    if b in int_types and a in {"DECIMAL", "NUMERIC", "FLOAT", "DOUBLE"}:
        return True

    string_types = {"VARCHAR", "CHAR", "TEXT", "TINYTEXT", "MEDIUMTEXT", "LONGTEXT"}
    if a in string_types and b in string_types:
        return True

    # Fall back to base-type prefix match (e.g. VARCHAR vs VARCHAR).
    return a.split("(")[0] == b.split("(")[0]
