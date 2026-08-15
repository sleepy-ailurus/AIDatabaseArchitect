"""Smart test data generator - schema-aware, FK-preserving sample data (feature 8)."""
from __future__ import annotations

import random
import string
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any

from app.services.schema_parser import ParsedSchema


_SURNAMES = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
_GIVEN = "伟芳娜敏静丽强磊军洋勇艳杰娟涛明超秀兰霞平刚桂英梅鑫鹏华玉红"
_CITIES = [
    "北京市", "上海市", "广州市", "深圳市", "杭州市", "成都市", "武汉市", "西安市",
    "南京市", "重庆市", "苏州市", "天津市", "长沙市", "青岛市", "郑州市", "沈阳市",
]
_STREETS = ["人民路", "中山路", "建设路", "解放路", "文化路", "学院路", "科技路", "幸福路"]


def _random_name() -> str:
    return random.choice(_SURNAMES) + "".join(
        random.choice(_GIVEN) for _ in range(random.randint(1, 2))
    )


def _random_mobile() -> str:
    return "1" + random.choice("3456789") + "".join(str(random.randint(0, 9)) for _ in range(9))


def _random_email(name: str = "") -> str:
    local = (name or "user" + str(random.randint(100, 999))).lower().replace(" ", "")
    return f"{local}@example.com"


def _random_id_card() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(17)) + random.choice("0123456789X")


def _random_address() -> str:
    return (
        random.choice(_CITIES)
        + random.choice(_STREETS)
        + str(random.randint(1, 200))
        + "号"
    )


def _random_datetime() -> datetime:
    now = datetime.now()
    return now - timedelta(days=random.randint(0, 365 * 3), hours=random.randint(0, 23))


def _default_value(col) -> str | None:
    if col.default_value and col.default_value.upper() not in ("NULL", "CURRENT_TIMESTAMP", "NOW()"):
        return col.default_value
    return None


def _column_generator(col, table_row_idx: int, fk_target_rows: dict[str, list[int]]):
    """Return a callable generating a value for a single column."""
    name = (col.name or "").lower()
    comment = (col.comment or "").lower()
    dtype = (col.data_type or "").upper()

    if col.is_primary_key:
        return lambda: table_row_idx + 1

    if any(k in name for k in ("mobile", "phone", "tel", "手机", "电话")):
        return lambda: _random_mobile()
    if any(k in name for k in ("email", "mail", "邮箱")):
        return lambda: _random_email()
    if any(k in name for k in ("id_card", "idcard", "identity", "sfz", "身份证")):
        return lambda: _random_id_card()
    if any(k in name for k in ("password", "passwd", "pwd", "密码", "口令")):
        return lambda: "$2b$12$" + "".join(random.choice(string.ascii_letters + string.digits) for _ in range(50))
    if any(k in name for k in ("token", "api_key", "secret", "密钥")):
        return lambda: uuid.uuid4().hex
    if any(k in name for k in ("address", "addr", "地址")):
        return lambda: _random_address()
    if any(k in name for k in ("avatar", "image", "img", "photo", "图片", "头像")):
        return lambda: f"https://example.com/static/img/{random.randint(1, 999)}.png"
    if any(k in name for k in ("status", "state", "type", "状态", "类型")):
        def _status():
            if dtype in ("TINYINT", "INT", "SMALLINT"):
                return str(random.choice([0, 1, 2]))
            return random.choice(["active", "disabled", "pending", "正常", "停用"])
        return _status
    if any(k in name for k in ("price", "amount", "money", "fee", "total", "价格", "金额", "费用")):
        return lambda: f"{random.randint(1, 9999)}.{random.randint(0, 99):02d}"
    if dtype in ("DATETIME", "TIMESTAMP", "DATE", "TIME"):
        return lambda: _random_datetime().strftime("%Y-%m-%d %H:%M:%S")
    if dtype in ("BOOLEAN", "BOOL", "TINYINT(1)"):
        return lambda: str(random.choice([0, 1]))
    if dtype in ("BIGINT", "INT", "INTEGER", "SMALLINT", "MEDIUMINT", "SERIAL", "BIGSERIAL"):
        return lambda: str(random.randint(1, 99999))
    if dtype in ("DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL"):
        return lambda: f"{random.randint(1, 9999)}.{random.randint(0, 99):02d}"
    if dtype == "UUID":
        return lambda: str(uuid.uuid4())
    if "name" in name or "姓名" in comment or "名称" in comment:
        return lambda: _random_name()
    if dtype in ("JSON", "JSONB"):
        return lambda: '{"key": "value"}'
    default = _default_value(col)
    if default is not None:
        return lambda: default
    if dtype in ("TEXT", "LONGTEXT", "MEDIUMTEXT", "VARCHAR", "CHAR", "TINYTEXT"):
        length = col.length or 20
        return lambda: "测试数据" + "".join(random.choice(string.ascii_lowercase) for _ in range(min(6, length)))
    return lambda: "NULL"


