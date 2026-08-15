"""Standalone MCP stdio launcher (cwd-independent).

Use this file when registering the MCP server with Claude Code / Cursor so the
command does not depend on the working directory:

  claude mcp add ai-database-architect -- <venv-python> <path-to>/mcp_stdio.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.mcp_server import run_stdio  # noqa: E402


if __name__ == "__main__":
    run_stdio()
