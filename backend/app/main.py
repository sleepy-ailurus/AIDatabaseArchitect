"""FastAPI application entrypoint.

Registers all routers, configures CORS (allowing the Vite dev server), creates
the SQLite platform database on startup, and exposes a health check.
"""
from __future__ import annotations

import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.config import BASE_DIR, settings
from app.database import init_db
from app.routers import (
    analysis,
    connections,
    er_models,
    exports,
    llm_configs,
    projects,
    relationships,
    schema,
    user_settings,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-database-architect")

app = FastAPI(
    title="AI Database Architect API",
    description="Intelligent database schema understanding & ER modeling platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("Platform database initialized at %s", settings.database_url)


@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "service": "ai-database-architect"}


# Register routers.
app.include_router(projects.router)
app.include_router(connections.router)
app.include_router(schema.router)
app.include_router(relationships.router)
app.include_router(er_models.router)
app.include_router(llm_configs.router)
app.include_router(exports.router)
app.include_router(analysis.router)
app.include_router(user_settings.router)


# ---------------------------------------------------------------------------
# Optional: serve the built frontend SPA from the same origin.
# Only active when SERVE_FRONTEND is set (used by the packaged desktop build),
# so the normal Vite dev / API-only workflow is unaffected.
# ---------------------------------------------------------------------------
_FRONTEND_DIST = None
if os.environ.get("SERVE_FRONTEND"):
    if getattr(sys, "frozen", False):
        _FRONTEND_DIST = os.path.join(sys._MEIPASS, "frontend_dist")
    else:
        _FRONTEND_DIST = os.path.join(BASE_DIR.parent, "frontend", "dist")

if _FRONTEND_DIST and os.path.isdir(_FRONTEND_DIST):

    @app.get("/{full_path:path}")
    async def _serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        candidate = os.path.join(_FRONTEND_DIST, full_path)
        if os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))
