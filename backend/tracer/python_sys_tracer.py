"""
backend/tracer/python_sys_tracer.py

The real-data camera system for CodeFlow.

Runs INSIDE the user's process (injected before first line of user code).
Captures every function call and return in project files.
Sends raw events to CodeFlow backend via local WebSocket.

NEVER raises an exception that could crash the user's app.
Every try/except is intentional and load-bearing.
"""

from __future__ import annotations

import os
import sys
import time
import json
import threading
import asyncio
import websockets  # pip install websockets
from pathlib import Path
from typing import Optional


# ─── Configuration (injected via environment variables) ───────────────────────

# Absolute path to the user's project root. Only files under this path are traced.
# e.g. /home/user/myapp
PROJECT_ROOT: str = os.environ.get("CODEFLOW_PROJECT_ROOT", "")

# WebSocket URL of the CodeFlow backend ingest endpoint
# e.g. ws://127.0.0.1:8765/ws/tracer/ingest
INGEST_WS_URL: str = os.environ.get(
    "CODEFLOW_INGEST_WS", "ws://127.0.0.1:8765/ws/tracer/ingest"
)

# Session ID assigned by backend when user clicks an intent in the UI
SESSION_ID: str = os.environ.get("CODEFLOW_SESSION_ID", "")

# ─── Internal state ───────────────────────────────────────────────────────────

# Thread-safe event queue: tracer (any thread) → sender thread
_event_queue: list[dict] = []
_queue_lock = threading.Lock()

# Sequence counter — monotonically increasing across all events in this session
_sequence = 0
_seq_lock = threading.Lock()

# Normalized absolute path of the project root, with a trailing separator.
# e.g. "/home/user/myapp/"  — the trailing sep prevents matching sibling dirs
# and makes component-level exclusion unambiguous.
_project_root_norm: str = ""

# First-level subdirectory names that are NEVER project source — always excluded.
# Covers virtualenvs (wherever they live inside the project root) and tooling dirs.
_EXCLUDED_FIRST_COMPONENTS: frozenset[str] = frozenset({
    ".venv", "venv", "env", ".env",          # virtual environments
    "node_modules",                            # JS deps (may co-exist in monorepos)
    ".tox", ".nox",                            # test environments
    ".git", ".hg", ".svn",                     # VCS internals
    "__pypackages__",                          # PEP 582
    "build", "dist", ".eggs", "*.egg-info",    # build artefacts
})

# Call stack depth per thread (for parent/child span tracking)
_call_stack: threading.local = threading.local()


# ─── Startup ──────────────────────────────────────────────────────────────────

def initialize(project_root: str, ingest_ws: str, session_id: str) -> None:
    """
    Call this once before installing the sys.settrace hook.
    Sets up global state and starts the background WS sender thread.
    """
    global PROJECT_ROOT, INGEST_WS_URL, SESSION_ID, _project_root_norm

    PROJECT_ROOT = project_root
    INGEST_WS_URL = ingest_ws
    SESSION_ID = session_id

    if not PROJECT_ROOT:
        raise ValueError("CODEFLOW_PROJECT_ROOT must be set")

    # Trailing separator guarantees that "/project/app" doesn't accidentally
    # match "/project/app-extra/" (prefix collision) and makes the
    # first-component exclusion split unambiguous.
    _project_root_norm = str(Path(PROJECT_ROOT).resolve()).rstrip("/\\") + os.sep

    # Start background thread that drains the queue and sends to backend
    sender = threading.Thread(
        target=_sender_thread_main,
        name="codeflow-sender",
        daemon=True,  # dies when user's app exits — does not block shutdown
    )
    sender.start()

    # Install the trace hook on the main thread
    sys.settrace(_trace_hook)

    # Also patch threading.Thread to install trace hook in new threads
    _patch_threading()


# ─── Core trace hook ─────────────────────────────────────────────────────────

