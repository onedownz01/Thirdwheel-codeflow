"""
backend/tracer/tracer_entrypoint.py

Injected into the user's Python process via:
    python -c "import tracer_entrypoint" -m uvicorn main:app
  or via PYTHONSTARTUP / sitecustomize.py

Reads config from environment variables set by process_runner.py,
initialises python_sys_tracer, then hands control back to the user's code.

MUST be completely self-contained — no CodeFlow backend imports.
The user's process does not have backend/ on sys.path.
"""
from __future__ import annotations

import os
import sys


def _bootstrap() -> None:
    project_root = os.environ.get("CODEFLOW_PROJECT_ROOT", "")
    ingest_ws = os.environ.get("CODEFLOW_INGEST_WS", "ws://127.0.0.1:8765/ws/tracer/ingest")
    session_id = os.environ.get("CODEFLOW_SESSION_ID", "")

    if not project_root:
        # Not being run under CodeFlow — do nothing, don't disrupt the app
        return

    # Find the tracer module. process_runner.py puts its directory on PYTHONPATH.
    try:
        import python_sys_tracer as tracer  # type: ignore
    except ImportError:
        # Tracer module not found on path — abort silently
        return

    try:
        tracer.initialize(
            project_root=project_root,
            ingest_ws=ingest_ws,
            session_id=session_id,
        )
    except Exception:
        # Never crash the user's app because of CodeFlow
        return


_bootstrap()
