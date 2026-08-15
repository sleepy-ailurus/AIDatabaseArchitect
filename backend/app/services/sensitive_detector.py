"""Sensitive data identifier - detect PII / privacy fields (feature 10).

Rule-based detection over column names + comments + types, with optional
read-only data sampling to raise/lower confidence. Categories are aligned with
GDPR (personal data vs special categories) and PIPL (敏感个人信息).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.services.schema_parser import ParsedSchema


@dataclass
class Rule:
    category: str
    label: str
    risk_level: str  # high | medium | low
    name_pattern: re.Pattern
    comment_keywords: tuple[str, ...] = ()
    data_type_hint: tuple[str, ...] = ()
    sample_validator: str | None = None  # key into _SAMPLE_VALIDATORS
    gdpr_special: bool = False
    pipl_sensitive: bool = False


_RULES: list[Rule] = [
    Rule(
        "mobile_phone", "手机号码", "high",
        re.compile(r"(mobile|phone|tel|cell|contact|手机|电话|手机号|联系方式)", re.I),
        ("手机", "电话"),
        ("VARCHAR", "CHAR"),
        "phone",
    ),
    Rule(
        "id_card", "身份证号", "high",
        re.compile(r"(id_card|idcard|identity|id_no|sfz|身份证|证件号)", re.I),
        ("身份证", "证件号"),
        ("VARCHAR", "CHAR"),
        "id_card",
        gdpr_special=True,
        pipl_sensitive=True,
    ),
    Rule(
        "email", "电子邮箱", "high",
        re.compile(r"(email|mail|邮箱|邮件)", re.I),
        ("邮箱", "邮件"),
        ("VARCHAR", "CHAR"),
        "email",
    ),
    Rule(
        "password", "密码/口令", "high",
        re.compile(r"(password|passwd|pwd|secret|pass_|密码|口令|密钥)", re.I),
        ("密码", "口令", "密钥"),
        ("VARCHAR", "CHAR", "TEXT"),
    ),
    Rule(
        "bank_card", "银行卡号", "high",
        re.compile(r"(bank_card|card_no|bankcard|银行卡|卡号|account_no)", re.I),
        ("银行卡", "卡号"),
        ("VARCHAR", "CHAR"),
        "bank_card",
        pipl_sensitive=True,
    ),
    Rule(
        "token", "Token/API Key", "high",
        re.compile(r"(token|api_key|apikey|access_key|secret_key|auth)", re.I),
        ("令牌", "密钥", "凭证"),
        ("VARCHAR", "CHAR", "TEXT"),
    ),
    Rule(
        "address", "地址", "medium",
        re.compile(r"(address|addr|location|地址|住址)", re.I),
        ("地址", "住址"),
        ("VARCHAR", "CHAR", "TEXT"),
    ),
    Rule(
        "ip", "IP 地址", "medium",
        re.compile(r"(ip_addr|ip_address|client_ip|remote_ip|ip$|ip_)", re.I),
        ("IP", "地址"),
        ("VARCHAR", "CHAR"),
        "ip",
    ),
    Rule(
        "birthday", "出生日期", "medium",
        re.compile(r"(birth|birthday|born|出生|生日)", re.I),
        ("出生", "生日"),
        ("DATE", "DATETIME", "VARCHAR", "CHAR"),
        "date",
    ),
    Rule(
        "name", "姓名", "medium",
        re.compile(r"(real_name|username|nickname|full_name|name|姓名|名称)", re.I),
        ("姓名", "名字"),
        ("VARCHAR", "CHAR"),
    ),
    Rule(
        "gender", "性别", "low",
        re.compile(r"(gender|sex|性别)", re.I),
        ("性别",),
        ("VARCHAR", "CHAR", "TINYINT"),
    ),
    Rule(
        "salary", "收入/财务", "medium",
        re.compile(r"(salary|income|wage|payroll|工资|薪酬|收入)", re.I),
        ("工资", "薪酬", "收入"),
        ("DECIMAL", "FLOAT", "DOUBLE", "INT"),
        pipl_sensitive=True,
    ),
    Rule(
        "health", "健康信息", "high",
        re.compile(r"(health|medical|diagnosis|病历|健康|体检|医疗)", re.I),
        ("健康", "医疗", "病历", "体检"),
        ("VARCHAR", "TEXT"),
        gdpr_special=True,
        pipl_sensitive=True,
    ),
]


_SAMPLE_VALIDATORS: dict[str, re.Pattern] = {
    "phone": re.compile(r"^1[3-9]\d{9}$|^\+?[0-9\- ]{7,15}$"),
    "email": re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
    "id_card": re.compile(r"^\d{17}[\dXx]$|^\d{15}$"),
    "bank_card": re.compile(r"^\d{12,19}$"),
    "ip": re.compile(r"^\d{1,3}(\.\d{1,3}){3}$"),
    "date": re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}"),
}


def _match_rule(column_name: str, comment: str, data_type: str, rule: Rule) -> float:
    """Return confidence 0..1 that a column matches a rule."""
    name_hit = bool(rule.name_pattern.search(column_name or ""))
    comment_hit = bool(comment) and any(k in comment for k in rule.comment_keywords)
    type_ok = not rule.data_type_hint or (data_type or "").upper() in {
        t.upper() for t in rule.data_type_hint
    }
    if not (name_hit or comment_hit):
        return 0.0
    if name_hit and comment_hit and type_ok:
        return 0.95
    if name_hit and type_ok:
        return 0.8
    if comment_hit and type_ok:
        return 0.65
    if name_hit or comment_hit:
        return 0.45
    return 0.0


def detect_sensitive_fields(schema: ParsedSchema) -> list[dict[str, Any]]:
    """Rule-based detection over schema metadata (no DB access)."""
    findings: list[dict[str, Any]] = []
    for t in schema.tables:
        for c in t.columns:
            for rule in _RULES:
                conf = _match_rule(c.name, c.comment or "", c.data_type, rule)
                if conf <= 0.0:
                    continue
                reason = []
                if rule.name_pattern.search(c.name):
                    reason.append(f"字段名匹配：{c.name}")
                if c.comment and any(k in c.comment for k in rule.comment_keywords):
                    reason.append(f"注释匹配：{c.comment}")
                findings.append(
                    {
                        "table_name": t.name,
                        "column_name": c.name,
                        "category": rule.category,
                        "category_label": rule.label,
                        "risk_level": rule.risk_level,
                        "confidence": round(conf, 3),
                        "matched_reason": "；".join(reason),
                        "sample_hits": None,
                        "sample_total": None,
                        "gdpr_special": rule.gdpr_special,
                        "pipi_sensitive": rule.pipl_sensitive,
                    }
                )
                break  # first matching rule per column wins
    return findings


def sample_validate(
    db_engine,
    table_name: str,
    column_name: str,
    sample_size: int = 100,
) -> dict[str, Any]:
    """Read a small sample (read-only) and validate values against format rules.

    Returns {sample_hits, sample_total, confidence_delta}.
    """
    rule = next(
        (r for r in _RULES if r.sample_validator and re.search(r.name_pattern, column_name)),
        None,
    )
    if rule is None or rule.sample_validator not in _SAMPLE_VALIDATORS:
        return {"sample_hits": 0, "sample_total": 0, "confidence_delta": 0.0}
    pattern = _SAMPLE_VALIDATORS[rule.sample_validator]
    from sqlalchemy import text

    try:
        with db_engine.connect() as conn:
            rows = conn.execute(
                text(
                    f'SELECT `{column_name}` FROM `{table_name}` '
                    f"WHERE `{column_name}` IS NOT NULL LIMIT {int(sample_size)}"
                )
            ).fetchall()
        total = len(rows)
        hits = sum(1 for row in rows if row[0] is not None and pattern.search(str(row[0])))
    except Exception:
        return {"sample_hits": 0, "sample_total": 0, "confidence_delta": 0.0}
    if total == 0:
        return {"sample_hits": 0, "sample_total": 0, "confidence_delta": 0.0}
    ratio = hits / total
    if ratio >= 0.9:
        delta = 0.1
    elif ratio >= 0.5:
        delta = 0.0
    elif ratio > 0:
        delta = -0.15
    else:
        delta = -0.35
    return {"sample_hits": hits, "sample_total": total, "confidence_delta": delta}


def risk_display(risk_level: str) -> str:
    return {
        "high": "高",
        "medium": "中",
        "low": "低",
    }.get(risk_level, risk_level)


def build_report(findings: list[dict]) -> str:
    lines = ["# 敏感数据识别报告", ""]
    lines.append("> 自动生成于 AI Database Architect · 对标 GDPR / 个保法（PIPL）")
    lines.append("")
    lines.append("## 统计")
    lines.append("")
    counts = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        counts[f["risk_level"]] = counts.get(f["risk_level"], 0) + 1
    lines.append(f"- 高风险：{counts['high']} · 中风险：{counts['medium']} · 低风险：{counts['low']}")
    lines.append("")
    lines.append("## 明细")
    lines.append("")
    lines.append("| 表.字段 | 类别 | 风险 | 置信度 | 识别依据 | 抽样命中 |")
    lines.append("|--------|------|------|--------|----------|----------|")
    for f in findings:
        sample = (
            f"{f.get('sample_hits')}/{f.get('sample_total')}"
            if f.get("sample_total")
            else "-"
        )
        lines.append(
            f"| `{f['table_name']}.{f['column_name']}` | {f['category_label']} | "
            f"{risk_display(f['risk_level'])} | {f['confidence']:.0%} | "
            f"{f.get('matched_reason') or ''} | {sample} |"
        )
    lines.append("")
    lines.append("## 建议措施")
    lines.append("")
    lines.append("1. 高风险字段（密码/令牌）：使用加盐哈希存储（如 bcrypt/argon2），禁止明文。")
    lines.append("2. 身份/银行卡/健康等敏感个人信息：加密存储（AES-256）并限制访问权限。")
    lines.append("3. 涉及个人信息导出时进行脱敏（掩码）处理。")
    lines.append("4. 遵循最小化原则，仅在必要时收集与保留。")
    lines.append("5. 建立访问审计日志，满足 GDPR 第 30 条 / 个保法合规要求。")
    return "\n".join(lines)
