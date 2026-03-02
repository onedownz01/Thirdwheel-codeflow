# CodeFlow

CodeFlow is an intent-anchored debugger: start from what a user tried to do, then inspect the execution chain, replay it backward, and request AI-assisted fixes with full causal context.

## Stack
- Backend: FastAPI, Pydantic v2, Tree-sitter, optional OpenTelemetry + Postgres
- Frontend: React 18, TypeScript, Zustand, React Flow, ELK.js
- Infra: OTel collector + Postgres via Docker Compose

## Repo Layout
- `backend/` API, parsing, tracing, AI fix service
- `frontend/` UI and websocket client
- `infra/` local observability services
- `docs/` architecture and operational docs

## Quick Start

### Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### One-Command Local Run (recommended)
```bash
./scripts/dev_local.sh
```

### Optional Infra (Postgres + OTel Collector)
```bash
cd infra
docker compose up -d
```

## API Surface
- `POST /parse`
- `GET /intents?repo=...`
- `GET /occurrences?repo=...&intent_id=...`
- `POST /trace/start`
- `GET /trace/{session_id}`
- `POST /fix`
- `DELETE /cache/{repo}`
- `GET /telemetry/status`
- `WS /ws/trace/{session_id}`

## Notes
- Lane A simulation is implemented now.
- Lane B OpenTelemetry wiring is active when `OTEL_EXPORTER_OTLP_ENDPOINT` is set.
- AI fix calls are manual and opt-in only.
- Frontend sends W3C `traceparent` headers for trace correlation.

## Frontend Shortcuts
- `Space`: play/pause playback
- `R`: reset active trace
- `F`: fit graph view

## Benchmark Extraction
```bash
python3 scripts/benchmark_extraction.py --repos tiangolo/fastapi expressjs/express
```
