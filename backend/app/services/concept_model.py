"""ER concept model conversion (physical model -> conceptual model, Chen notation).

Reverse-engineering a *physical* relational schema (tables, columns, foreign
keys) into a *conceptual* ER model where:

  - tables       -> entities (rectangles)
  - columns      -> attributes (ellipses)
  - foreign keys -> relationships (diamonds) with 1/N cardinality labels
  - pure junction tables (composite PK made of exactly two FKs) become
    many-to-many relationships that may carry their own attributes

The converter is deterministic (rule-based). Optional AI enhancement can
generate business-meaningful relationship names (e.g. 回复 / 发送 / 下单) using
the user's configured LLM; every failure falls back to rule-based names.
"""
from __future__ import annotations

import json
from typing import Any

from app.services.llm_service import LLMSettings
from app.services.schema_parser import ParsedSchema


# ---------------------------------------------------------------------------
# Cardinality helpers
# ---------------------------------------------------------------------------
def _chen_cards(cardinality: str) -> tuple[str, str]:
    """Map a stored cardinality enum to Chen notation endpoint labels.

    The stored canonical form is (source, target) after N:1 normalization:
      one-to-one    -> 1 : 1
      one-to-many   -> 1 : N   (source = one side, target = many side)
      many-to-many  -> N : N
    """
    card = str(cardinality or "").lower()
    if card in ("one-to-one", "1:1"):
        return "1", "1"
    if card in ("many-to-many", "n:n"):
        return "N", "N"
    return "1", "N"


# ---------------------------------------------------------------------------
# Rule-based relationship naming
# ---------------------------------------------------------------------------
_VERB_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    (("order", "订单", "orders"), "下单"),
    (("user", "用户", "member", "会员", "客户", "customer"), "拥有"),
    (("admin", "管理员", "staff", "员工"), "管理"),
    (("comment", "留言", "message", "reply", "回复"), "发送"),
    (("category", "分类", "type", "类型"), "归类"),
]


def _default_relation_name(
    src_name: str,
    tgt_name: str,
    src_col_comment: str | None = None,
    tgt_col_comment: str | None = None,
    cardinality: str = "one-to-many",
) -> str:
    """Heuristic relationship name with sensible Chinese defaults."""
    for comment in (src_col_comment, tgt_col_comment):
        if comment and comment.strip() and comment.strip() != (src_name or tgt_name):
            return comment.strip()[:12]
    for keys, verb in _VERB_PATTERNS:
        if any(k in (src_name or "") for k in keys) and any(k in (tgt_name or "") for k in keys):
            return verb
    card = str(cardinality or "").lower()
    if card in ("many-to-many", "n:n"):
        return f"{src_name}与{tgt_name}关联"
    if card in ("one-to-one", "1:1"):
        return f"{src_name}对应{tgt_name}"
    return f"{src_name}关联{tgt_name}"


# ---------------------------------------------------------------------------
# Optional AI relationship naming
# ---------------------------------------------------------------------------
def _ai_naming_prompt(entities: list[dict], relations: list[dict]) -> str:
    entity_name = {e["id"]: e["name"] for e in entities}
    rows = []
    for r in relations:
        rows.append(
            {
                "id": r["id"],
                "source": entity_name.get(r["source_entity"], ""),
                "target": entity_name.get(r["target_entity"], ""),
                "cardinality": f"{r['source_card']}:{r['target_card']}",
            }
        )
    return (
        "下面是一组概念模型实体之间的联系，请为每个联系生成一个简洁的业务语义名称"
        "（2~6 个汉字，动词或动宾短语，例如：回复、发送、下单、管理）。\n"
        f"实体：{json.dumps([{'id': e['id'], 'name': e['name']} for e in entities], ensure_ascii=False)}\n"
        f"联系：{json.dumps(rows, ensure_ascii=False)}\n"
        "只输出 JSON：{\"relations\":[{\"id\":\"<联系id>\",\"name\":\"<名称>\"}]}，不要输出其他文字。"
    )


def ai_name_relations(
    entities: list[dict],
    relations: list[dict],
    settings: LLMSettings,
) -> dict[str, str]:
    """Ask the LLM for business-meaningful relationship names.

    Returns {relation_id: name}. Never raises: on any failure an empty dict is
    returned so the caller can fall back to rule-based names.
    """
    try:
        from app.services.llm_service import complete_json

        payload = complete_json(
            settings,
            system_prompt=(
                "你是一个数据库概念建模专家。根据实体名称和联系基数，"
                "为每个联系生成简洁、符合业务直觉的中文名称。"
            ),
            user_prompt=_ai_naming_prompt(entities, relations),
        )
        items = payload.get("relations") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            return {}
        known = {r["id"] for r in relations}
        out: dict[str, str] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            rid = str(item.get("id") or "")
            name = str(item.get("name") or "").strip()
            if rid in known and name:
                out[rid] = name[:12]
        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------
