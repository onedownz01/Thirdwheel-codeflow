"""
backend/tracer/process_runner.py

Launches the user's Python process with the CodeFlow tracer injected.

Usage (called by /trace/start with mode=live):
    runner = ProcessRunner(project_root, repo_key, ingest_ws_url)
    pid = await runner.start(["python", "-m", "uvicorn", "main:app"], session_id)
    await runner.stop()

Injection strategy: run_with_tracer.py wrapper
  ProcessRunner rewrites the user's command so that run_with_tracer.py runs
  first.  That script imports tracer_entrypoint (installing sys.settrace),
  then hands control to the original module or script via runpy.

  Example rewrites:
    ["python", "-m", "uvicorn", "main:app"]  →  ["python", WRAPPER, "uvicorn", "main:app"]
    ["python", "app.py", "--port", "8000"]   →  ["python", WRAPPER, "app.py", "--port", "8000"]
    ["python3", "-m", "flask", "run"]        →  ["python3", WRAPPER, "flask", "run"]
    ["uvicorn", "main:app"]                  →  unchanged (non-python executable)

Why not PYTHONSTARTUP?
  PYTHONSTARTUP only fires in interactive mode (the Python REPL).
  It does NOT run for `python -m module` or `python script.py`.
"""
from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path


# Directory containing python_sys_tracer.py, tracer_entrypoint.py, run_with_tracer.py
_TRACER_DIR = str(Path(__file__).parent.resolve())
_WRAPPER = str(Path(_TRACER_DIR) / "run_with_tracer.py")


class ProcessRunner:
    """
    Manages a single traced subprocess.
    One instance per /trace/start (live mode) call.
    """

    def __init__(
        self,
        project_root: str,
        repo_key: str,
        ingest_ws_url: str = "ws://127.0.0.1:8000/ws/tracer/ingest",
    ) -> None:
        self.project_root = str(Path(project_root).resolve())
        self.repo_key = repo_key
        self.ingest_ws_url = ingest_ws_url
        self._process: asyncio.subprocess.Process | None = None
        self._session_id: str = ""

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process else None

    @property
    def is_running(self) -> bool:
        if not self._process:
            return False
        return self._process.returncode is None

    async def start(self, command: list[str], session_id: str) -> int:
        """
        Launch `command` with the tracer injected.
        Returns the PID of the launched process.
        Raises RuntimeError if already running.
        """
        if self.is_running:
            raise RuntimeError(f"Process already running (pid={self.pid})")

        self._session_id = session_id
        env = self._build_env(session_id)
        wrapped = self._transform_command(command)

        self._process = await asyncio.create_subprocess_exec(
            *wrapped,
            env=env,
            cwd=self.project_root,
            # Forward stdout/stderr to the CodeFlow backend's own streams
            # so the user can see their app's output in their terminal.
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        return self._process.pid

    async def stop(self) -> None:
        """Gracefully stop the traced process (SIGTERM, then SIGKILL after 5s)."""
        if not self._process or not self.is_running:
            return
        try:
            self._process.send_signal(signal.SIGTERM)
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
        except ProcessLookupError:
            pass  # already exited

    async def wait(self) -> int:
        """Wait for process to exit and return its exit code."""
        if not self._process:
            return -1
        return await self._process.wait()

    def update_session(self, session_id: str) -> None:
        """Update our record of the current session ID."""
        self._session_id = session_id

    # ── Internals ─────────────────────────────────────────────────────────────

    def _transform_command(self, command: list[str]) -> list[str]:
        """
        Rewrite the user's command to inject the tracer wrapper.

        For Python commands, inserts run_with_tracer.py after the Python
        executable and drops the '-m' flag (run_with_tracer handles it via runpy).

        For non-Python executables (uvicorn, gunicorn directly), returns unchanged
        — tracer injection is not possible without knowing they're Python.
        """
        if not command:
            return command

        executable = command[0]
        exe_lower = Path(executable).name.lower()

        # Only rewrite python / python3 / python3.x invocations
        if "python" not in exe_lower:
            return command

        rest = command[1:]

        # Drop leading '-m' flag — run_with_tracer uses runpy.run_module instead
        if rest and rest[0] == "-m":
            rest = rest[1:]

        return [executable, _WRAPPER] + rest

    def _build_env(self, session_id: str) -> dict[str, str]:
        """
        Build the environment for the child process.
        Inherits the current environment, then overrides CodeFlow-specific vars.
        """
        env = os.environ.copy()

        # Tell the tracer where the project is
        env["CODEFLOW_PROJECT_ROOT"] = self.project_root

        # Tell the tracer where to send events
        env["CODEFLOW_INGEST_WS"] = self.ingest_ws_url

        # Initial session ID
        env["CODEFLOW_SESSION_ID"] = session_id

        # Ensure the tracer modules are importable in the child process
        existing_path = env.get("PYTHONPATH", "")
        if existing_path:
            env["PYTHONPATH"] = f"{_TRACER_DIR}{os.pathsep}{existing_path}"
        else:
            env["PYTHONPATH"] = _TRACER_DIR

        return env
