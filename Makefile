SHELL := /bin/bash

.PHONY: setup dev backend frontend test lint build dry-run

setup:
	./scripts/bootstrap_env.sh

dev:
	./scripts/dev_local.sh

backend:
	.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev -- --host 127.0.0.1 --port 5173

test:
	.venv/bin/python -m pytest -q backend/tests

lint:
	.venv/bin/python -m ruff check backend
	cd frontend && npm run lint

build:
	cd frontend && npm run build

dry-run:
	.venv/bin/python scripts/e2e_dry_run.py --repo tiangolo/fastapi
