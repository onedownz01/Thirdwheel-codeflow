"""
backend/tracer/run_with_tracer.py

Bootstrap wrapper — injects the CodeFlow tracer before running the user's app.

ProcessRunner._transform_command() rewrites the user's command to call this
script instead of invoking python directly.  This file then:
  1. Imports tracer_entrypoint (which calls initialize() and installs sys.settrace)
  2. Hands control to the original module or script via runpy

Why not PYTHONSTARTUP?
  PYTHONSTARTUP only fires in interactive mode (the Python REPL).
  It does NOT run for `python -m module` or `python script.py` — the two
  most common ways to start a server.  This wrapper solves that.

Usage (never called directly — ProcessRunner builds the command):
    python run_with_tracer.py uvicorn main:app --reload
    python run_with_tracer.py app.py --port 8080
"""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

# ─── Bootstrap tracer ────────────────────────────────────────────────────────
# The tracer directory is on PYTHONPATH (set by ProcessRunner._build_env),
# so tracer_entrypoint is importable.  Importing it calls _bootstrap() which
# reads CODEFLOW_* env vars and installs sys.settrace.
try:
    import tracer_entrypoint  # noqa: F401 — side-effect only
except Exception:
    pass  # never crash the user's app because of CodeFlow

# ─── Run the original command ─────────────────────────────────────────────────
# sys.argv[0] is this script; sys.argv[1] is the module name or script path;
# sys.argv[2:] are the original arguments.

if len(sys.argv) < 2:
    sys.exit("run_with_tracer: no module or script specified")

target = sys.argv[1]
sys.argv = sys.argv[1:]  # shift: user code sees itself as argv[0]

if Path(target).exists():
    # Script mode: python run_with_tracer.py app.py [args...]
    runpy.run_path(target, run_name="__main__")
else:
    # Module mode: python run_with_tracer.py uvicorn main:app [args...]
    runpy.run_module(target, run_name="__main__", alter_sys=True)
