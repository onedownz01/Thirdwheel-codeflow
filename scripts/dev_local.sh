#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

cleanup() {
  if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" || true
  fi
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" || true
  fi
}
trap cleanup EXIT INT TERM

echo "[dev_local] starting backend on http://${BACKEND_HOST}:${BACKEND_PORT}"
python3 -m uvicorn backend.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
BACKEND_PID=$!

echo "[dev_local] starting frontend on http://${FRONTEND_HOST}:${FRONTEND_PORT}"
(
  cd frontend
  npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

echo "[dev_local] backend pid=${BACKEND_PID}, frontend pid=${FRONTEND_PID}"
echo "[dev_local] press Ctrl+C to stop both"

wait -n "$BACKEND_PID" "$FRONTEND_PID"
exit 1