def _trace_hook(frame, event: str, arg) -> Optional[callable]:
    """
    Called by CPython on every function call, return, and exception.
    Must be FAST and NEVER raise.

    frame  — the current execution frame
    event  — 'call' | 'return' | 'exception' | 'line' (we ignore 'line')
    arg    — None for 'call', return value for 'return', exc_info for 'exception'
    """
    # Fast-path: skip everything except call/return/exception
    if event == "line":
        return _trace_hook

    try:
        # Fast-path: skip synthetic Python frames that are never useful and
        # would always appear as live:: noise (no matching parsed function).
        # co_name examples: "<module>", "<listcomp>", "<dictcomp>", "<genexpr>",
        # "<lambda>" (lambdas are skipped too — they have no stable identity).
        co_name = frame.f_code.co_name
        if co_name.startswith("<"):
            return None

        # Fast-path: check if this file is inside the project
        filename = frame.f_code.co_filename
        if not _is_project_file(filename):
            return None  # returning None = stop tracing this frame (huge perf win)

        if event == "call":
            _handle_call(frame)
        elif event == "return":
            _handle_return(frame, arg)
        elif event == "exception":
            _handle_exception(frame, arg)

    except Exception:
        # Tracer MUST NOT crash the app under any circumstances.
        # Silently swallow all errors here.
        pass

    return _trace_hook  # always return self to keep tracing this frame


def _is_project_file(filename: str) -> bool:
    """
    Returns True only for files that are genuine project source files —
    i.e. inside the project root AND not inside a virtualenv / tooling dir.

    This is the #1 performance gate — must be as fast as possible.

    Correctness notes:
    * _project_root_norm has a trailing separator, so startswith() is a true
      path-prefix check (no accidental matches on sibling dirs).
    * We exclude the first path component after the root to drop .venv/,
      venv/, node_modules/ etc. that may live inside the project tree.
    * We also exclude any path containing "site-packages" or "dist-packages"
      as a belt-and-suspenders guard for non-standard venv layouts.
    """
    if not filename:
        return False
    if filename.startswith("<"):  # <string>, <stdin>, <frozen importlib...>
        return False
    try:
        resolved = str(Path(filename).resolve())

        # Must be inside the project root (trailing-sep guarantees prefix safety)
        if not resolved.startswith(_project_root_norm):
            return False

        # Belt-and-suspenders: reject any path that contains site-packages
        # regardless of where they live (handles non-standard venv layouts).
        if "site-packages" in resolved or "dist-packages" in resolved:
            return False

        # Exclude first-level subdirectories that are never project source.
        # e.g. _project_root_norm = "/proj/"  resolved = "/proj/.venv/lib/h11.py"
        #      rel = ".venv/lib/h11.py"  first_component = ".venv"  → excluded
        rel = resolved[len(_project_root_norm):]
        first_component = rel.split("/")[0].split("\\")[0]
        if first_component in _EXCLUDED_FIRST_COMPONENTS:
            return False

        return True
    except Exception:
        return False


# ─── Call handler ─────────────────────────────────────────────────────────────

def _handle_call(frame) -> None:
    """Fires at the START of a function call. Captures arguments."""
    fn_name = frame.f_code.co_name
    filename = frame.f_code.co_filename
    line = frame.f_code.co_firstlineno
    ts = _now_ms()

    # Extract only the declared parameters (not all locals).
    # co_varnames lists ALL locals; first co_argcount entries are params.
    # co_posonlyargcount and co_kwonlyargcount handle keyword-only params.
    code = frame.f_code
    n_pos = code.co_argcount  # includes 'self', 'cls'
    n_kw = code.co_kwonlyargcount
    param_names = code.co_varnames[: n_pos + n_kw]

    inputs = []
    for name in param_names:
        raw_val = frame.f_locals.get(name)
        rv = _safe_runtime_value(name, raw_val)
        inputs.append(rv)

    # Push to call stack (for duration tracking on return)
    stack = _get_call_stack()
    span_id = _make_span_id()
    parent_span_id = stack[-1]["span_id"] if stack else None
    stack.append(
        {
            "span_id": span_id,
            "fn_name": fn_name,
            "file": filename,
            "line": line,
            "start_ms": ts,
        }
    )

    event = {
        "event_type": "call",
        "fn_name": fn_name,
        "file": filename,
        "line": line,
        "timestamp_ms": ts,
        "inputs": inputs,
        "outputs": [],
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "session_id": SESSION_ID,
        "sequence": _next_seq(),
    }
    _enqueue(event)