def _build_entities(schema: ParsedSchema) -> tuple[list[dict], dict[str, str]]:
    """Build entity dicts from schema tables; returns (entities, table->entity_id)."""
    entities: list[dict] = []
    entity_by_table: dict[str, str] = {}
    for idx, t in enumerate(schema.tables):
        eid = f"entity_{idx}"
        entity_by_table[t.name.lower()] = eid
        attributes = []
        for cidx, c in enumerate(t.columns):
            attributes.append(
                {
                    "id": f"attr_{idx}_{cidx}",
                    "name": (c.comment or "").strip() or c.name,
                    "column": c.name,
                    "data_type": c.data_type,
                    "is_pk": c.is_primary_key,
                    "is_fk": False,
                    "is_unique": c.is_unique,
                    "nullable": c.nullable,
                    "comment": c.comment,
                }
            )
        entities.append(
            {
                "id": eid,
                "name": (t.comment or "").strip() or t.name,
                "table": t.name,
                "comment": t.comment,
                "attributes": attributes,
                "position": None,
            }
        )
    return entities, entity_by_table


def _mark_fk_attributes(
    entities: list[dict],
    entity_by_table: dict[str, str],
    relationships: list[dict],
) -> None:
    """Light up is_fk on entity attributes that participate in relationships."""
    entity_index = {e["id"]: e for e in entities}
    for r in relationships:
        src_table = str(r.get("source_table") or "").lower()
        src_col = str(r.get("source_column") or "").lower()
        eid = entity_by_table.get(src_table)
        if not eid:
            continue
        entity = entity_index[eid]
        for attr in entity["attributes"]:
            if attr["column"].lower() == src_col:
                attr["is_fk"] = True
                break


def _is_junction_table(table) -> bool:
    """True when a table is a pure M:N junction (composite PK == 2 distinct FKs)."""
    fks = [fk for fk in (table.foreign_keys or []) if fk.get("source_column")]
    if len(fks) != 2:
        return False
    pk_cols = {c.name.lower() for c in table.columns if c.is_primary_key}
    fk_cols = {(fk.get("source_column") or "").lower() for fk in fks}
    if pk_cols != fk_cols or len(pk_cols) != 2:
        return False
    targets = {(fk.get("target_table") or "").lower() for fk in fks}
    return len(targets) == 2


def _relation_from_fk(
    rel_idx: int,
    src_table: str,
    src_col: str,
    tgt_table: str,
    tgt_col: str,
    cardinality: str,
    entity_by_table: dict[str, str],
    entity_index: dict[str, dict],
    reason: list[str],
    source_type: str,
) -> dict | None:
    src_eid = entity_by_table.get(str(src_table).lower())
    tgt_eid = entity_by_table.get(str(tgt_table).lower())
    if not src_eid or not tgt_eid or src_eid == tgt_eid:
        return None
    src_card, tgt_card = _chen_cards(cardinality)
    src_entity = entity_index[src_eid]
    tgt_entity = entity_index[tgt_eid]
    src_comment = next(
        (a["comment"] for a in src_entity["attributes"] if a["column"].lower() == str(src_col).lower()),
        None,
    )
    name = _default_relation_name(
        src_entity["name"],
        tgt_entity["name"],
        src_comment,
        None,
        cardinality,
    )
    return {
        "id": f"rel_{rel_idx}",
        "name": name,
        "source_entity": src_eid,
        "target_entity": tgt_eid,
        "source_card": src_card,
        "target_card": tgt_card,
        "source_table": str(src_table),
        "source_column": str(src_col),
        "target_table": str(tgt_table),
        "target_column": str(tgt_col),
        "cardinality": str(cardinality),
        "attributes": [],
        "reason": reason,
        "source_type": source_type,
    }


