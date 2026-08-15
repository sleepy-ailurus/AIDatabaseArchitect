"""Course design / graduation design document generator (feature 11)."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from app.services.schema_parser import ParsedSchema


def _rel_display(r: dict) -> str:
    return (
        f"{r.get('source_table')}.{r.get('source_column')} → "
        f"{r.get('target_table')}.{r.get('target_column')}"
        f"（{r.get('cardinality') or ''}）"
    )


def _entity_name(entities: list[dict], eid: str) -> str:
    for e in entities:
        if e.get("id") == eid:
            return e.get("name") or eid
    return eid


def build_markdown(
    project_name: str,
    project_description: str | None,
    schema: ParsedSchema,
    relationships: list[dict],
    concept_model: dict | None = None,
    author: str = "",
    student_id: str = "",
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entities = concept_model.get("entities", []) if concept_model else []
    relations = concept_model.get("relations", []) if concept_model else []
    lines: list[str] = []

    lines.append(f"# {project_name} 数据库设计说明书")
    if author or student_id:
        lines.append("")
        lines.append(f"**作者**：{author or '-'}　**学号**：{student_id or '-'}")
    lines.append("")
    lines.append(f"> 自动生成于 {now} · AI Database Architect")
    lines.append("")

    # 1 概述
    lines.append("## 1. 项目概述")
    lines.append("")
    if project_description:
        lines.append(project_description)
        lines.append("")
    lines.append(f"- 数据库名称：`{schema.database_name}`")
    if schema.db_version:
        lines.append(f"- 数据库版本：{schema.db_version}")
    lines.append(f"- 实体/表数量：{len(schema.tables)}")
    lines.append(f"- 关系数量：{len(relationships)}")
    lines.append(f"- 字段总数：{sum(len(t.columns) for t in schema.tables)}")
    lines.append("")

    # 2 需求分析
    lines.append("## 2. 需求分析")
    lines.append("")
    lines.append("> 说明：请根据实际业务需求补充需求描述。以下为从数据库结构中识别出的实体与联系概要。")
    lines.append("")
    if entities:
        lines.append("识别出的实体：")
        lines.append("")
        for e in entities:
            attrs = "、".join(a["name"] for a in (e.get("attributes") or [])[:8])
            lines.append(f"- **{e['name']}**：{attrs}")
        lines.append("")
    if relations:
        lines.append("识别出的联系：")
        lines.append("")
        for r in relations:
            src = _entity_name(entities, r.get("source_entity") or "")
            tgt = _entity_name(entities, r.get("target_entity") or "")
            lines.append(f"- {r['name']}：{src}（{r.get('source_card')}）— {tgt}（{r.get('target_card')}）")
        lines.append("")

    # 3 概念结构设计
    lines.append("## 3. 概念结构设计")
    lines.append("")
    lines.append("采用 Chen 记法 ER 概念模型描述业务实体、属性与联系。概念模型图可在『ER 模型 → 概念模型』中查看与导出。")
    lines.append("")
    lines.append("### 3.1 实体及其属性")
    lines.append("")
    for e in entities:
        lines.append(f"#### {e['name']}")
        lines.append("")
        for a in e.get("attributes") or []:
            tag = "（主键）" if a.get("is_pk") else ""
            lines.append(f"- {a['name']}{tag}")
        lines.append("")
    lines.append("### 3.2 联系")
    lines.append("")
    if relations:
        lines.append("| 联系 | 实体 A | 基数 | 实体 B | 基数 |")
        lines.append("|------|--------|------|--------|------|")
        for r in relations:
            src = _entity_name(entities, r.get("source_entity") or "")
            tgt = _entity_name(entities, r.get("target_entity") or "")
            lines.append(
                f"| {r['name']} | {src} | {r.get('source_card')} | "
                f"{tgt} | {r.get('target_card')} |"
            )
    else:
        lines.append("无。")
    lines.append("")

    # 4 逻辑结构设计
    lines.append("## 4. 逻辑结构设计")
    lines.append("")
    lines.append("将概念模型转换为关系模式（表结构）如下：")
    lines.append("")
    for t in schema.tables:
        lines.append(f"### 4.{schema.tables.index(t) + 1} `{t.name}`")
        if t.comment:
            lines.append(f"> {t.comment}")
            lines.append("")
        lines.append("| 字段 | 类型 | 可空 | 主键 | 唯一 | 默认值 | 注释 |")
        lines.append("|------|------|------|------|------|--------|------|")
        for c in t.columns:
            lines.append(
                f"| `{c.name}` | {c.data_type} | {'是' if c.nullable else '否'} | "
                f"{'✓' if c.is_primary_key else ''} | {'✓' if c.is_unique else ''} | "
                f"{c.default_value or ''} | {c.comment or ''} |"
            )
        lines.append("")

    # 5 规范化分析
    lines.append("## 5. 规范化分析")
    lines.append("")
    lines.append("> 提示：可结合『架构评审』中的 AI 意见补充范式分析（1NF/2NF/3NF/BCNF）章节。")
    lines.append("")
    for t in schema.tables:
        pk = "、".join(c.name for c in t.columns if c.is_primary_key)
        lines.append(f"- `{t.name}`：主键 {pk or '无'}；满足 1NF（属性原子性）。")
    lines.append("")

    # 6 关系说明
    lines.append("## 6. 关系说明")
    lines.append("")
    lines.append("| 源表.字段 | 目标表.字段 | 基数 | 类型 | 状态 |")
    lines.append("|-----------|-------------|------|------|------|")
    for r in relationships:
        lines.append(
            f"| `{r.get('source_table')}.{r.get('source_column')}` | "
            f"`{r.get('target_table')}.{r.get('target_column')}` | "
            f"{r.get('cardinality') or ''} | {r.get('source_type') or ''} | {r.get('status') or ''} |"
        )
    lines.append("")

    # 7 数据字典
    lines.append("## 7. 数据字典")
    lines.append("")
    lines.append("各表字段字典已在上文『逻辑结构设计』中列出，可在『注释补全』页面导出完整数据字典（Excel/Word/PDF）。")
    lines.append("")

    # 8 总结
    lines.append("## 8. 总结")
    lines.append("")
    lines.append(f"本系统数据库共设计 {len(schema.tables)} 张表、{sum(len(t.columns) for t in schema.tables)} 个字段、{len(relationships)} 条关系，覆盖了业务的核心数据需求，并遵循数据库规范化原则。")
    lines.append("")
    return "\n".join(lines)


def build_word(
    project_name: str,
    project_description: str | None,
    schema: ParsedSchema,
    relationships: list[dict],
    concept_model: dict | None = None,
    author: str = "",
    student_id: str = "",
) -> bytes:
    from docx import Document

    doc = Document()
    doc.add_heading(f"{project_name} 数据库设计说明书", 0)
    if author or student_id:
        doc.add_paragraph(f"作者：{author or '-'}　学号：{student_id or '-'}")
    doc.add_paragraph(f"自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · AI Database Architect")

    entities = concept_model.get("entities", []) if concept_model else []
    relations = concept_model.get("relations", []) if concept_model else []

    doc.add_heading("1. 项目概述", level=1)
    if project_description:
        doc.add_paragraph(project_description)
    doc.add_paragraph(f"数据库名称：{schema.database_name}；表数量：{len(schema.tables)}；关系数量：{len(relationships)}")

    doc.add_heading("2. 需求分析", level=1)
    doc.add_paragraph("说明：请根据实际业务需求补充需求描述。以下为从数据库结构中识别出的实体与联系概要。")
    for e in entities:
        attrs = "、".join(a["name"] for a in (e.get("attributes") or [])[:8])
        doc.add_paragraph(f"实体 {e['name']}：{attrs}", style="List Bullet")
    for r in relations:
        src = _entity_name(entities, r.get("source_entity") or "")
        tgt = _entity_name(entities, r.get("target_entity") or "")
        doc.add_paragraph(f"联系 {r['name']}：{src}（{r.get('source_card')}）— {tgt}（{r.get('target_card')}）", style="List Bullet")

    doc.add_heading("3. 概念结构设计", level=1)
    doc.add_paragraph("采用 Chen 记法 ER 概念模型描述业务实体、属性与联系。")
    for e in entities:
        doc.add_heading(e["name"], level=2)
        for a in e.get("attributes") or []:
            tag = "（主键）" if a.get("is_pk") else ""
            doc.add_paragraph(f"{a['name']}{tag}", style="List Bullet")

    doc.add_heading("4. 逻辑结构设计", level=1)
    for t in schema.tables:
        doc.add_heading(t.name, level=2)
        if t.comment:
            doc.add_paragraph(t.comment)
        table = doc.add_table(rows=1, cols=7)
        table.style = "Light Grid Accent 1"
        for i, text in enumerate(["字段", "类型", "可空", "主键", "唯一", "默认值", "注释"]):
            table.rows[0].cells[i].text = text
        for c in t.columns:
            cells = table.add_row().cells
            cells[0].text = c.name
            cells[1].text = c.data_type
            cells[2].text = "是" if c.nullable else "否"
            cells[3].text = "✓" if c.is_primary_key else ""
            cells[4].text = "✓" if c.is_unique else ""
            cells[5].text = c.default_value or ""
            cells[6].text = c.comment or ""
        doc.add_paragraph()

    doc.add_heading("5. 规范化分析", level=1)
    doc.add_paragraph("提示：可结合『架构评审』中的 AI 意见补充范式分析章节。")
    for t in schema.tables:
        pk = "、".join(c.name for c in t.columns if c.is_primary_key)
        doc.add_paragraph(f"{t.name}：主键 {pk or '无'}；满足 1NF。", style="List Bullet")

    doc.add_heading("6. 关系说明", level=1)
    table = doc.add_table(rows=1, cols=4)
    table.style = "Light Grid Accent 1"
    for i, text in enumerate(["源表.字段", "目标表.字段", "基数", "类型"]):
        table.rows[0].cells[i].text = text
    for r in relationships:
        cells = table.add_row().cells
        cells[0].text = f"{r.get('source_table')}.{r.get('source_column')}"
        cells[1].text = f"{r.get('target_table')}.{r.get('target_column')}"
        cells[2].text = r.get("cardinality") or ""
        cells[3].text = r.get("source_type") or ""

    doc.add_heading("7. 总结", level=1)
    doc.add_paragraph(
        f"本系统数据库共设计 {len(schema.tables)} 张表、{sum(len(t.columns) for t in schema.tables)} 个字段、"
        f"{len(relationships)} 条关系，覆盖了业务的核心数据需求，并遵循数据库规范化原则。"
    )

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_pdf(
    project_name: str,
    project_description: str | None,
    schema: ParsedSchema,
    relationships: list[dict],
    concept_model: dict | None = None,
    author: str = "",
    student_id: str = "",
) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("BodyCN", parent=styles["Normal"], fontSize=9, leading=13)
    h1 = ParagraphStyle("H1CN", parent=styles["Heading1"], fontSize=15, spaceBefore=8, spaceAfter=6)
    h2 = ParagraphStyle("H2CN", parent=styles["Heading2"], fontSize=12, spaceBefore=6, spaceAfter=4)
    story = [Paragraph(f"{project_name} 数据库设计说明书", styles["Title"])]
    story.append(Paragraph(f"作者：{author or '-'}　学号：{student_id or '-'}", body))
    story.append(Paragraph(f"自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · AI Database Architect", body))

    story.append(Paragraph("1. 项目概述", h1))
    if project_description:
        story.append(Paragraph(project_description, body))
    story.append(Paragraph(f"数据库名称：{schema.database_name}；表数量：{len(schema.tables)}；关系数量：{len(relationships)}", body))

    story.append(Paragraph("2. 需求分析", h1))
    story.append(Paragraph("说明：请根据实际业务需求补充需求描述。以下为从数据库结构中识别出的实体与联系概要。", body))
    entities = concept_model.get("entities", []) if concept_model else []
    for e in entities:
        attrs = "、".join(a["name"] for a in (e.get("attributes") or [])[:8])
        story.append(Paragraph(f"实体 {e['name']}：{attrs}", body))

    story.append(Paragraph("3. 概念结构设计", h1))
    story.append(Paragraph("采用 Chen 记法 ER 概念模型描述业务实体、属性与联系。", body))
    for e in entities:
        story.append(Paragraph(e["name"], h2))
        for a in e.get("attributes") or []:
            tag = "（主键）" if a.get("is_pk") else ""
            story.append(Paragraph(f"· {a['name']}{tag}", body))

    story.append(Paragraph("4. 逻辑结构设计", h1))
    for t in schema.tables:
        story.append(Paragraph(t.name, h2))
        rows = [["字段", "类型", "可空", "主键", "唯一", "默认值", "注释"]]
        for c in t.columns:
            rows.append(
                [c.name, c.data_type, "是" if c.nullable else "否",
                 "✓" if c.is_primary_key else "", "✓" if c.is_unique else "",
                 c.default_value or "", c.comment or ""]
            )
        tbl = Table(rows, repeatRows=1, colWidths=[30 * mm, 24 * mm, 10 * mm, 10 * mm, 10 * mm, 22 * mm, 44 * mm])
        tbl.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DBEAFE")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(tbl)
        story.append(Spacer(1, 6))

    story.append(Paragraph("5. 规范化分析", h1))
    story.append(Paragraph("提示：可结合『架构评审』中的 AI 意见补充范式分析章节。", body))
    for t in schema.tables:
        pk = "、".join(c.name for c in t.columns if c.is_primary_key)
        story.append(Paragraph(f"· {t.name}：主键 {pk or '无'}；满足 1NF。", body))

    story.append(Paragraph("6. 关系说明", h1))
    rows = [["源表.字段", "目标表.字段", "基数", "类型"]]
    for r in relationships:
        rows.append(
            [
                f"{r.get('source_table')}.{r.get('source_column')}",
                f"{r.get('target_table')}.{r.get('target_column')}",
                r.get("cardinality") or "",
                r.get("source_type") or "",
            ]
        )
    tbl = Table(rows, repeatRows=1, colWidths=[52 * mm, 52 * mm, 30 * mm, 30 * mm])
    tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DBEAFE")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ]
        )
    )
    story.append(tbl)

    story.append(Paragraph("7. 总结", h1))
    story.append(
        Paragraph(
            f"本系统数据库共设计 {len(schema.tables)} 张表、{sum(len(t.columns) for t in schema.tables)} 个字段、"
            f"{len(relationships)} 条关系，覆盖了业务的核心数据需求，并遵循数据库规范化原则。",
            body,
        )
    )
    doc.build(story)
    return buf.getvalue()
