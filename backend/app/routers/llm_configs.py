"""LLM configuration center router.

CRUD for model provider configs (DeepSeek, Gemini, Qwen, OpenAI-compatible).
API keys are encrypted at rest and never returned in full; the list/detail
responses expose a masked representation only.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LLMConfig
from app.schemas import (
    LLMConfigCreate,
    LLMConfigOut,
    LLMConfigUpdate,
    LLMTestRequest,
    LLMTestResult,
)
from app.services import crypto
from app.services.llm_service import LLMSettings, settings_from_config, test_llm_connection

router = APIRouter(prefix="/api", tags=["llm-configs"])

_PROVIDER_DEFAULTS = {
    "openai": "https://api.openai.com/v1",
    "ollama": "http://localhost:11434",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}


def _to_out(cfg: LLMConfig) -> LLMConfigOut:
    api_key_plain = crypto.decrypt(cfg.api_key_encrypted)
    return LLMConfigOut(
        id=cfg.id,
        name=cfg.name,
        provider=cfg.provider,
        base_url=cfg.base_url,
        model=cfg.model,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        timeout_seconds=cfg.timeout_seconds,
        max_retries=cfg.max_retries,
        rate_limit=cfg.rate_limit,
        rate_unlimited=cfg.rate_unlimited,
        usage=cfg.usage or [],
        usage_list=cfg.usage or [],
        is_default=cfg.is_default,
        is_active=cfg.is_active,
        last_test_ok=cfg.last_test_ok,
        created_at=cfg.created_at,
        api_key_masked=crypto.mask(api_key_plain) if api_key_plain else None,
        status_ok=cfg.last_test_ok,
    )


def _normalize_usage(payload) -> list[str] | None:
    usage = getattr(payload, "usage", None)
    usage_list = getattr(payload, "usage_list", None)
    return usage_list if usage_list is not None else usage


@router.get("/llm-configs", response_model=list[LLMConfigOut])
def list_configs(db: Session = Depends(get_db)):
    configs = db.query(LLMConfig).order_by(LLMConfig.id.asc()).all()
    return [_to_out(c) for c in configs]


@router.get("/llm-configs/{config_id}", response_model=LLMConfigOut)
def get_config(config_id: int, db: Session = Depends(get_db)):
    cfg = db.get(LLMConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="配置不存在")
    return _to_out(cfg)


@router.post("/llm-configs", response_model=LLMConfigOut, status_code=status.HTTP_201_CREATED)
def create_config(payload: LLMConfigCreate, db: Session = Depends(get_db)):
    base_url = payload.base_url or _PROVIDER_DEFAULTS.get(payload.provider, "")
    cfg = LLMConfig(
        name=payload.name,
        provider=payload.provider,
        base_url=base_url,
        api_key_encrypted=crypto.encrypt(payload.api_key) if payload.api_key else None,
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        timeout_seconds=payload.timeout_seconds,
        max_retries=payload.max_retries,
        rate_limit=payload.rate_limit,
        rate_unlimited=payload.rate_unlimited,
        usage=_normalize_usage(payload) or [],
        is_default=payload.is_default,
        is_active=payload.is_active if payload.is_active is not None else True,
    )
    db.add(cfg)
    db.flush()
    if payload.is_default:
        _unset_other_defaults(db, cfg.id)
    db.commit()
    db.refresh(cfg)
    return _to_out(cfg)


@router.patch("/llm-configs/{config_id}", response_model=LLMConfigOut)
def update_config(config_id: int, payload: LLMConfigUpdate, db: Session = Depends(get_db)):
    cfg = db.get(LLMConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="配置不存在")

    data = payload.model_dump(exclude_unset=True)
    # Handle the api_key specially: only update if a new one is provided.
    api_key = data.pop("api_key", None)
    usage_list = data.pop("usage_list", None)
    usage = data.pop("usage", None)

    for key, value in data.items():
        setattr(cfg, key, value)
    if api_key:
        cfg.api_key_encrypted = crypto.encrypt(api_key)
    if usage_list is not None or usage is not None:
        cfg.usage = usage_list if usage_list is not None else usage

    if cfg.is_default:
        _unset_other_defaults(db, cfg.id)

    db.commit()
    db.refresh(cfg)
    return _to_out(cfg)


@router.delete("/llm-configs/{config_id}", response_model=dict)
def delete_config(config_id: int, db: Session = Depends(get_db)):
    cfg = db.get(LLMConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="配置不存在")
    db.delete(cfg)
    db.commit()
    return {"message": "配置已删除", "id": config_id}


@router.post("/llm-configs/test", response_model=LLMTestResult)
def test_config(payload: LLMTestRequest, db: Session = Depends(get_db)):
    """Test an LLM config. Accepts either an existing config_id or inline fields."""
    if payload.config_id:
        cfg = db.get(LLMConfig, payload.config_id)
        if not cfg:
            raise HTTPException(status_code=404, detail="配置不存在")
        settings = settings_from_config(cfg)
    else:
        if not (payload.base_url and payload.api_key and payload.model):
            raise HTTPException(status_code=400, detail="测试连接需要 provider/base_url/api_key/model")
        settings = LLMSettings(
            provider=payload.provider or "openai",
            base_url=payload.base_url,
            api_key=payload.api_key,
            model=payload.model,
            endpoint_path=payload.endpoint_path or "/chat/completions",
            temperature=payload.temperature if payload.temperature is not None else 0.2,
            max_tokens=payload.max_tokens or 4096,
            timeout_seconds=payload.timeout_seconds or 60,
            max_retries=payload.max_retries if payload.max_retries is not None else 0,
        )

    result = test_llm_connection(settings)

    # Persist the test outcome if we tested a saved config.
    if payload.config_id:
        cfg = db.get(LLMConfig, payload.config_id)
        if cfg:
            cfg.last_test_ok = result["success"]
            db.commit()

    return LLMTestResult(**result)


def _unset_other_defaults(db: Session, keep_id: int) -> None:
    others = db.query(LLMConfig).filter(LLMConfig.id != keep_id, LLMConfig.is_default.is_(True)).all()
    for o in others:
        o.is_default = False
