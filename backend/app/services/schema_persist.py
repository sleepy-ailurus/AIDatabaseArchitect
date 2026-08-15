"""Persist a parsed schema as a new snapshot + database-constraint relationships.

Shared by the live DB sync (schema router) and the offline DDL/DBML import so
that both entry points produce identical snapshot and relationship rows.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Relationship, SchemaColumn, SchemaSnapshot, SchemaTable
from app.services.relation_candidate import normalize_relationship_direction
from app.services.schema_parser import ParsedSchema


def persist_schema_snapshot(db: Session, project_id: int, schema: ParsedSchema) -> tuple[SchemaSnapshot, int]:
    """Create a new schema snapshot version + explicit FK relationships.

    Returns (snapshot, relationship_count).
    """
    last_version = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.project_id == project_id)
        .order_by(SchemaSnapshot.version.desc())
        .first()
    )
    next_version = (last_version.version + 1) if last_version else 1

    snapshot = SchemaSnapshot(
        project_id=project_id,
        snapshot_data=schema.to_dict(),
        version=next_version,
    )
    db.add(snapshot)
    db.flush()

    for t in schema.tables:
        table_row = SchemaTable(
            snapshot_id=snapshot.id,
            table_name=t.name,
            comment=t.comment,
            engine=t.engine,
        )
        db.add(table_row)
        db.flush()
        for c in t.columns:
            db.add(
                SchemaColumn(
                    table_id=table_row.id,
                    column_name=c.name,
                    data_type=c.data_type,
                    length=c.length,
                    nullable=c.nullable,
                    default_value=c.default_value,
                    is_primary_key=c.is_primary_key,
                    is_unique=c.is_unique,
                    comment=c.comment,
                )
            )

    relationship_count = 0
    tables_by_name = {t.name: t for t in schema.tables}

    def _col(tbl_name: str, col_name: str):
        tbl = tables_by_name.get(tbl_name)
        if not tbl:
            return None
        return next((c for c in tbl.columns if c.name == col_name), None)

    for t in schema.tables:
        for fk in t.foreign_keys:
            source_col = fk.get("source_column")
            target_table = fk.get("target_table")
            target_col = fk.get("target_column")
            if not (source_col and target_table and target_col):
                continue
            sc_obj = _col(t.name, source_col)
            tc_obj = _col(target_table, target_col)
            src_is_pk = bool(getattr(sc_obj, "is_primary_key", False))
            tgt_is_pk = bool(getattr(tc_obj, "is_primary_key", False))
            src_is_unique = bool(getattr(sc_obj, "is_unique", False))

            if not src_is_pk and tgt_is_pk:
                card = "one-to-one" if src_is_unique else "many-to-one"
            elif src_is_pk and not tgt_is_pk:
                card = "one-to-many"
            elif src_is_pk and tgt_is_pk:
                card = "one-to-one"
            else:
                card = "many-to-one"

            st, sc, tt, tc, card_norm = normalize_relationship_direction(
                t.name,
                source_col,
                target_table,
                target_col,
                card,
            )
            existing = (
                db.query(Relationship)
                .filter(
                    Relationship.project_id == project_id,
                    Relationship.source_table == st,
                    Relationship.source_column == sc,
                    Relationship.target_table == tt,
                    Relationship.target_column == tc,
                    Relationship.source_type == "database_constraint",
                )
                .first()
            )
            if existing:
                continue
            db.add(
                Relationship(
                    project_id=project_id,
                    source_table=st,
                    source_column=sc,
                    target_table=tt,
                    target_column=tc,
                    cardinality=card_norm,
                    confidence=1.0,
                    source_type="database_constraint",
                    status="confirmed",
                    reason=["数据库显式外键约束"],
                    constraint_name=fk.get("name"),
                )
            )
            relationship_count += 1

    db.commit()
    db.refresh(snapshot)
    return snapshot, relationship_count
