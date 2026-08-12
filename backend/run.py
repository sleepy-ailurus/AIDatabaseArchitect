import os
import socket
import sys
import threading
import webbrowser

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


def _wait_for_server_and_open(port: int) -> None:
    """Block until the local server is reachable, then open the browser."""
    if _wait_for_server(port):
        webbrowser.open(f"http://localhost:{port}")


def _run_server(port: int) -> None:
    """Run the FastAPI/uvicorn server (used in a background thread when packaged)."""
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    port = _find_free_port(8000)

    if getattr(sys, "frozen", False):
        # Packaged build: serve the frontend ourselves and show a native
        # desktop window (pywebview -> Edge WebView2) instead of a browser tab.
        threading.Thread(target=_run_server, args=(port,), daemon=True).start()
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
        # :5173) proxies /api here. Optionally open the API root in a browser.
        threading.Thread(
            target=_wait_for_server_and_open, args=(port,), daemon=True
        ).start()
        uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False)
