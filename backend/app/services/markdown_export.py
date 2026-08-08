"""Markdown document generation for database design docs.

Generates a document containing: database overview, Mermaid ER diagram, table
structure details, field & index descriptions, relationship descriptions
(explicit + AI inferred) and AI inference basis with confidence.
"""
from __future__ import annotations

from datetime import datetime

from app.services.schema_parser import ParsedSchema

CARDINALITY_DISPLAY = {
    "many-to-one": "N : 1",
    "one-to-many": "1 : N",
    "one-to-one": "1 : 1",
    "many-to-many": "N : N",
    "1:1": "1 : 1",
    "1:N": "1 : N",
    "N:N": "N : N",
}


def cardinality_display(card: str) -> str:
    return CARDINALITY_DISPLAY.get(card, card)


def _confidence_level(conf: float) -> str:
    if conf >= 0.85:
        return "高"
    if conf >= 0.60:
        return "中"
    return "低"


def _mermaid_type(data_type: str) -> str:
    t = (data_type or "").lower()
    if "int" in t or "bigint" in t:
        return "bigint"
    if "decimal" in t or "numeric" in t or "float" in t or "double" in t:
        return "decimal"
    if "date" in t or "time" in t:
        return "datetime"
    if "text" in t:
        return "text"
    if "bool" in t or "tinyint(1)" in t:
        return "boolean"
    return "varchar"


def _mermaid_relation_symbol(card: str) -> str:
    # Mermaid erDiagram cardinality symbols.
    return {
        "many-to-one": "}o--||",
        "one-to-many": "||--o{",
        "one-to-one": "||--||",
        "many-to-many": "}o--o{",
        "1:1": "||--||",
        "1:N": "||--o{",
        "N:N": "}o--o{",
    }.get(card, "}o--||")


