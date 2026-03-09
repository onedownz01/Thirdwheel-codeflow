"""
backend/tracer/process_runner.py

Launches the user's Python process with the CodeFlow tracer injected.

Usage (called by /runner/start endpoint):
    runner = ProcessRunner(project_root, repo_key, ingest_ws_url)
    pid = await runner.start(["python", "-m", "uvicorn", "main:app"], session_id)
    await runner.stop()

The tracer is injected via PYTHONSTARTUP — Python runs that file before
executing any user code, including -m and script targets.

Why PYTHONSTARTUP and not PYTHONPATH + sitecustomize?
  - PYTHONSTARTUP is cleaner: only runs once, in interactive+script mode
  - sitecustomize affects every subprocess the user's app spawns (e.g. celery workers)
    which could be desirable later but is too broad for v1
  - We also add our tracer dir to PYTHONPATH so the import resolves
"""
from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path


# Directory containing python_sys_tracer.py and tracer_entrypoint.py
_TRACER_DIR = str(Path(__file__).parent.resolve())


class ProcessRunner:
    """
    Manages a single traced subprocess.
    One instance per /runner/start call.
    """

    def __init__(
        self,
        project_root: str,
        repo_key: str,
        ingest_ws_url: str = "ws://127.0.0.1:8765/ws/tracer/ingest",
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

        self._process = await asyncio.create_subprocess_exec(
            *command,
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
        """
        Update the session ID for the next intent window.
        The tracer reads SESSION_ID from its env at startup — for a running
        process this must be signalled differently (see capture window control).
        This method updates our record; the actual signal goes via the ingest WS.
        """
        self._session_id = session_id

    # ── Internals ─────────────────────────────────────────────────────────────

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

        # Initial session ID (can be updated via capture window signals)
        env["CODEFLOW_SESSION_ID"] = session_id

        # PYTHONSTARTUP: Python runs this file before user code in script/module mode
        entrypoint = str(Path(_TRACER_DIR) / "tracer_entrypoint.py")
        env["PYTHONSTARTUP"] = entrypoint

        # Ensure the tracer module (python_sys_tracer.py) is importable
        existing_path = env.get("PYTHONPATH", "")
        if existing_path:
            env["PYTHONPATH"] = f"{_TRACER_DIR}{os.pathsep}{existing_path}"
        else:
            env["PYTHONPATH"] = _TRACER_DIR

        return env