# ─── Return handler ───────────────────────────────────────────────────────────

def _handle_return(frame, return_value) -> None:
    """Fires when a function returns. Captures return value and duration."""
    fn_name = frame.f_code.co_name
    filename = frame.f_code.co_filename
    line = frame.f_code.co_firstlineno
    ts = _now_ms()

    stack = _get_call_stack()
    duration_ms = None
    span_id = _make_span_id()
    parent_span_id = None

    # Pop the matching frame from call stack
    if stack and stack[-1]["fn_name"] == fn_name:
        frame_info = stack.pop()
        duration_ms = ts - frame_info["start_ms"]
        span_id = frame_info["span_id"]
        parent_span_id = stack[-1]["span_id"] if stack else None

    # IMPORTANT: For async functions and generators, 'return' fires multiple times.
    # A return value of None mid-generator is a yield, not the final return.
    # We emit all return events; the correlator/frontend handles dedup.
    rv = _safe_runtime_value("return", return_value)

    event = {
        "event_type": "return",
        "fn_name": fn_name,
        "file": filename,
        "line": line,
        "timestamp_ms": ts,
        "inputs": [],
        "outputs": [rv],
        "duration_ms": duration_ms,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "session_id": SESSION_ID,
        "sequence": _next_seq(),
    }
    _enqueue(event)


# ─── Exception handler ────────────────────────────────────────────────────────

def _handle_exception(frame, exc_info) -> None:
    """Fires when an exception propagates through a frame."""
    fn_name = frame.f_code.co_name
    filename = frame.f_code.co_filename
    line = frame.f_lineno  # current line (where exception occurred, not fn start)
    ts = _now_ms()

    exc_type, exc_value, _ = exc_info
    error_type = exc_type.__name__ if exc_type else "UnknownError"

    try:
        error_msg = str(exc_value)
    except Exception:
        error_msg = "<unserializable exception>"

    event = {
        "event_type": "error",
        "fn_name": fn_name,
        "file": filename,
        "line": line,
        "timestamp_ms": ts,
        "inputs": [],
        "outputs": [],
        "error": error_msg,
        "error_type": error_type,
        "error_line": line,
        "span_id": _make_span_id(),
        "parent_span_id": None,
        "session_id": SESSION_ID,
        "sequence": _next_seq(),
    }
    _enqueue(event)


# ─── Safe value serialization ─────────────────────────────────────────────────

# Sensitive key fragments — mirrors value_sanitizer.py's SENSITIVE_TOKENS
_SENSITIVE_TOKENS = {
    "password", "passwd", "secret", "token", "api_key", "key",
    "auth", "credential", "credit_card", "ssn", "pin", "cvv", "cookie",
}

_MAX_STR_LEN = 160
_MAX_LIST_LEN = 6
_MAX_DICT_KEYS = 8


def _safe_runtime_value(name: str, value) -> dict:
    """
    Converts a raw Python value into a RuntimeValue dict.
    Matches the schema.RuntimeValue shape exactly.
    Mirrors value_sanitizer.sanitize_value() logic — but works without importing it,
    because the tracer runs in the user's process which may not have CodeFlow on sys.path.

    NOTE: If CodeFlow IS on the path, prefer importing value_sanitizer directly.
    This is a self-contained fallback.

    MUST NEVER raise.
    """
    try:
        lowered = name.lower()
        is_sensitive = any(tok in lowered for tok in _SENSITIVE_TOKENS)

        if is_sensitive:
            return {
                "name": name,
                "value": "••••••",
                "type_name": _safe_type_name(value),
                "is_sensitive": True,
            }

        return {
            "name": name,
            "value": _serialize(value),
            "type_name": _safe_type_name(value),
            "is_sensitive": False,
        }
    except Exception:
        return {"name": name, "value": "<capture error>", "type_name": "unknown", "is_sensitive": False}


def _safe_type_name(value) -> str:
    try:
        return type(value).__name__
    except Exception:
        return "unknown"


