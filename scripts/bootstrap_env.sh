#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d .venv ]]; then
  echo "[bootstrap] creating .venv"
  python3 -m venv .venv
fi

echo "[bootstrap] installing backend dependencies"
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r backend/requirements.txt -r backend/requirements-dev.txt

echo "[bootstrap] installing frontend dependencies"
(cd frontend && npm install)

echo "[bootstrap] done"