def _topological_order(schema: ParsedSchema) -> list:
    """Order tables so FK targets come before sources (Kahn's algorithm)."""
    by_name = {t.name.lower(): t for t in schema.tables}
    indegree = {t.name: 0 for t in schema.tables}
    dependents: dict[str, list] = defaultdict(list)
    for t in schema.tables:
        for fk in t.foreign_keys or []:
            target = by_name.get(str(fk.get("target_table") or "").lower())
            if target and target.name.lower() != t.name.lower():
                indegree[t.name] += 1
                dependents[target.name].append(t.name)
    queue = deque([t.name for t in schema.tables if indegree[t.name] == 0])
    order: list[str] = []
    while queue:
        name = queue.popleft()
        order.append(name)
        for dep in dependents[name]:
            indegree[dep] -= 1
            if indegree[dep] == 0:
                queue.append(dep)
    # Remaining tables participate in cycles; append them last.
    for t in schema.tables:
        if t.name not in order:
            order.append(t.name)
    return order


def generate_insert_sql(
    schema: ParsedSchema,
    rows_per_table: int = 10,
    db_type: str = "mysql",
) -> dict[str, Any]:
    """Generate INSERT statements for every table preserving FK integrity."""
    tables_by_name = {t.name.lower(): t for t in schema.tables}
    order = _topological_order(schema)
    pk_values: dict[str, list[int]] = {}  # table -> generated PK values
    statements: list[str] = []
    row_counts: dict[str, int] = {}

    is_mysql = str(db_type).lower() == "mysql"
    if is_mysql:
        statements.append("SET FOREIGN_KEY_CHECKS = 0;")

    for tname in order:
        table = tables_by_name.get(tname.lower())
        if table is None:
            continue
        fk_map = {}
        for fk in table.foreign_keys or []:
            target = tables_by_name.get(str(fk.get("target_table") or "").lower())
            if target:
                fk_map[str(fk.get("source_column") or "").lower()] = (
                    target.name,
                    pk_values.get(target.name, []),
                )

        cols = table.columns
        col_names = [c.name for c in cols]
        generated: list[list[str]] = []
        for idx in range(rows_per_table):
            row: list[str] = []
            for c in cols:
                key = c.name.lower()
                if key in fk_map:
                    target_table, values = fk_map[key]
                    if values:
                        row.append(str(random.choice(values)))
                    else:
                        row.append("NULL")
                    continue
                gen = _column_generator(c, idx, pk_values)
                try:
                    val = gen()
                except Exception:
                    val = "NULL"
                if val is None or str(val).upper() == "NULL":
                    row.append("NULL")
                elif isinstance(val, bool):
                    row.append("1" if val else "0")
                elif isinstance(val, (int, float)):
                    row.append(str(val))
                elif isinstance(val, str) and (
                    val.isdigit()
                    or val.replace(".", "", 1).isdigit()
                    or val.upper() in ("TRUE", "FALSE")
                    or (is_mysql and val in ("CURRENT_TIMESTAMP",))
                ):
                    row.append(val)
                else:
                    escaped = val.replace("\\", "\\\\").replace("'", "''")
                    row.append(f"'{escaped}'")
            generated.append(row)

        if table.columns and any(c.is_primary_key for c in table.columns):
            pk_col = next(c for c in table.columns if c.is_primary_key)
            pk_values[table.name] = list(range(1, rows_per_table + 1))

        qname = f"`{table.name}`" if is_mysql else f'"{table.name}"'
        statements.append(
            f"INSERT INTO {qname} ({', '.join(col_names)}) VALUES\n"
            + ",\n".join(f"({', '.join(row)})" for row in generated)
            + ";"
        )
        row_counts[table.name] = rows_per_table

    if is_mysql:
        statements.append("SET FOREIGN_KEY_CHECKS = 1;")
    return {"sql": statements, "row_counts": row_counts}


def execute_sql(engine, statements: list[str]) -> dict[str, Any]:
    """Execute generated statements inside a single transaction."""
    from sqlalchemy import text

    executed = 0
    try:
        with engine.begin() as tx:
            for stmt in statements:
                if stmt.strip().startswith("SET FOREIGN_KEY_CHECKS"):
                    tx.execute(text(stmt))
                    continue
                tx.execute(text(stmt))
                executed += 1
    except Exception as exc:
        return {"executed": executed, "error": str(exc)}
    return {"executed": executed, "error": None}
