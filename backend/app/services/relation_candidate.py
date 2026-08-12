"""Rule-based candidate relation generation (Stage 2).

Generates potential logical-foreign-key relationships from a parsed schema
using naming patterns, type compatibility and PK/unique matching. Obviously
incompatible pairs are filtered out before any LLM call to save tokens and
reduce false positives.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.schema_parser import ParsedSchema, is_type_compatible


@dataclass
class CandidateRelation:
    source_table: str
    source_column: str
    source_data_type: str
    target_table: str
    target_column: str
    target_data_type: str
    cardinality: str = "many-to-one"
    confidence: float = 0.5
    reason: list[str] = field(default_factory=list)
    type_match: bool = True


def _singularize(name: str) -> str:
    """Naive singularization for table-name matching."""
    n = name.lower()
    if n.endswith("ies"):
        return n[:-3] + "y"
    if n.endswith("ses") or n.endswith("xes"):
        return n[:-2]
    if n.endswith("s") and not n.endswith("ss"):
        return n[:-1]
    return n


# Naming patterns indicating a possible foreign key column.
_ID_PATTERNS = [
    re.compile(r"^(.+)_id$"),
    re.compile(r"^(.+)Id$"),
    re.compile(r"^(.+)_code$"),
    re.compile(r"^(.+)Code$"),
    re.compile(r"^(.+)_no$"),
    re.compile(r"^(.+)_uuid$"),
]


def _extract_hint(column_name: str) -> str | None:
    """Return the leading hint from a candidate FK column name, e.g. user_id -> user."""
    cn = column_name
    for pat in _ID_PATTERNS:
        m = pat.match(cn)
        if m:
            return m.group(1).lower()
    return None


def _table_name_matches_hint(table_name: str, hint: str) -> bool:
    """Check whether a table name matches a column-name hint (singular/plural).

    Supports exact, inflected, sub-string, and abbreviation matching:
      user_id  -> users / user / user_infos
      dept_id  -> department / departments (abbr prefix match)
      tea_id   -> teacher / teachers      (abbr prefix match)
      course_id -> course / courses
    """
    tn = table_name.lower()
    h = hint.lower()
    # 1. Exact / simple singular-plural.
    if tn == h or tn == h + "s" or tn == h + "es":
        return True
    if _singularize(tn) == h or _singularize(h) == tn:
        return True
    # 2. Compound normalization.
    if tn.replace("_", "") == h.replace("_", "") + "s":
        return True
    if _singularize(tn).replace("_", "") == h.replace("_", ""):
        return True
    # 3. Sub-string containment (e.g. tea ≈ teacher, dept ≈ department).
    #    Only accept when the hint is a *prefix* of the table name (or vice
    #    versa), to avoid false positives like "id" matching everything.
    if len(h) >= 3 and (tn.startswith(h) or h.startswith(tn)):
        return True
    # 4. Abbreviation: every character of hint appears in order in table name.
    #    e.g. "dpt" -> "department", "tc" -> "teacher_course".
    if len(h) >= 3 and _is_subsequence(h, tn):
        return True
    return False


def _is_strong_table_match(table_name: str, hint: str) -> bool:
    """Return True when the hint matches the table name exactly or through a
    simple singular/plural inflection.

    Strong matches are reliable enough to accept the canonical FK pattern
    ``child.xxx_id -> parent.id`` (target column is the plain ``id`` primary
    key). Fuzzy matches (prefix / substring / abbreviation) still require the
    target column to echo the hint so we do not pair ``user_id`` with a table
    that merely starts with "user" (e.g. ``user_friend``).
    """
    tn = table_name.lower()
    h = hint.lower()
    if tn == h or _singularize(tn) == h or _singularize(h) == tn:
        return True
    if tn == h + "s" or tn == h + "es":
        return True
    if tn.replace("_", "") == h.replace("_", "") + "s":
        return True
    if _singularize(tn).replace("_", "") == h.replace("_", ""):
        return True
    return False


def _is_subsequence(short: str, long: str) -> bool:
    """Return True if every character of `short` appears in `long` in order."""
    idx = 0
    for ch in long:
        if ch == short[idx]:
            idx += 1
            if idx == len(short):
                return True
    return False


def _target_column_matches_hint(column_name: str, hint: str) -> bool:
    """Check that the target column name is plausibly a PK for the hint.

    Accepts patterns like: id / tea_id / course_id / dept_id
    Rejects columns like tc_id when the hint is "tea".
    """
    cn = column_name.lower()
    h = hint.lower()
    # Direct hit: column ends with _id or is exactly the hint + _id.
    if cn == h or cn == h + "_id" or cn == h + "id":
        return True
    if cn.endswith("_" + h + "_id") or cn.endswith("_" + h + "id"):
        return True
    # The column name contains the hint as a sub-word (with _ delimiters).
    # e.g. "tea" in "teacher_id" -> True, "tea" in "tc_id" -> False.
    parts = set(cn.replace("-", "_").split("_"))
    if h in parts:
        return True
    # Subsequence check with a stricter minimum length (>=4 chars).
    if len(h) >= 4 and _is_subsequence(h, cn):
        return True
    return False


def generate_candidates(schema: ParsedSchema) -> list[CandidateRelation]:
    """Generate candidate relationships from a parsed schema.

    A candidate is generated when a source column's name hints at a target
    table (e.g. user_id -> users) and the target column is a PK or unique,
    with compatible data types.
    """
    candidates: list[CandidateRelation] = []

    # Index tables by lower-cased name and pre-compute their PK columns.
    pk_index: dict[str, list[tuple[str, str]]] = {}  # table -> [(col, type)]
    unique_index: dict[str, list[tuple[str, str]]] = {}
    for t in schema.tables:
        tn = t.name.lower()
        pk_cols = [(c.name, c.data_type) for c in t.columns if c.is_primary_key]
        uq_cols = [(c.name, c.data_type) for c in t.columns if c.is_unique and not c.is_primary_key]
        pk_index[tn] = pk_cols
        unique_index[tn] = uq_cols

    existing_fks: set[tuple[str, str, str, str]] = set()
    for t in schema.tables:
        for fk in t.foreign_keys:
            existing_fks.add(
                (t.name.lower(), (fk.get("source_column") or "").lower(), (fk.get("target_table") or "").lower(), (fk.get("target_column") or "").lower())
            )

    seen: set[tuple[str, str, str, str]] = set()

    for src_table in schema.tables:
        for col in src_table.columns:
            hint = _extract_hint(col.name)
            if not hint:
                continue
            # Skip self-referential PK columns (e.g. id column itself).
            if col.is_primary_key:
                continue

            for tgt_table in schema.tables:
                if tgt_table.name == src_table.name:
                    continue
                if not _table_name_matches_hint(tgt_table.name, hint):
                    continue
                strong_match = _is_strong_table_match(tgt_table.name, hint)

                # Prefer PK target, fall back to unique columns named id/code.
                target_cols: list[tuple[str, str, bool]] = []
                for pc_name, pc_type in pk_index.get(tgt_table.name.lower(), []):
                    target_cols.append((pc_name, pc_type, True))
                if not target_cols:
                    for uc_name, uc_type in unique_index.get(tgt_table.name.lower(), []):
                        if uc_name.lower() in {"code", "no", "uuid"} or uc_name.lower().endswith("_id"):
                            target_cols.append((uc_name, uc_type, False))

                for tcol_name, tcol_type, is_pk in target_cols:
                    # Guard: when the target table match is fuzzy (sub-string /
                    # abbreviation), skip target columns whose names do not
                    # contain the hint. This prevents "tea_id -> tc_id" on a
                    # table that merely happens to contain the letters "tea".
                    # For exact / inflected table matches, the canonical
                    # "xxx_id -> parent.id" pattern is always valid, so a plain
                    # `id` PK target is accepted without the column guard.
                    if not strong_match and not _target_column_matches_hint(tcol_name, hint):
                        continue

                    key = (
                        src_table.name.lower(),
                        col.name.lower(),
                        tgt_table.name.lower(),
                        tcol_name.lower(),
                    )
                    if key in seen or key in existing_fks:
                        continue
                    type_ok = is_type_compatible(col.data_type, tcol_type)
                    if not type_ok:
                        continue
                    seen.add(key)

                    reasons: list[str] = []
                    conf = 0.5
                    reasons.append(f"字段命名 {col.name} 与目标表 {tgt_table.name} 匹配")
                    conf += 0.15
                    if is_pk:
                        reasons.append(f"目标字段 {tgt_table.name}.{tcol_name} 为表主键")
                        conf += 0.2
                    else:
                        reasons.append(f"目标字段 {tgt_table.name}.{tcol_name} 具有唯一约束")
                        conf += 0.1
                    if is_type_compatible(col.data_type, tcol_type):
                        reasons.append(f"字段类型兼容 ({col.data_type} ↔ {tcol_type})")
                        conf += 0.1
                    if hint == _singularize(tgt_table.name.lower()):
                        reasons.append("表名单复数匹配")
                        conf += 0.05

                    conf = min(conf, 0.97)
                    candidates.append(
                        CandidateRelation(
                            source_table=src_table.name,
                            source_column=col.name,
                            source_data_type=col.data_type,
                            target_table=tgt_table.name,
                            target_column=tcol_name,
                            target_data_type=tcol_type,
                            cardinality="many-to-one",
                            confidence=round(conf, 3),
                            reason=reasons,
                            type_match=type_ok,
                        )
                    )

    # Sort by confidence descending.
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates


def candidate_to_dict(c: CandidateRelation) -> dict:
    return {
        "source_table": c.source_table,
        "source_column": c.source_column,
        "source_data_type": c.source_data_type,
        "target_table": c.target_table,
        "target_column": c.target_column,
        "target_data_type": c.target_data_type,
        "cardinality": c.cardinality,
        "confidence": c.confidence,
        "reason": c.reason,
        "type_match": c.type_match,
    }


# Canonical forms written to storage / returned over API.
# The UI should never see N:1 / many-to-one — N:1 is always flipped to 1:N
# (swap source ↔ target) so cardinality notation is consistent and Crow's Foot
# markers read naturally on the FK (many) side.
_CARD_ALIASES = {
    "1:1": "one-to-one",
    "one-to-one": "one-to-one",
    "1:n": "one-to-many",
    "1:N": "one-to-many",
    "one-to-many": "one-to-many",
    "n:1": "many-to-one",
    "N:1": "many-to-one",
    "many-to-one": "many-to-one",
    "n:n": "many-to-many",
    "N:N": "many-to-many",
    "many-to-many": "many-to-many",
}


def normalize_relationship_direction(
    source_table: str,
    source_column: str,
    target_table: str,
    target_column: str,
    cardinality: str,
) -> tuple[str, str, str, str, str]:
    """Ensure cardinality never appears as many-to-one / N:1.

    When the relationship is many-to-one (source=N, target=1), swap source and
    target and rewrite cardinality to one-to-many. 1:1 and N:N pass through
    unchanged.

    Returns (source_table, source_column, target_table, target_column, cardinality)
    using the canonical "one-to-many" / "one-to-one" / "many-to-many" strings.
    """
    canon = _CARD_ALIASES.get(str(cardinality or "").strip(), "one-to-many")
    if canon == "many-to-one":
        # swap endpoints so source becomes "one" (PK side) and target becomes "many" (FK side)
        return (target_table, target_column, source_table, source_column, "one-to-many")
    return (
        str(source_table or ""),
        str(source_column or ""),
        str(target_table or ""),
        str(target_column or ""),
        canon,
    )
