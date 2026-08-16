import os
import socket
import sys
import threading

# When packaged as a Windows GUI app (--noconsole), stdout/stderr are None.
# Uvicorn's default formatter calls stream.isatty(), so provide a fallback.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# In a packaged build, serve the frontend from the backend itself.
# Must be set BEFORE app.main is imported, because main.py reads it at load time.
if getattr(sys, "frozen", False):
    os.environ.setdefault("SERVE_FRONTEND", "1")

import uvicorn

from app.config import settings
from app.main import app


def _find_free_port(start: int = 8000, max_tries: int = 50) -> int:
    """Return the first free localhost TCP port at or after `start`."""
    for port in range(start, start + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start


def _wait_for_server(port: int, timeout: float = 30.0) -> bool:
    """Block until the local server is reachable. Returns True on success."""
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.3)
    return False


def _run_server(port: int) -> None:
    """Run the FastAPI/uvicorn server (used in a background thread when packaged)."""
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False)


def _run_mcp_http(port: int = 8001) -> None:
    """Run the MCP server over Streamable HTTP on a dedicated localhost port."""
    import asyncio

    import uvicorn

    from app.services.mcp_server import BearerAuthMiddleware, server

    async def serve() -> None:
        starlette_app = server.streamable_http_app(
            streamable_http_path="/mcp",
            host="127.0.0.1",
        )
        token = (settings.mcp_auth_token or "").strip()
        if token:
            starlette_app = BearerAuthMiddleware(starlette_app, token)
        config = uvicorn.Config(starlette_app, host="127.0.0.1", port=port, log_level="info")
        await uvicorn.Server(config).serve()

    asyncio.run(serve())


if __name__ == "__main__":
    # MCP stdio mode: `python run.py --mcp` starts a local MCP server for
    # Cursor / Claude Code / Codex etc.
    if "--mcp" in sys.argv:
        from app.services.mcp_server import run_stdio

        run_stdio()
        sys.exit(0)

    port = _find_free_port(8000)
    mcp_port = _find_free_port(port + 1)

    if getattr(sys, "frozen", False):
        # Packaged build: serve the frontend ourselves and show a native
        # desktop window (pywebview -> Edge WebView2) instead of a browser tab.
        threading.Thread(target=_run_server, args=(port,), daemon=True).start()
        threading.Thread(target=_run_mcp_http, args=(mcp_port,), daemon=True).start()
        import webview

        if _wait_for_server(port):
            webview.create_window(
                "AIDatabaseArchitect",
                f"http://127.0.0.1:{port}/",
                width=1440,
                height=900,
            )
            webview.start()
    else:
        # Development: just run the API server; the Vue dev server (Vite on
        # :5173) proxies /api here. Do not open a browser automatically.
        threading.Thread(target=_run_mcp_http, args=(mcp_port,), daemon=True).start()
        uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False)