def generate_markdown(
    schema: ParsedSchema,
    relationships: list[dict],
    project_name: str = "数据库设计文档",
    project_description: str | None = None,
) -> str:
    """Generate the full Markdown design document."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []

    # 1. Title + overview
    lines.append(f"# {project_name}")
    lines.append("")
    lines.append(f"> 自动生成于 {now}  ·  AI Database Architect")
    lines.append("")
    lines.append("## 1. 数据库概述")
    lines.append("")
    if project_description:
        lines.append(project_description)
        lines.append("")
    lines.append(f"- **数据库名称**：`{schema.database_name}`")
    if schema.db_version:
        lines.append(f"- **数据库版本**：{schema.db_version}")
    lines.append(f"- **表数量**：{len(schema.tables)}")
    lines.append(f"- **关系总数**：{len(relationships)}")
    explicit = [r for r in relationships if r.get("source_type") == "database_constraint"]
    ai_inferred = [r for r in relationships if r.get("source_type") == "ai_suggestion"]
    manual = [r for r in relationships if r.get("source_type") == "manual"]
    lines.append(f"  - 显式外键：{len(explicit)} 条")
    lines.append(f"  - AI 推断：{len(ai_inferred)} 条")
    lines.append(f"  - 手动添加：{len(manual)} 条")
    lines.append("")

    # 2. ER diagram (Mermaid)
    lines.append("## 2. ER 关系图")
    lines.append("")
    lines.append("```mermaid")
    lines.append("erDiagram")
    # Table definitions.
    for t in schema.tables:
        safe_name = _safe_mermaid_name(t.name)
        lines.append(f"    {safe_name} {{")
        for c in t.columns:
            attr = _mermaid_type(c.data_type)
            tag = "PK" if c.is_primary_key else ("FK" if c.is_unique else "")
            tag_str = f" {tag}" if tag else ""
            comment_str = f' "{c.comment}"' if c.comment else ""
            lines.append(f"        {attr} {c.name}{tag_str}{comment_str}")
        lines.append("    }")
        lines.append("")
    # Relationship lines.
    drawn: set[tuple[str, str]] = set()
    for r in relationships:
        src = _safe_mermaid_name(r.get("source_table", ""))
        tgt = _safe_mermaid_name(r.get("target_table", ""))
        if not src or not tgt:
            continue
        edge_key = (src, tgt)
        if edge_key in drawn:
            continue
        drawn.add(edge_key)
        sym = _mermaid_relation_symbol(r.get("cardinality", "many-to-one"))
        label = f"{r.get('source_column', '')}_{r.get('target_column', '')}".replace(" ", "_")
        lines.append(f"    {tgt} {sym} {src} : {label}")
    lines.append("```")
    lines.append("")

    # 3. Table structure details
    lines.append("## 3. 表结构说明")
    lines.append("")
    for t in schema.tables:
        lines.append(f"### 3.{schema.tables.index(t) + 1} `{t.name}`")
        if t.comment:
            lines.append(f"> {t.comment}")
            lines.append("")
        if t.engine:
            lines.append(f"- **存储引擎**：{t.engine}")
        lines.append("")
        lines.append("| 字段名 | 类型 | 可空 | 默认值 | 主键 | 唯一 | 说明 |")
        lines.append("|--------|------|------|--------|------|------|------|")
        for c in t.columns:
            nullable = "是" if c.nullable else "否"
            default = c.default_value if c.default_value is not None else ""
            pk = "✓" if c.is_primary_key else ""
            uq = "✓" if c.is_unique else ""
            comment = c.comment or ""
            lines.append(
                f"| `{c.name}` | {c.data_type} | {nullable} | {default} | {pk} | {uq} | {comment} |"
            )
        lines.append("")
        # Indexes.
        if t.indexes:
            lines.append("**索引：**")
            lines.append("")
            lines.append("| 索引名 | 字段 | 唯一 |")
            lines.append("|--------|------|------|")
            for idx in t.indexes:
                cols = ", ".join(idx.get("columns", []) or [])
                unique = "✓" if idx.get("unique") else ""
                lines.append(f"| {idx.get('name', '')} | {cols} | {unique} |")
            lines.append("")

    # 4. Relationships
    lines.append("## 4. 关系说明")
    lines.append("")
    lines.append("### 4.1 显式外键关系")
    lines.append("")
    if explicit:
        lines.append("| 源表.字段 | 目标表.字段 | 基数 | 约束名 |")
        lines.append("|-----------|-------------|------|--------|")
        for r in explicit:
            lines.append(
                f"| `{r.get('source_table')}.{r.get('source_column')}` | "
                f"`{r.get('target_table')}.{r.get('target_column')}` | "
                f"{cardinality_display(r.get('cardinality', ''))} | "
                f"{r.get('constraint_name') or ''} |"
            )
        lines.append("")
    else:
        lines.append("无显式外键关系。")
        lines.append("")

    lines.append("### 4.2 AI 推断关系")
    lines.append("")
    if ai_inferred:
        lines.append("| 源表.字段 | 目标表.字段 | 基数 | 置信度 | 状态 |")
        lines.append("|-----------|-------------|------|--------|------|")
        for r in ai_inferred:
            conf = r.get("confidence", 0.0)
            lines.append(
                f"| `{r.get('source_table')}.{r.get('source_column')}` | "
                f"`{r.get('target_table')}.{r.get('target_column')}` | "
                f"{cardinality_display(r.get('cardinality', ''))} | "
                f"{conf:.0%} ({_confidence_level(conf)}) | "
                f"{r.get('status', '')} |"
            )
        lines.append("")
    else:
        lines.append("无 AI 推断关系。")
        lines.append("")

    if manual:
        lines.append("### 4.3 手动添加关系")
        lines.append("")
        lines.append("| 源表.字段 | 目标表.字段 | 基数 |")
        lines.append("|-----------|-------------|------|")
        for r in manual:
            lines.append(
                f"| `{r.get('source_table')}.{r.get('source_column')}` | "
                f"`{r.get('target_table')}.{r.get('target_column')}` | "
                f"{cardinality_display(r.get('cardinality', ''))} |"
            )
        lines.append("")

    # 5. AI inference basis
    lines.append("## 5. AI 推断依据与置信度")
    lines.append("")
    if ai_inferred:
        lines.append("| 关系 | 置信度 | 级别 | 推断依据 |")
        lines.append("|------|--------|------|----------|")
        for r in ai_inferred:
            conf = r.get("confidence", 0.0)
            reason = "；".join(r.get("reason", []) or [])
            lines.append(
                f"| `{r.get('source_table')}.{r.get('source_column')}` → "
                f"`{r.get('target_table')}.{r.get('target_column')}` | "
                f"{conf:.0%} | {_confidence_level(conf)} | {reason} |"
            )
        lines.append("")
        lines.append("> 置信度分级：高 ≥ 85%，中 60%-84%，低 < 60%。所有 AI 推断结果均经过程序校验与人工确认。")
        lines.append("")
    else:
        lines.append("本次未生成 AI 推断关系。")
        lines.append("")

    # 6. Footer
    lines.append("---")
    lines.append("")
    lines.append(f"*文档版本：V1.0  ·  生成时间：{now}  ·  AI Database Architect*")
    lines.append("")

    return "\n".join(lines)


def _safe_mermaid_name(name: str) -> str:
    """Mermaid entity names must be alphanumeric (use a quoted-safe transform)."""
    if not name:
        return ""
    # Mermaid supports quoted identifiers; keep simple alphanumerics.
    safe = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)
    return safe.upper() if safe else ""
