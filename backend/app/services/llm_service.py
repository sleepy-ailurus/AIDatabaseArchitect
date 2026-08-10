"""LLM integration service (OpenAI-compatible API: DeepSeek, Qwen, OpenAI, ...).

Builds a structured prompt from schema metadata, calls the chat completions
endpoint via httpx, parses the JSON response and validates the inferred
relationships against the actual schema.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

import httpx

from app.services.crypto import decrypt
from app.services.relation_candidate import CandidateRelation, candidate_to_dict
from app.services.schema_parser import ParsedSchema, is_type_compatible


# ---------------------------------------------------------------------------
# Sliding window rate limiter (in-memory, per-config)
# ---------------------------------------------------------------------------
_rate_limit_windows: dict[int, list[float]] = {}


def check_rate_limit(config_id: int, rate_limit: int, unlimited: bool = False) -> bool:
    """Check whether a request is within the rate limit using a 1-second sliding window.

    Returns True if the request is allowed, False if rate-limited.
    When *unlimited* is True, always returns True.
    """
    if unlimited:
        return True

    now = time.time()
    window_start = now - 1.0  # 1-second window

    timestamps = _rate_limit_windows.get(config_id, [])
    # Remove timestamps outside the window
    timestamps = [t for t in timestamps if t >= window_start]

    if len(timestamps) < rate_limit:
        timestamps.append(now)
        _rate_limit_windows[config_id] = timestamps
        return True

    _rate_limit_windows[config_id] = timestamps
    return False


# ---------------------------------------------------------------------------
# Config wrapper
# ---------------------------------------------------------------------------
@dataclass
class LLMSettings:
    provider: str
    base_url: str
    api_key: str
    model: str
    endpoint_path: str = "/chat/completions"
    temperature: float = 0.2
    max_tokens: int = 4096
    timeout_seconds: int = 60
    max_retries: int = 2
    config_id: int | None = None
    rate_limit: int = 50
    rate_unlimited: bool = False


def settings_from_config(config) -> LLMSettings:
    """Build LLMSettings from a LLMConfig ORM object."""
    return LLMSettings(
        provider=config.provider,
        base_url=config.base_url,
        api_key=decrypt(config.api_key_encrypted) or "",
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries,
        config_id=config.id,
        rate_limit=config.rate_limit,
        rate_unlimited=config.rate_unlimited,
    )


# ---------------------------------------------------------------------------
# Test connection
# ---------------------------------------------------------------------------
def test_llm_connection(settings: LLMSettings) -> dict:
    """Send a minimal chat request to verify credentials/model availability."""
    if settings.config_id is not None:
        if not check_rate_limit(settings.config_id, settings.rate_limit, settings.rate_unlimited):
            return {
                "success": False,
                "message": f"请求频率超限（{settings.rate_limit}次/秒），请稍后重试",
                "elapsed_ms": 0,
                "model": settings.model,
            }

    start = time.time()
    url = _chat_url(settings.base_url, settings.endpoint_path)
    headers = {"Authorization": f"Bearer {settings.api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 8,
        "temperature": 0,
    }
    try:
        with httpx.Client(timeout=settings.timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=payload)
        elapsed = int((time.time() - start) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            model_used = data.get("model", settings.model)
            return {
                "success": True,
                "message": "连接成功，模型可用",
                "elapsed_ms": elapsed,
                "model": model_used,
            }
        return {
            "success": False,
            "message": _http_error_message(resp.status_code, resp.text),
            "elapsed_ms": elapsed,
            "model": settings.model,
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "message": f"请求超时（{settings.timeout_seconds}s），请检查网络或 Base URL",
            "elapsed_ms": int((time.time() - start) * 1000),
            "model": settings.model,
        }
    except httpx.ConnectError as exc:
        return {
            "success": False,
            "message": f"无法连接到 API 端点: {exc}",
            "elapsed_ms": int((time.time() - start) * 1000),
            "model": settings.model,
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"连接失败: {exc}",
            "elapsed_ms": int((time.time() - start) * 1000),
            "model": settings.model,
        }


def _http_error_message(status: int, body: str) -> str:
    if status == 401:
        return "API Key 无效或认证失败，请检查凭据"
    if status == 404:
        return "模型不存在或 Base URL 错误，请检查模型名称和地址"
    if status == 429:
        return "请求被限流，请稍后重试或检查配额"
    if status in (400, 422):
        return f"请求参数错误: {_truncate(body)}"
    if status >= 500:
        return f"模型服务异常（{status}），请稍后重试"
    return f"请求失败（HTTP {status}）: {_truncate(body)}"


def _truncate(text: str, n: int = 300) -> str:
    return text[:n] + "..." if len(text) > n else text


def _chat_url(base_url: str, endpoint_path: str = "/chat/completions") -> str:
    base = base_url.rstrip("/")
    ep = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"
    if base.endswith(ep):
        return base
    # Ollama and other local endpoints don't use /v1 prefix
    if ep in ("/api/chat", "/chat/completions", "/responses"):
        # Only add /v1 for OpenAI-compatible providers, not Ollama
        if base.endswith("/v1"):
            return base + ep
        if "/v1/" in base:
            return base + ep
        if base.endswith(":11434") or "ollama" in base.lower():
            return base + ep
        return base + "/v1" + ep
    return base + ep


# ---------------------------------------------------------------------------
# Schema summarization for the prompt
# ---------------------------------------------------------------------------
def _summarize_schema(schema: ParsedSchema) -> list[dict]:
    """Produce a compact, metadata-only description of the schema for the LLM."""
    tables = []
    for t in schema.tables:
        cols = []
        for c in t.columns:
            cols.append(
                {
                    "name": c.name,
                    "type": c.data_type,
                    "nullable": c.nullable,
                    "pk": c.is_primary_key,
                    "unique": c.is_unique,
                    "comment": c.comment,
                }
            )
        tables.append(
            {
                "name": t.name,
                "comment": t.comment,
                "columns": cols,
            }
        )
    return tables


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "你是一个数据库架构分析专家。你的任务是根据提供的数据库 Schema 元数据，"
    "判断给定的候选表关系是否成立，并给出结构化的 JSON 结果。\n"
    "你必须严格遵守以下规则：\n"
    "1. 只能输出给定 Schema 中真实存在的表和字段。\n"
    "2. 只能对提供的候选关系进行判断，不要凭空创造新的关系。\n"
    "3. 输出必须是合法的 JSON 数组，每个元素包含字段：source_table, source_column, "
    "target_table, target_column, cardinality(可选值: many-to-one, one-to-many, "
    "one-to-one, many-to-many), confidence(0-1 的浮点数), reason(字符串数组), "
    "risks(字符串数组)。\n"
    "4. confidence 表示你认为该关系成立的可信度，0.85 以上为高，0.60-0.84 为中，0.60 以下为低。\n"
    "5. 不要输出任何 JSON 以外的文字。"
)


def _build_prompt(schema: ParsedSchema, candidates: list[CandidateRelation]) -> str:
    schema_desc = json.dumps(_summarize_schema(schema), ensure_ascii=False)
    cand_desc = json.dumps([candidate_to_dict(c) for c in candidates], ensure_ascii=False)
    return (
        f"数据库 Schema 元数据如下：\n{schema_desc}\n\n"
        f"以下是待判断的候选关系列表：\n{cand_desc}\n\n"
        "请对每一个候选关系进行判断，输出 JSON 数组。"
    )


# ---------------------------------------------------------------------------
# Result validation
# ---------------------------------------------------------------------------
@dataclass
class LLMRelationResult:
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    cardinality: str
    confidence: float
    reason: list[str]
    risks: list[str]
    valid: bool = True
    validation_error: str | None = None


def _validate_result(item: dict, schema: ParsedSchema, candidate_keys: set[tuple[str, str, str, str]]) -> LLMRelationResult:
    def err(msg: str) -> LLMRelationResult:
        return LLMRelationResult(
            source_table=item.get("source_table", ""),
            source_column=item.get("source_column", ""),
            target_table=item.get("target_table", ""),
            target_column=item.get("target_column", ""),
            cardinality=item.get("cardinality", "many-to-one"),
            confidence=float(item.get("confidence", 0.0)),
            reason=item.get("reason", []) or [],
            risks=item.get("risks", []) or [],
            valid=False,
            validation_error=msg,
        )

    s_table = item.get("source_table")
    s_col = item.get("source_column")
    t_table = item.get("target_table")
    t_col = item.get("target_column")
    if not all([s_table, s_col, t_table, t_col]):
        return err("缺少必要字段")

    key = (s_table.lower(), s_col.lower(), t_table.lower(), t_col.lower())
    if key not in candidate_keys:
        return err("关系不在候选范围内，已忽略")

    # Verify tables/columns exist in schema.
    src_table_obj = next((t for t in schema.tables if t.name.lower() == s_table.lower()), None)
    tgt_table_obj = next((t for t in schema.tables if t.name.lower() == t_table.lower()), None)
    if not src_table_obj:
        return err(f"源表 {s_table} 不存在")
    if not tgt_table_obj:
        return err(f"目标表 {t_table} 不存在")
    src_col_obj = next((c for c in src_table_obj.columns if c.name.lower() == s_col.lower()), None)
    tgt_col_obj = next((c for c in tgt_table_obj.columns if c.name.lower() == t_col.lower()), None)
    if not src_col_obj:
        return err(f"源字段 {s_table}.{s_col} 不存在")
    if not tgt_col_obj:
        return err(f"目标字段 {t_table}.{t_col} 不存在")

    # Type compatibility.
    if not is_type_compatible(src_col_obj.data_type, tgt_col_obj.data_type):
        return err(f"字段类型不兼容 ({src_col_obj.data_type} ↔ {tgt_col_obj.data_type})")

    # Confidence range.
    try:
        conf = float(item.get("confidence", 0.0))
    except (TypeError, ValueError):
        return err("confidence 不是合法数值")
    if conf < 0 or conf > 1:
        return err("confidence 超出 0-1 范围")

    # Cardinality enum.
    cardinality = item.get("cardinality", "many-to-one")
    allowed = {"many-to-one", "one-to-many", "one-to-one", "many-to-many", "1:1", "1:N", "N:N"}
    if cardinality not in allowed:
        return err(f"cardinality 值非法: {cardinality}")

    return LLMRelationResult(
        source_table=s_table,
        source_column=s_col,
        target_table=t_table,
        target_column=t_col,
        cardinality=cardinality,
        confidence=conf,
        reason=item.get("reason", []) or [],
        risks=item.get("risks", []) or [],
        valid=True,
    )


def _parse_json_response(text: str) -> list[dict]:
    """Extract a JSON array from an LLM response that may contain code fences."""
    cleaned = text.strip()
    # Strip markdown code fences.
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Remove first fence line.
        lines = lines[1:]
        # Remove trailing fence line if present.
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    # Find the first JSON array.
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# Main analysis entry point
# ---------------------------------------------------------------------------
def analyze_candidates(
    schema: ParsedSchema,
    candidates: list[CandidateRelation],
    settings: LLMSettings,
) -> list[LLMRelationResult]:
    """Call the LLM to analyze candidate relationships and validate the output.

    If there are no candidates, returns an empty list immediately.
    """
    if not candidates:
        return []

    if settings.config_id is not None:
        if not check_rate_limit(settings.config_id, settings.rate_limit, settings.rate_unlimited):
            raise LLMError(f"请求频率超限（{settings.rate_limit}次/秒），请稍后重试")

    candidate_keys = {
        (c.source_table.lower(), c.source_column.lower(), c.target_table.lower(), c.target_column.lower())
        for c in candidates
    }

    prompt = _build_prompt(schema, candidates)
    headers = {"Authorization": f"Bearer {settings.api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
    }
    url = _chat_url(settings.base_url, settings.endpoint_path)

    last_error: str | None = None
    for attempt in range(settings.max_retries + 1):
        try:
            with httpx.Client(timeout=settings.timeout_seconds) as client:
                resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                try:
                    items = _parse_json_response(content)
                except json.JSONDecodeError as exc:
                    last_error = f"LLM 返回内容无法解析为 JSON: {exc}"
                    continue
                if not isinstance(items, list):
                    last_error = "LLM 返回内容不是 JSON 数组"
                    continue
                return [_validate_result(it, schema, candidate_keys) for it in items]
            last_error = _http_error_message(resp.status_code, resp.text)
            # Don't retry on auth/model errors.
            if resp.status_code in (401, 404):
                break
        except httpx.TimeoutException:
            last_error = f"请求超时（{settings.timeout_seconds}s）"
        except httpx.ConnectError as exc:
            last_error = f"无法连接到 API 端点: {exc}"
        except Exception as exc:
            last_error = f"调用 LLM 失败: {exc}"

    raise LLMError(last_error or "调用 LLM 失败")


class LLMError(Exception):
    pass
