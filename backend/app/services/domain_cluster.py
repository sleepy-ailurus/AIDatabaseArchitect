"""Business-domain clustering over the FK graph (feature 9)."""
from __future__ import annotations

import json

import networkx as nx

from app.services.llm_service import LLMSettings, complete_json
from app.services.schema_parser import ParsedSchema


def build_fk_graph(schema: ParsedSchema, relationships: list[dict] | None = None) -> nx.Graph:
    """Undirected graph where tables are nodes and FK/relationships are edges."""
    graph = nx.Graph()
    for t in schema.tables:
        graph.add_node(t.name)
    for t in schema.tables:
        for fk in t.foreign_keys or []:
            target = fk.get("target_table")
            if target and target != t.name:
                graph.add_edge(t.name, target)
    for r in relationships or []:
        src = r.get("source_table")
        tgt = r.get("target_table")
        if src and tgt and src != tgt and graph.has_node(src) and graph.has_node(tgt):
            graph.add_edge(src, tgt)
    return graph


def cluster_schema(schema: ParsedSchema, relationships: list[dict] | None = None) -> list[dict]:
    """Cluster tables into business domains using modularity-based community detection."""
    graph = build_fk_graph(schema, relationships)
    if graph.number_of_nodes() == 0:
        return []

    try:
        communities = list(nx.community.greedy_modularity_communities(graph))
    except Exception:
        communities = [set(graph.nodes)]

    # Fall back to connected components when modularity yields one giant group.
    if len(communities) == 1 and len(communities[0]) > 1:
        components = [set(c) for c in nx.connected_components(graph)]
        if len(components) > 1 and max(len(c) for c in components) < len(communities[0]):
            communities = components

    clusters = []
    for idx, community in enumerate(communities):
        tables = sorted(community)
        clusters.append(
            {
                "cluster_index": idx,
                "name": f"业务域 {idx + 1}",
                "description": None,
                "tables": tables,
            }
        )
    clusters.sort(key=lambda c: len(c["tables"]), reverse=True)
    for idx, c in enumerate(clusters):
        c["cluster_index"] = idx
    return clusters


def ai_name_clusters(
    schema: ParsedSchema,
    clusters: list[dict],
    settings: LLMSettings,
) -> dict[int, dict[str, str]]:
    """Ask the LLM to name each cluster and write a one-line description."""
    try:
        table_comments = {t.name: (t.comment or "") for t in schema.tables}
        rows = [
            {
                "index": c["cluster_index"],
                "tables": [
                    {"name": t, "comment": table_comments.get(t, "")} for t in c["tables"]
                ],
            }
            for c in clusters
        ]
        payload = complete_json(
            settings,
            system_prompt=(
                "你是数据库架构专家。根据每组表及其注释，判断它们共同构成的业务域，"
                "为每个业务域生成简洁名称（2~6 字，如：用户域、订单域、商品域）和一句话描述。"
                "只输出 JSON：{\"domains\":[{\"index\":0,\"name\":\"...\",\"description\":\"...\"}]}"
            ),
            user_prompt=f"业务域分组：{json.dumps(rows, ensure_ascii=False)}",
        )
        items = payload.get("domains") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            return {}
        out: dict[int, dict[str, str]] = {}
        for item in items:
            if isinstance(item, dict) and "index" in item:
                out[int(item["index"])] = {
                    "name": str(item.get("name") or "")[:12],
                    "description": str(item.get("description") or "")[:100],
                }
        return out
    except Exception:
        return {}


def analyze_domains(
    schema: ParsedSchema,
    relationships: list[dict] | None = None,
    use_ai_names: bool = False,
    llm_settings: LLMSettings | None = None,
) -> list[dict]:
    clusters = cluster_schema(schema, relationships)
    if use_ai_names and llm_settings is not None and clusters:
        names = ai_name_clusters(schema, clusters, llm_settings)
        for c in clusters:
            info = names.get(c["cluster_index"])
            if info and info.get("name"):
                c["name"] = info["name"]
                c["description"] = info.get("description") or None
    return clusters
