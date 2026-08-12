"""LLM integration service (OpenAI-compatible API: DeepSeek, Qwen, OpenAI, ...).

Builds a structured prompt from schema metadata, calls the chat completions
endpoint via httpx, parses the JSON response and validates the inferred
relationships against the actual schema.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable

import httpx

from app.services.crypto import decrypt
from app.services.relation_candidate import CandidateRelation, _extract_hint, candidate_to_dict
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
    endpoint_path = getattr(config, "endpoint_path", None)
    if not endpoint_path:
        endpoint_path = "/api/chat" if config.provider == "ollama" else "/chat/completions"
    return LLMSettings(
        provider=config.provider,
        base_url=config.base_url,
        api_key=decrypt(config.api_key_encrypted) or "",
        model=config.model,
        endpoint_path=endpoint_path,
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
    headers = {"Content-Type": "application/json"}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"
    payload = {
        "model": settings.model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 8,
        "temperature": 0,
        "stream": False,
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
    # If the endpoint already carries a /v1 prefix, do not duplicate a trailing /v1 in base_url.
    if ep.startswith("/v1/"):
        if base.endswith("/v1"):
            return base + ep[len("/v1"):]
        return base + ep
    # Legacy Ollama native endpoint: use as-is.
    if ep == "/api/chat":
        return base + ep
    # OpenAI-compatible endpoints: ensure /v1 prefix when missing.
    if ep in ("/chat/completions", "/responses"):
        if base.endswith("/v1") or "/v1/" in base:
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
    "判断给定的候选表关系是否成立，并基于 Schema 语义补充额外的合理关系，"
    "最终给出结构化的 JSON 结果。\n"
    "你必须严格遵守以下规则：\n"
    "1. 只能输出给定 Schema 中真实存在的表和字段。\n"
    "2. 对提供的候选关系进行判断（只输出你认为成立的关系）；同时，如果发现 Schema 中"
    "还存在未列出的合理关系（例如 xxx_id 指向另一张表的主键或唯一键，且两张表名没有"
    "直接对应关系），也可以补充输出，但必须使用 Schema 中真实存在的表和字段，"
    "不得凭空捏造。\n"
    "3. 输出必须是合法的 JSON 数组，每个元素包含字段：source_table, source_column, "
    "target_table, target_column, cardinality, confidence(0-1 的浮点数), reason(字符串数组), "
    "risks(字符串数组)。\n"
    "4. cardinality 的可选值: many-to-one, one-to-many, one-to-one, many-to-many。\n"
    "   重要：cardinality 的第一个值对应 source 表（源表）端，第二个值对应 target 表（目标表）端。\n"
    "   - many-to-one 表示 source 端是多方（N），target 端是一方（1），即 source_table 有多条记录对应 target_table 的一条记录。\n"
    "   - one-to-many 表示 source 端是一方（1），target 端是多方（N），即 source_table 的一条记录对应 target_table 的多条记录。\n"
    "   - 通常，源表的 source_column 是外键（非主键）时，source 端是多方（many-to-one）。\n"
    "5. confidence 表示你认为该关系成立的可信度，0.85 以上为高，0.60-0.84 为中，0.60 以下为低。\n"
    "6. 不要输出任何 JSON 以外的文字。"
)


def _build_prompt(schema: ParsedSchema, candidates: list[CandidateRelation]) -> str:
    schema_desc = json.dumps(_summarize_schema(schema), ensure_ascii=False)
    cand_desc = json.dumps([candidate_to_dict(c) for c in candidates], ensure_ascii=False)
    if candidates:
        instruction = (
            "请对每一个候选关系进行判断，只输出你认为成立的关系；"
            "此外，如果你认为 Schema 中还存在未列出的合理关系，也可以一并补充输出。"
        )
    else:
        instruction = (
            "候选关系列表为空。请根据 Schema 语义找出你认为合理的外键式逻辑关系"
            "（例如 xxx_id 指向另一张表的主键或唯一键），输出 JSON 数组。"
        )
    return (
        f"数据库 Schema 元数据如下：\n{schema_desc}\n\n"
        f"以下是待判断的候选关系列表：\n{cand_desc}\n\n"
        f"{instruction}"
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


def _is_plausible_new_proposal(item: dict, schema: ParsedSchema) -> bool:
    """Structural gate for relations the LLM proposes outside the rule-candidate list.

    A free-form proposal is only accepted when it references real tables/columns,
    the source column is a non-PK reference-like column (e.g. xxx_id), and the
    target column is a PK or unique key of the target table. This prevents the
    LLM from inventing hallucinated relationships. Type compatibility is checked
    separately by the caller.
    """
    s_table = (item.get("source_table") or "").lower()
    s_col = (item.get("source_column") or "").lower()
    t_table = (item.get("target_table") or "").lower()
    t_col = (item.get("target_column") or "").lower()
    if not all([s_table, s_col, t_table, t_col]):
        return False
    src_t = next((t for t in schema.tables if t.name.lower() == s_table), None)
    tgt_t = next((t for t in schema.tables if t.name.lower() == t_table), None)
    if not src_t or not tgt_t:
        return False
    src_c = next((c for c in src_t.columns if c.name.lower() == s_col), None)
    tgt_c = next((c for c in tgt_t.columns if c.name.lower() == t_col), None)
    if not src_c or not tgt_c:
        return False
    if src_c.is_primary_key:
        return False
    if _extract_hint(src_c.name) is None:
        return False
    if not (tgt_c.is_primary_key or tgt_c.is_unique):
        return False
    return True


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
    if key not in candidate_keys and not _is_plausible_new_proposal(item, schema):
        return err("关系不在候选范围内且未通过结构校验，已忽略")

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

    # Programmatic cardinality correction based on FK direction and UNIQUE constraints.
    # source_column is the FK column (not PK), target_column is PK → default N:1 (many-to-one).
    # BUT if source_column is additionally UNIQUE → each FK value can occur at most once,
    # so the relationship is strictly 1:1 (e.g. teacher_info.tea_id → teacher.tea_id
    # where teacher_info has a UNIQUE KEY on tea_id).
    src_is_pk = bool(getattr(src_col_obj, "is_primary_key", False))
    tgt_is_pk = bool(getattr(tgt_col_obj, "is_primary_key", False))
    src_is_unique = bool(getattr(src_col_obj, "is_unique", False))

    if not src_is_pk and tgt_is_pk:
        # source has FK semantics pointing at a PK target.
        if src_is_unique:
            # FK column itself is UNIQUE → at most one source row per target row → 1:1
            cardinality = "one-to-one"
        else:
            # Standard FK → source is "many", target is "one".
            cardinality = "many-to-one"
    elif src_is_pk and not tgt_is_pk:
        # source is PK referencing FK → 1:N (one-to-many): source=one, target=many
        cardinality = "one-to-many"
    elif src_is_pk and tgt_is_pk:
        # PK-to-PK shared → one-to-one
        cardinality = "one-to-one"
    else:
        # Neither is PK (weak reference) — keep LLM's original judgment, but normalize aliases.
        cardinality_aliases = {
            "1:1": "one-to-one",
            "1:N": "one-to-many",
            "N:1": "many-to-one",
            "N:N": "many-to-many",
        }
        cardinality = cardinality_aliases.get(cardinality.upper(), cardinality)

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
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        snippet = text[:800].replace("\n", "\\n").replace("\r", "")
        raise ValueError(
            f"无法解析为 JSON ({exc}); 原始响应前 800 字符: {snippet}"
        ) from exc


# ---------------------------------------------------------------------------
# Main analysis entry point
# ---------------------------------------------------------------------------
def analyze_candidates(
    schema: ParsedSchema,
    candidates: list[CandidateRelation],
    settings: LLMSettings,
    is_cancelled: Callable[[], bool] | None = None,
) -> list[LLMRelationResult]:
    """Call the LLM to analyze candidate relationships and validate the output.

    When there are no rule candidates the LLM is still called in discovery mode
    so semantically-obvious relations (e.g. owner_id -> user.id) can be proposed
    and structurally validated.

    ``is_cancelled`` (when provided) is checked before every attempt so a user
    cancellation can interrupt long-running retries promptly.
    """
    if settings.config_id is not None:
        if not check_rate_limit(settings.config_id, settings.rate_limit, settings.rate_unlimited):
            raise LLMError(f"请求频率超限（{settings.rate_limit}次/秒），请稍后重试")

    if is_cancelled is not None and is_cancelled():
        raise RuntimeError("Task cancelled by user")

    candidate_keys = {
        (c.source_table.lower(), c.source_column.lower(), c.target_table.lower(), c.target_column.lower())
        for c in candidates
    }

    prompt = _build_prompt(schema, candidates)
    headers = {"Content-Type": "application/json"}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"
    payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "stream": False,
    }
    # Qwen3 reasoning models on DashScope (阿里云百炼) spend a long time in the
    # thinking phase on large schema prompts and can blow past the configured
    # timeout. Analysis only needs the final judgment, so disable thinking for
    # these providers to keep each attempt well within the request timeout.
    if "dashscope" in (settings.base_url or "").lower():
        payload["enable_thinking"] = False
    url = _chat_url(settings.base_url, settings.endpoint_path)

    last_error: str | None = None
    for attempt in range(settings.max_retries + 1):
        if is_cancelled is not None and is_cancelled():
            raise RuntimeError("Task cancelled by user")
        try:
            # Analysis prompts are much larger than a connectivity ping; give the
            # call a little headroom over the configured timeout so a slow model
            # still gets a fair chance on its first attempt.
            with httpx.Client(timeout=max(settings.timeout_seconds, 90)) as client:
                resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                try:
                    items = _parse_json_response(content)
                except ValueError as exc:
                    last_error = str(exc)
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
