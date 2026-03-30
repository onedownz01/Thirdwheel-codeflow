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

## Benchmark — Codeflow as a ParsedRepo for LLM Agents

> Full report: [`benchmark/FINAL_BENCHMARK_REPORT.md`](benchmark/FINAL_BENCHMARK_REPORT.md)
> Run date: 2026-03-30 · 14 repos · 70 functions judged · Judge: Gemini 2.5 Flash

When an LLM agent parses a repository, it has two options: read all raw source files, or consume Codeflow's structured `ParsedRepo` JSON. This benchmark answers two questions:

1. **How many tokens does Codeflow save?**
2. **How much does an agent actually understand from it?**

### 1. Token Efficiency — 14 repos, ~2.3M raw tokens

| Repo | Category | Raw Tokens | CF Tokens | Saved | Ratio |
|------|:--------:|:----------:|:---------:|:-----:|:-----:|
| `fastapi/full-stack-fastapi-template` | App | 75,035 | 31,286 | **58.3%** | 2.40× |
| `zauberzeug/nicegui` | App | 81,128 | 47,034 | **42.0%** | 1.72× |
| `Textualize/rich` | Library | 292,337 | 63,449 | **78.3%** | 4.61× |
| `pydantic/pydantic` | Library | 380,113 | 196,655 | **48.3%** | 1.93× |
| `sqlalchemy/sqlalchemy` | Library | 281,448 | 161,589 | **42.6%** | 1.74× |
| `encode/httpx` | SDK | 134,082 | 80,663 | **39.8%** | 1.66× |
| `psf/requests` | SDK | 85,992 | 58,957 | **31.4%** | 1.46× |
| `anthropics/anthropic-sdk-python` | SDK | 191,843 | 145,706 | **24.0%** | 1.32× |
| `pallets/click` | CLI | 166,675 | 126,972 | **23.8%** | 1.31× |
| `httpie/httpie` | CLI | 119,789 | 93,546 | **21.9%** | 1.28× |
| `pallets/flask` | Framework | 135,633 | 114,082 | **15.9%** | 1.19× |
| `encode/starlette` | Framework | 141,009 | 135,492 | **3.9%** | 1.04× |
| `openai/openai-python` | SDK | 183,840 | 181,780 | **1.1%** | 1.01× |
| `tiangolo/fastapi` | Framework | 31,506 | 33,527 | **-6.4%** | 0.94× |
| **TOTAL** | | **2,300,430** | **1,470,738** | **36.1%** | **1.56×** |

```
  Textualize/rich                    78.3%  ████████████████████░░░░░
  fastapi/full-stack-fastapi-template 58.3%  ███████████████░░░░░░░░░░
  pydantic/pydantic                  48.3%  ████████████░░░░░░░░░░░░░
  sqlalchemy/sqlalchemy              42.6%  ███████████░░░░░░░░░░░░░░
  zauberzeug/nicegui                 42.0%  ███████████░░░░░░░░░░░░░░
  encode/httpx                       39.8%  ██████████░░░░░░░░░░░░░░░
  psf/requests                       31.4%  ████████░░░░░░░░░░░░░░░░░
  anthropics/anthropic-sdk-python    24.0%  ██████░░░░░░░░░░░░░░░░░░░
  pallets/click                      23.8%  ██████░░░░░░░░░░░░░░░░░░░
  httpie/httpie                      21.9%  █████░░░░░░░░░░░░░░░░░░░░
  pallets/flask                      15.9%  ████░░░░░░░░░░░░░░░░░░░░░
  encode/starlette                    3.9%  █░░░░░░░░░░░░░░░░░░░░░░░░
  openai/openai-python                1.1%  ░░░░░░░░░░░░░░░░░░░░░░░░░
  tiangolo/fastapi                   -6.4%  (overhead — no function bodies to strip)
```

**Pattern:** Repos with rich docstrings, large test suites, or comment-heavy code compress best. Pure framework internals (FastAPI itself, Starlette) are near-parity because their source *is* the semantics — almost every line carries signal.

### 2. Comprehension Quality — Ground Truth (ast.walk + regex)

| Metric | Result |
|--------|--------|
| Function recall | **100%** on all 14 repos |
| Return type accuracy | **100%** |
| Route detection | 50–100% (framework-dependent) |
| Docstring coverage | 3–52% (avg 17%) |
| Total intents extracted | 3,869 across 14 repos |

