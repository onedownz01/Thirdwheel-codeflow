# CodeFlow

**See what your code does. Not just what it says.**

CodeFlow is an intent-anchored execution tracer. Paste any GitHub URL — it surfaces every user-facing action in the codebase, then lets you trace the full call chain for each one: which functions ran, in what order, with what inputs and outputs. Zero setup. No instrumentation required.

---

## The Problem

AI-generated code ships fast. Models made it safer. Nobody made it *visible*.

When a user clicks a button, you have no idea what functions that action touches, what data moves through them, or what comes back at each step. Logs show you what happened after the fact. CodeFlow shows you the full execution path — before, during, or without running anything at all.

---

## How It Works

```
GitHub URL → parse → intent graph → click intent → trace → call chain with I/O
```

CodeFlow reads the repository, extracts every user-facing action (buttons, forms, API routes, CLI commands), builds a static call graph, and maps each action to its execution path. Click an intent and watch the canvas zoom to the exact function chain — with file paths, line numbers, and input/output on every block.

---

## Three Modes

| Mode | What it does | Requirement |
|------|-------------|-------------|
| **Sim** | Walks the static call graph, generates a synthetic trace | Any public GitHub URL |
| **OTel** | Receives real spans from your running service | OTel SDK pointed at CodeFlow |
| **Live** | Attaches a tracer to a local process, captures real I/O | Local repo + run command |

---

## Quick Start

**Prerequisites:** Python 3.11+, Node 18+

### One command (recommended)
```bash
./scripts/dev_local.sh
```

### Manual

```bash
# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, paste a GitHub repo (e.g. `tiangolo/fastapi`), hit **Parse**.

### First-time bootstrap
```bash
./scripts/bootstrap_env.sh
```

### Optional: Postgres + OTel Collector
```bash
cd infra && docker compose up -d
```

---

## Environment Variables

All optional. CodeFlow works without any of these in Sim mode.

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Enables AI fix suggestions (opt-in, never called automatically) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTel collector endpoint for real span ingestion |
| `DATABASE_URL` | Postgres connection string for trace persistence |
| `GITHUB_TOKEN` | GitHub PAT for higher API rate limits on large repos |

Create a `.env` file in the project root (gitignored):
```bash
GITHUB_TOKEN=ghp_...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, Pydantic v2, Tree-sitter, NetworkX |
| Frontend | React 18, TypeScript, Zustand, React Flow, ELK.js |
| Tracing | OpenTelemetry, Python sys.settrace |
| Infra (optional) | OTel Collector, Postgres, Docker Compose |

---

## API Reference

```
GET  /intents?repo={owner/repo}          List all detected intents
GET  /occurrences?repo=...&intent_id=... Get call chain for an intent
POST /trace/start                        Start a trace session
POST /trace/ingest                       Ingest OTel spans
GET  /trace/{session_id}                 Fetch trace events
POST /fix                                Request AI fix suggestion (opt-in)
DELETE /cache/{repo}                     Clear cached parse for a repo
GET  /telemetry/status                   OTel connection status
WS   /ws/trace/{session_id}             Live trace event stream
```

---

## Repo Layout

```
backend/
  main.py              FastAPI app + routes
  parser/              GitHub fetch, AST parsing, graph builder
  tracer/              Simulator, OTel bridge, Python sys tracer
  ai/                  Fix suggester (Anthropic, opt-in)
  models/              Pydantic schemas

frontend/
  src/
    components/        FlowCanvas, IntentPanel, TracePanel, TopBar
    store/             Zustand state
    hooks/             API + WebSocket hooks

infra/                 Docker Compose for OTel + Postgres
scripts/               Dev runner, bootstrap, benchmarks
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / pause trace playback |
| `R` | Reset active trace |
| `F` | Fit graph to view |

---

## Supported Languages & Patterns

| Language | Detected Patterns |
|----------|-------------------|
| TypeScript / React | `onClick`, `onSubmit`, `onChange`, `onKeyDown` handlers |
| Python / FastAPI | `@app.get/post/put/delete` route decorators |
| Python / Flask | `@app.route()` decorators |
| Python / CLI | `argparse` subcommands, `ArgumentParser` patterns |
| Python / Class APIs | Public methods on exported classes |

---

## Scripts

```bash
# Benchmark intent extraction across multiple repos
python3 scripts/benchmark_extraction.py --repos tiangolo/fastapi expressjs/express

# End-to-end dry run (parse + trace without UI)
python3 scripts/e2e_dry_run.py --repo tiangolo/fastapi
```

---

## Notes

- **No data leaves your machine in Sim mode.** The only external call is GitHub's public API to fetch repo contents.
- **AI fixes are opt-in.** The `ANTHROPIC_API_KEY` is only used when you explicitly request a fix. It is never called automatically.
- **OTel mode** works via manual span ingest (`POST /trace/ingest`) even without a running collector. It falls back to simulation when no spans arrive within the session window.

---

Built by [Thirdwheel](https://github.com/thirdwheel-dev).
