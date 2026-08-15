"""Schema snapshot diff - compare two snapshots and describe what changed."""
from __future__ import annotations

from typing import Any

from app.services.schema_parser import ParsedColumn, ParsedSchema


def _col_change(old: ParsedColumn, new: ParsedColumn) -> list[str]:
    changes: list[str] = []
    if old.data_type != new.data_type or old.length != new.length:
        changes.append(
            f"类型: {old.data_type}{f'({old.length})' if old.length else ''} → "
            f"{new.data_type}{f'({new.length})' if new.length else ''}"
        )
    if old.nullable != new.nullable:
        changes.append("可空: " + ("是→否" if old.nullable else "否→是"))
    if (old.default_value or "") != (new.default_value or ""):
        changes.append(f"默认值: {old.default_value or '无'} → {new.default_value or '无'}")
    if old.is_primary_key != new.is_primary_key:
        changes.append("主键: " + ("新增" if new.is_primary_key else "移除"))
    if old.is_unique != new.is_unique:
        changes.append("唯一: " + ("新增" if new.is_unique else "移除"))
    if (old.comment or "") != (new.comment or ""):
        changes.append(f"注释: {old.comment or '无'} → {new.comment or '无'}")
    return changes


def _index_key(idx: dict) -> str:
    return f"{idx.get('name')}|{','.join(idx.get('columns') or [])}|{bool(idx.get('unique'))}"


def _fk_key(fk: dict) -> str:
    return (
        f"{fk.get('source_column')}|{fk.get('target_table')}|{fk.get('target_column')}"
    )


def compare_schemas(old: ParsedSchema, new: ParsedSchema) -> dict[str, Any]:
    """Return a structured diff between two parsed schemas."""
    old_tables = {t.name.lower(): t for t in old.tables}
    new_tables = {t.name.lower(): t for t in new.tables}

    added: list[str] = []
    removed: list[str] = []
    changed: list[dict] = []
    unchanged: list[str] = []

    for name in sorted(new_tables.keys() - old_tables.keys()):
        added.append(new_tables[name].name)
    for name in sorted(old_tables.keys() - new_tables.keys()):
        removed.append(old_tables[name].name)

    for name in sorted(old_tables.keys() & new_tables.keys()):
        ot = old_tables[name]
        nt = new_tables[name]
        table_diff: dict[str, Any] = {
            "table": nt.name,
            "comment": None,
            "columns_added": [],
            "columns_removed": [],
            "columns_changed": [],
            "indexes_added": [],
            "indexes_removed": [],
            "fks_added": [],
            "fks_removed": [],
        }
        if (ot.comment or "") != (nt.comment or ""):
            table_diff["comment"] = {"old": ot.comment, "new": nt.comment}

        old_cols = {c.name.lower(): c for c in ot.columns}
        new_cols = {c.name.lower(): c for c in nt.columns}
        for cn in sorted(new_cols.keys() - old_cols.keys()):
            table_diff["columns_added"].append(
                {
                    "name": new_cols[cn].name,
                    "data_type": new_cols[cn].data_type,
                    "length": new_cols[cn].length,
                    "is_primary_key": new_cols[cn].is_primary_key,
                    "is_unique": new_cols[cn].is_unique,
                    "nullable": new_cols[cn].nullable,
                    "comment": new_cols[cn].comment,
                }
            )
        for cn in sorted(old_cols.keys() - new_cols.keys()):
            table_diff["columns_removed"].append(old_cols[cn].name)
        for cn in sorted(old_cols.keys() & new_cols.keys()):
            changes = _col_change(old_cols[cn], new_cols[cn])
            if changes:
                table_diff["columns_changed"].append(
                    {"name": new_cols[cn].name, "changes": changes}
                )

        old_idx = {_index_key(i): i for i in ot.indexes}
        new_idx = {_index_key(i): i for i in nt.indexes}
        for key in sorted(new_idx.keys() - old_idx.keys()):
            table_diff["indexes_added"].append(new_idx[key])
        for key in sorted(old_idx.keys() - new_idx.keys()):
            table_diff["indexes_removed"].append(old_idx[key])

        old_fk = {_fk_key(f): f for f in ot.foreign_keys}
        new_fk = {_fk_key(f): f for f in nt.foreign_keys}
        for key in sorted(new_fk.keys() - old_fk.keys()):
            table_diff["fks_added"].append(new_fk[key])
        for key in sorted(old_fk.keys() - new_fk.keys()):
            table_diff["fks_removed"].append(old_fk[key])

        has_changes = any(
            [
                table_diff["comment"],
                table_diff["columns_added"],
                table_diff["columns_removed"],
                table_diff["columns_changed"],
                table_diff["indexes_added"],
                table_diff["indexes_removed"],
                table_diff["fks_added"],
                table_diff["fks_removed"],
            ]
        )
        if has_changes:
            changed.append(table_diff)
        else:
            unchanged.append(nt.name)

    return {
        "summary": {
            "tables_added": len(added),
            "tables_removed": len(removed),
            "tables_changed": len(changed),
            "columns_added": sum(len(c["columns_added"]) for c in changed),
            "columns_removed": sum(len(c["columns_removed"]) for c in changed),
            "columns_changed": sum(len(c["columns_changed"]) for c in changed),
        },
        "tables_added": added,
        "tables_removed": removed,
        "tables_changed": changed,
        "tables_unchanged": unchanged,
    }


def diff_from_snapshots(old_data: dict, new_data: dict) -> dict[str, Any]:
    """Convenience wrapper for two snapshot_data dicts."""
    from app.services.schema_parser import schema_from_dict

    return compare_schemas(
        schema_from_dict(old_data or {}),
        schema_from_dict(new_data or {}),
    )
