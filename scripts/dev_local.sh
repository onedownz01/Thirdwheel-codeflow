#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
MAX_RESTARTS="${MAX_RESTARTS:-3}"

VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-${VENV_DIR}/bin/python}"
PIP_BIN="${PIP_BIN:-${VENV_DIR}/bin/pip}"
LOG_DIR="${ROOT_DIR}/.logs"
mkdir -p "$LOG_DIR"

BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"

BACKEND_RESTARTS=0
FRONTEND_RESTARTS=0

cleanup() {
  if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" || true
  fi
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" || true
  fi
}
trap cleanup EXIT INT TERM

ensure_backend_env() {
  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "[dev_local] creating virtualenv at ${VENV_DIR}"
    python3 -m venv "$VENV_DIR"
  fi

  if ! "$PYTHON_BIN" -c "import fastapi, uvicorn, pydantic" >/dev/null 2>&1; then
    echo "[dev_local] installing backend dependencies"
    "$PIP_BIN" install --upgrade pip
    "$PIP_BIN" install -r backend/requirements.txt
  fi
}

ensure_frontend_env() {
  if [[ ! -d frontend/node_modules ]]; then
    echo "[dev_local] installing frontend dependencies"
    (cd frontend && npm install)
  fi
}

start_backend() {
  echo "[dev_local] backend -> http://${BACKEND_HOST}:${BACKEND_PORT} (log: ${BACKEND_LOG})"
  "$PYTHON_BIN" -m uvicorn backend.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
    >>"$BACKEND_LOG" 2>&1 &
  BACKEND_PID=$!
}

start_frontend() {
  echo "[dev_local] frontend -> http://${FRONTEND_HOST}:${FRONTEND_PORT} (log: ${FRONTEND_LOG})"
  (
    cd frontend
    npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
  ) >>"$FRONTEND_LOG" 2>&1 &
  FRONTEND_PID=$!
}

ensure_backend_env
ensure_frontend_env

: >"$BACKEND_LOG"
: >"$FRONTEND_LOG"
start_backend
start_frontend

echo "[dev_local] backend pid=${BACKEND_PID}, frontend pid=${FRONTEND_PID}"
echo "[dev_local] press Ctrl+C to stop"

while true; do
  sleep 2

  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    BACKEND_RESTARTS=$((BACKEND_RESTARTS + 1))
    if (( BACKEND_RESTARTS > MAX_RESTARTS )); then
      echo "[dev_local] backend exceeded restart limit (${MAX_RESTARTS})."
      echo "[dev_local] tail backend log:"
      tail -n 40 "$BACKEND_LOG" || true
      exit 1
    fi
    echo "[dev_local] backend exited; restarting (${BACKEND_RESTARTS}/${MAX_RESTARTS})"
    start_backend
  fi

  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    FRONTEND_RESTARTS=$((FRONTEND_RESTARTS + 1))
    if (( FRONTEND_RESTARTS > MAX_RESTARTS )); then
      echo "[dev_local] frontend exceeded restart limit (${MAX_RESTARTS})."
      echo "[dev_local] tail frontend log:"
      tail -n 40 "$FRONTEND_LOG" || true
      exit 1
    fi
    echo "[dev_local] frontend exited; restarting (${FRONTEND_RESTARTS}/${MAX_RESTARTS})"
    start_frontend
  fi
done