def _serialize(value):
    """
    Recursively serializes a value to a JSON-safe primitive.
    Truncates strings, lists, and dicts to avoid huge payloads.
    Falls back to type name string on anything unserializable.
    """
    try:
        if value is None or isinstance(value, (bool, int, float)):
            return value

        if isinstance(value, str):
            return value[:_MAX_STR_LEN] + ("…" if len(value) > _MAX_STR_LEN else "")

        if isinstance(value, (list, tuple)):
            truncated = value[:_MAX_LIST_LEN]
            serialized = [_serialize(item) for item in truncated]
            if len(value) > _MAX_LIST_LEN:
                serialized.append(f"… +{len(value) - _MAX_LIST_LEN} more")
            return serialized

        if isinstance(value, dict):
            keys = list(value.keys())[:_MAX_DICT_KEYS]
            result = {str(k): _serialize(value[k]) for k in keys}
            if len(value) > _MAX_DICT_KEYS:
                result["…"] = f"+{len(value) - _MAX_DICT_KEYS} more keys"
            return result

        if isinstance(value, bytes):
            return f"<bytes len={len(value)}>"

        # For all other objects: try repr, fall back to type name
        try:
            r = repr(value)
            return r[:_MAX_STR_LEN] + ("…" if len(r) > _MAX_STR_LEN else "")
        except Exception:
            return f"<{_safe_type_name(value)}>"

    except Exception:
        return "<serialize error>"


# ─── Queue + sender thread ────────────────────────────────────────────────────

def _enqueue(event: dict) -> None:
    with _queue_lock:
        _event_queue.append(event)


def _drain_queue() -> list[dict]:
    with _queue_lock:
        if not _event_queue:
            return []
        events = _event_queue.copy()
        _event_queue.clear()
        return events


def _sender_thread_main() -> None:
    """
    Background daemon thread.
    Drains the event queue every 50ms and sends batches to the backend via WS.
    Uses asyncio in its own loop — isolated from user's event loop.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_sender_loop())


async def _sender_loop() -> None:
    """
    Maintains a persistent WebSocket connection to the backend ingest endpoint.
    Reconnects with backoff on disconnect.
    """
    backoff = 1.0
    while True:
        try:
            async with websockets.connect(INGEST_WS_URL, ping_interval=20) as ws:
                backoff = 1.0  # reset on successful connect
                while True:
                    await asyncio.sleep(0.05)  # 50ms drain interval
                    events = _drain_queue()
                    if not events:
                        continue
                    payload = json.dumps({"session_id": SESSION_ID, "events": events})
                    await ws.send(payload)
        except Exception:
            # Connection failed or dropped — retry with backoff
            await asyncio.sleep(min(backoff, 30.0))
            backoff *= 2.0


# ─── Thread instrumentation ───────────────────────────────────────────────────

def _patch_threading() -> None:
    """
    Monkey-patches threading.Thread to install our trace hook in new threads.
    Without this, threads spawned by the user's app (e.g. uvicorn worker threads)
    would not be traced.
    """
    original_bootstrap = threading.Thread._bootstrap_inner  # type: ignore

    def patched_bootstrap(self):
        sys.settrace(_trace_hook)
        original_bootstrap(self)

    threading.Thread._bootstrap_inner = patched_bootstrap  # type: ignore


# ─── Utilities ────────────────────────────────────────────────────────────────

def _now_ms() -> float:
    return time.monotonic() * 1000.0


def _next_seq() -> int:
    global _sequence
    with _seq_lock:
        _sequence += 1
        return _sequence


_span_counter = 0
_span_lock = threading.Lock()


def _make_span_id() -> str:
    global _span_counter
    with _span_lock:
        _span_counter += 1
        return f"{SESSION_ID[:8]}-{_span_counter:06d}"


def _get_call_stack() -> list[dict]:
    """Per-thread call stack stored in thread-local storage."""
    if not hasattr(_call_stack, "stack"):
        _call_stack.stack = []
    return _call_stack.stack


# ─── Entry point (used when injected as a script) ────────────────────────────

if __name__ == "__main__":
    # This file can be run as a bootstrap script:
    # python -c "import python_sys_tracer; python_sys_tracer.initialize(...)"
    # Actual invocation is handled by tracer_entrypoint.py
    pass