All functions present in source were captured by Codeflow — zero misses across 15,000+ functions.

### 3. LLM Judge — Semantic Comprehension (Gemini 2.5 Flash)

**Methodology:** For each repo, 5 functions are evaluated in 3 passes:
- **Pass A** — Codeflow metadata only (name, type, params, return_type, docstring, calls)
- **Pass B** — Full raw source body
- **Meta-judge** — Gemini scores both descriptions against the actual source

Gemini 2.5 Flash was chosen as an independent judge (not Claude) to avoid circularity.

| Repo | CF Score | Raw Score | Retention | Grade |
|------|:--------:|:---------:|:---------:|:-----:|
| `psf/requests` | 7.0/10 | 7.8/10 | **90%** | A |
| `Textualize/rich` | 6.8/10 | 8.2/10 | **83%** | A |
| `pallets/flask` | 7.2/10 | 9.0/10 | **80%** | A |
| `fastapi/full-stack-fastapi-template` | 7.2/10 | 9.4/10 | **77%** | B+ |
| `anthropics/anthropic-sdk-python` | 7.0/10 | 9.4/10 | **74%** | B+ |
| `encode/httpx` | 6.8/10 | 9.4/10 | **72%** | B+ |
| `encode/starlette` | 6.2/10 | 8.8/10 | **70%** | B+ |
| `pallets/click` | 6.6/10 | 9.4/10 | **70%** | B+ |
| `tiangolo/fastapi` | 7.0/10 | 10.0/10 | **70%** | B+ |
| `sqlalchemy/sqlalchemy` | 5.6/10 | 8.8/10 | **64%** | B |
| `openai/openai-python` | 6.0/10 | 9.6/10 | **62%** | B |
| `zauberzeug/nicegui` | 5.2/10 | 9.6/10 | **54%** | C |
| `pydantic/pydantic` | 5.6/10 | 10.0/10 | **56%** | C |
| `httpie/httpie` | 3.8/10 | 8.4/10 | **45%** | D |
| **AVERAGE** | **6.3/10** | **9.1/10** | **69%** | **B** |

**Retention by use-case category:**

| Category | Repos | Avg Retention | Notes |
|----------|:-----:|:-------------:|-------|
| Python Frameworks (B) | 3 | **73%** | Medium-density code, well-named APIs |
| Python Libraries / SDKs (C) | 4 | **74%** | Typed signatures carry much signal |
| Python App Code (A) | 2 | **65%** | Route logic is captured; business rules need body |
| Mixed / Large Libraries (E) | 3 | **67%** | Variable — rich docstrings help a lot |
| CLI Tools (D) | 2 | **58%** | Argument parsing captured; deep logic is opaque |

**What the scores mean in practice:**

- At **69% retention**, an agent reading Codeflow gets ~7/10 understanding on average with a ~36% token savings. For navigation ("which function handles password reset?"), CF is sufficient. For deep behavioural questions ("does this function prevent email enumeration?"), the raw body wins.
- The **best case** is `psf/requests` at **90% retention** — a small, well-documented library where docstrings cover most of the intent.
- The **worst case** is `httpie/httpie` at **45%** — a CLI tool where most logic lives in deeply nested conditionals that metadata can't express.
- When docstrings are present, CF scores jump ~2 points. The single highest-impact improvement is docstring coverage in the source repo.

### Reproducing the Benchmark

```bash
pip install tiktoken tree-sitter tree-sitter-python tree-sitter-javascript google-generativeai

GEMINI_API_KEY=... GITHUB_TOKEN=... python -m benchmark.final_benchmark
# → benchmark/FINAL_BENCHMARK_REPORT.md
```

---

## Notes

- **No data leaves your machine in Sim mode.** The only external call is GitHub's public API to fetch repo contents.
- **AI fixes are opt-in.** The `ANTHROPIC_API_KEY` is only used when you explicitly request a fix. It is never called automatically.
- **OTel mode** works via manual span ingest (`POST /trace/ingest`) even without a running collector. It falls back to simulation when no spans arrive within the session window.

---

Built by [Thirdwheel](https://github.com/thirdwheel-dev).