def convert_to_concept_model(
    schema: ParsedSchema,
    relationships: list[dict],
    use_ai_names: bool = False,
    llm_settings: LLMSettings | None = None,
) -> dict:
    """Convert a physical schema + relationship list into a Chen concept model.

    Returns model_data: {"entities": [...], "relations": [...]}.
    """
    entities, entity_by_table = _build_entities(schema)
    entity_index = {e["id"]: e for e in entities}

    # Visible relationships are the same set the ER canvas draws: confirmed
    # database constraints / AI-confirmed / manual. Pending suggestions and
    # rejected rows are excluded so the concept model matches what the user
    # actually committed to.
    visible = [
        r for r in relationships if str(r.get("status") or "") in ("confirmed", "manual")
    ]
    _mark_fk_attributes(entities, entity_by_table, visible)

    relations: list[dict] = []
    seen_fk: set[tuple[str, str, str, str]] = set()

    # 1) Regular foreign-key relationships.
    for r in visible:
        st = r.get("source_table") or ""
        sc = r.get("source_column") or ""
        tt = r.get("target_table") or ""
        tc = r.get("target_column") or ""
        if not (st and sc and tt and tc):
            continue
        key = (str(st).lower(), str(sc).lower(), str(tt).lower(), str(tc).lower())
        if key in seen_fk:
            continue
        seen_fk.add(key)
        rel = _relation_from_fk(
            len(relations),
            st,
            sc,
            tt,
            tc,
            r.get("cardinality") or "one-to-many",
            entity_by_table,
            entity_index,
            [
                f"外键 {st}.{sc} → {tt}.{tc} 转换为概念联系",
                f"来源：{r.get('source_type') or '数据库约束'}",
            ],
            str(r.get("source_type") or "database_constraint"),
        )
        if rel:
            relations.append(rel)

    # 2) M:N junction tables -> relationships with their own attributes.
    junction_entity_ids: set[str] = set()
    for table in schema.tables:
        if not _is_junction_table(table):
            continue
        fks = [fk for fk in (table.foreign_keys or []) if fk.get("source_column")]
        eid = entity_by_table.get(table.name.lower())
        if not eid:
            continue
        targets: list[tuple[str, str]] = []
        for fk in fks:
            tt = fk.get("target_table") or ""
            tc = fk.get("target_column") or ""
            tgt_eid = entity_by_table.get(tt.lower())
            if tgt_eid:
                targets.append((tgt_eid, tt, tc))
        if len(targets) != 2:
            continue
        junction_entity_ids.add(eid)
        attrs = []
        fk_cols = {(fk.get("source_column") or "").lower() for fk in fks}
        for cidx, c in enumerate(table.columns):
            if c.name.lower() in fk_cols:
                continue
            attrs.append(
                {
                    "id": f"relattr_{len(relations)}_{cidx}",
                    "name": (c.comment or "").strip() or c.name,
                    "column": c.name,
                    "data_type": c.data_type,
                    "is_pk": c.is_primary_key,
                    "is_fk": False,
                    "is_unique": c.is_unique,
                    "nullable": c.nullable,
                    "comment": c.comment,
                }
            )
        e1_name = entity_index[targets[0][0]]["name"]
        e2_name = entity_index[targets[1][0]]["name"]
        relations.append(
            {
                "id": f"rel_{len(relations)}",
                "name": f"{e1_name}与{e2_name}关联",
                "source_entity": targets[0][0],
                "target_entity": targets[1][0],
                "source_card": "N",
                "target_card": "N",
                "source_table": targets[0][1],
                "source_column": fks[0].get("source_column") or "",
                "target_table": targets[1][1],
                "target_column": fks[1].get("target_column") or "",
                "cardinality": "many-to-many",
                "attributes": attrs,
                "reason": [
                    f"表 {table.name} 为纯关联表（复合主键由两个外键组成），转换为 M:N 联系",
                    "其业务属性上移为联系属性",
                ],
                "source_type": "junction",
            }
        )

    if junction_entity_ids:
        entities = [e for e in entities if e["id"] not in junction_entity_ids]

    # 3) Optional AI naming for relations (fallback to rule names on failure).
    if use_ai_names and llm_settings is not None and relations:
        names = ai_name_relations(entities, relations, llm_settings)
        for r in relations:
            if r["id"] in names:
                r["name"] = names[r["id"]]

    return {"entities": entities, "relations": relations, "viewport": None}


def build_concept_model_from_snapshot(
    snapshot_data: dict,
    relationships: list[dict],
    use_ai_names: bool = False,
    llm_settings: LLMSettings | None = None,
) -> dict:
    """Convenience wrapper: snapshot dict -> ParsedSchema -> concept model."""
    from app.services.schema_parser import schema_from_dict

    schema = schema_from_dict(snapshot_data or {})
    return convert_to_concept_model(schema, relationships, use_ai_names, llm_settings)


def apply_concept_positions(model_data: dict, positions: dict[str, dict]) -> dict:
    """Merge user-dragged node positions back into the concept model."""
    data = json.loads(json.dumps(model_data or {}))
    for entity in data.get("entities", []):
        if entity["id"] in positions:
            entity["position"] = positions[entity["id"]]
    return data


def count_stats(model_data: dict) -> dict[str, Any]:
    entities = model_data.get("entities") or []
    relations = model_data.get("relations") or []
    attr_count = sum(len(e.get("attributes") or []) for e in entities)
    return {
        "entity_count": len(entities),
        "relation_count": len(relations),
        "attribute_count": attr_count,
    }
