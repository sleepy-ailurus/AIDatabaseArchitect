"""Application configuration loaded from environment / .env."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


def _default_database_url() -> str:
    """Default SQLite location.

    When running as a packaged executable the program directory is read-only,
    so we fall back to a writable user-data directory under %APPDATA%.
    """
    if getattr(sys, "frozen", False):
        data_dir = Path(os.environ.get("APPDATA", str(Path.home()))) / "AIDatabaseArchitect"
        data_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{data_dir / 'app.db'}"
    return f"sqlite:///{BASE_DIR / 'app.db'}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Platform SQLite database (writable user-data dir when packaged).
    database_url: str = _default_database_url()

    # Secret key used to derive the Fernet key for credential encryption.
    # In production this should be provided via the environment.
    secret_key: str = "ai-database-architect-default-secret-key-change-me"

    # CORS origins allowed to call the API.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:8000",
    ]

    # Optional static Bearer token for the MCP HTTP endpoint.
    # Empty (default) disables authentication; when set, every MCP HTTP
    # request must carry `Authorization: Bearer <token>`.
    mcp_auth_token: str = ""

    # High / medium confidence thresholds for AI suggestions.
    confidence_high_threshold: float = 0.85
    confidence_medium_threshold: float = 0.60


settings = Settings()


def get_fernet_key() -> bytes:
    """Derive a stable 32-byte url-safe key from the configured secret."""
    import hashlib
    from base64 import urlsafe_b64encode

    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return urlsafe_b64encode(digest)
