# Codeflow

**Intent-anchored code parser and execution tracer for LLM agents.**

Codeflow converts any GitHub repository into a compact `ParsedRepo` graph — functions, intents, types, call edges — that an agent can reason over directly, without reading raw source files. It also runs as an interactive tracer: paste a URL, click an intent, watch the full execution chain animate in real time.

**→ [thirdwheel-codeflow.vercel.app](https://thirdwheel-codeflow.vercel.app)**

---

## Why

An LLM agent navigating an unfamiliar codebase has two options:

1. Read the raw files — high fidelity, extreme token cost, context window exhaustion on any real repo
2. Receive structured metadata — low token cost, but how much signal actually survives?

Codeflow takes option 2 seriously. Every parser decision — what to extract, what to drop, what to index — is made with agent consumption as the primary constraint. The benchmark below measures the tradeoff empirically.

---

## How It Works

```
GitHub URL → Tree-sitter AST → ParsedRepo JSON → agent context
                                      ↓
                             intent graph + call edges
                                      ↓
                        click intent → animated trace (Sim / OTel / Live)
```

The parser extracts every function with its signature, type classification, docstring, return type, and outbound calls. Intent detection finds every user-facing action — API routes, form handlers, CLI commands, class API entry points — and maps each to its call chain. The output is a single structured JSON object an agent can consume in one shot.

---

## Three Trace Modes

| Mode | What it does | Requirement |
|------|-------------|-------------|
| **Sim** | Walks the static call graph; generates a synthetic trace | Any public GitHub URL |
| **OTel** | Receives real spans from a running service | OTel SDK pointed at Codeflow |
| **Live** | Attaches `sys.settrace` to a local process; captures real I/O | Local repo + run command |

---

## Quick Start

**Prerequisites:** Python 3.11+, Node 18+

```bash
# One command
./scripts/dev_local.sh
```

```bash
# Manual
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001

# New terminal
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173`, paste a GitHub repo (e.g. `tiangolo/fastapi`), hit **Parse**.

> **Optional:** Set `GITHUB_TOKEN` in a `.env` file to raise the rate limit from 60 → 5,000 req/hr.

---

## Environment Variables

All optional. Codeflow runs fully offline in Sim mode.

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub PAT — raises rate limit from 60 → 5,000 req/hr |
| `CODEFLOW_GITHUB_FETCH_MODE` | Set to `archive` to force tarball fetch (useful for deterministic benchmarks) |
| `ANTHROPIC_API_KEY` | Enables AI fix suggestions (opt-in, never called automatically) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTel collector endpoint for real span ingestion |
| `DATABASE_URL` | Postgres connection string for trace persistence (falls back to in-memory) |

---

## Benchmark

> **19/21 repos** fully parsed and judged · Run date: 2026-03-30
> Tokenizer: `cl100k_base` (tiktoken) · Retention judge: Gemini 2.5 Flash

### Token Efficiency

| Repo | Raw tokens | CF tokens | Saved | Ratio |
|------|----------:|----------:|------:|------:|
| `psf/requests` | 85,992 | 58,948 | +31.4% | 1.46× |
| `pallets/click` | 166,675 | 127,028 | +23.8% | 1.31× |
| `Textualize/rich` | 292,338 | 63,448 | +78.3% | 4.61× |
| `agronholm/anyio` | 186,698 | 214,973 | -15.1% | 0.87× |
| `httpie/httpie` | 119,789 | 93,545 | +21.9% | 1.28× |
| `anthropics/anthropic-sdk-python` | 191,843 | 145,828 | +24.0% | 1.32× |
| `openai/openai-python` | 183,840 | 179,999 | +2.1% | 1.02× |
| `pallets/flask` | 135,633 | 114,155 | +15.8% | 1.19× |
| `tiangolo/fastapi` | 31,506 | 33,531 | -6.4% | 0.94× |
| `encode/starlette` | 141,009 | 135,252 | +4.1% | 1.04× |
| `encode/httpx` | 134,082 | 80,637 | +39.9% | 1.66× |
| `tortoise/tortoise-orm` | 112,448 | 68,270 | +39.3% | 1.65× |
| `pydantic/pydantic` | 380,113 | 194,967 | +48.7% | 1.95× |
| `Textualize/textual` | 66,195 | 51,777 | +21.8% | 1.28× |
| `celery/celery` | 251,810 | 226,671 | +10.0% | 1.11× |
| `fastapi/full-stack-fastapi-template` | 75,035 | 31,280 | +58.3% | 2.40× |
| `tiangolo/asyncer` | 14,633 | 8,941 | +38.9% | 1.64× |
| `supabase/supabase-js` | 242,974 | 30,639 | +87.4% | 7.93× |
| `trpc/trpc` | 43,531 | 11,523 | +73.5% | 3.78× |
| `vuejs/pinia` | 103,422 | 16,940 | +83.6% | 6.11× |
| `shadcn-ui/ui` | 55,604 | 10,982 | +80.2% | 5.06× |

**Total:** `3,015,170 → 1,899,334` tokens · **Mean savings: 36.3%** · **Avg ratio: 2.36×**

### Semantic Retention (LLM Judge)

5 functions sampled per repo, scored by Gemini 2.5 Flash on signature accuracy, docstring fidelity, and call-chain completeness. Judge model was not involved in parsing.

| Repo | Saved | Retention |
|------|------:|----------:|
| `psf/requests` | 31% | **90%** |
| `Textualize/rich` | 78% | **83%** |
| `pallets/flask` | 16% | **80%** |
| `fastapi/full-stack-fastapi-template` | 58% | **77%** |
| `anthropics/anthropic-sdk-python` | 24% | **74%** |
| `encode/httpx` | 40% | **72%** |
| `tiangolo/fastapi` | -6% | **70%** |
| `pallets/click` | 24% | **70%** |
| `encode/starlette` | 4% | **70%** |
| `sqlalchemy/sqlalchemy` | 43% | **64%** |
| `openai/openai-python` | 1% | **62%** |
| `zauberzeug/nicegui` | 42% | **54%** |
| `httpie/httpie` | 22% | **45%** |
| `pydantic/pydantic` | 48% | **56%** |

**Average retention: 69%** · **Function recall: 100%**

### Benchmark Artifacts

| File | Contents |
|------|----------|
| [`benchmark/CODEFLOW_BENCHMARK_REPORT.md`](benchmark/CODEFLOW_BENCHMARK_REPORT.md) | Full 21-repo token efficiency report |
| [`benchmark/FINAL_BENCHMARK_REPORT.md`](benchmark/FINAL_BENCHMARK_REPORT.md) | Combined 3-pass benchmark (token + recall + LLM judge) |
| [`benchmark/JUDGE_REPORT.md`](benchmark/JUDGE_REPORT.md) | Raw Gemini 2.5 Flash judge output |
| [`benchmark/UNDERSTANDING_REPORT.md`](benchmark/UNDERSTANDING_REPORT.md) | Parser coverage and extraction quality |

### Reproducing

```bash
pip install tiktoken tree-sitter tree-sitter-python tree-sitter-javascript google-generativeai

# Token benchmark (21 repos)
GITHUB_TOKEN=... python -m benchmark.full_benchmark

# Combined 3-pass benchmark with LLM judge
GEMINI_API_KEY=... GITHUB_TOKEN=... python -m benchmark.final_benchmark
```

---

## ParsedRepo Schema

```python
class ParsedFunction(BaseModel):
    id: str                    # Stable short hash — "fn:a1b2c3"
    name: str
    file: str
    type: FunctionType         # route | handler | service | db | auth | util | component | hook | other
    params: list[Param]        # { name, type, direction }
    line: int
    return_type: str
    docstring: str             # First line of docstring / JSDoc
    calls: list[str]           # Outbound call ids

class ParsedRepo(BaseModel):
    schema_version: str
    repo: str                  # owner/repo
    branch: str
    functions: list[ParsedFunction]
    intents: list[Intent]      # User-facing actions mapped to handler_fn_id
    edges: list[Edge]          # Call graph edges (source → target)
    fn_type_index: dict        # { "route": [...ids], "handler": [...ids], ... }
    file_index: dict           # { "path/to/file.py": [...ids], ... }
    file_count: int
    parsed_at: str
```

`fn_type_index` and `file_index` give agents O(1) lookups — "all routes" or "functions in auth.py" — without scanning the full list.

---

## API Reference

```
POST /parse                               Parse a repo → full ParsedRepo JSON
GET  /intents?repo={owner/repo}           Intents list for an already-parsed repo
GET  /occurrences?repo=...&intent_id=...  Call chain for one intent
POST /trace/start                         Start a trace session
POST /trace/ingest                        Ingest OTel spans
GET  /trace/{session_id}                  Fetch trace events
POST /fix                                 AI fix suggestion (opt-in)
DELETE /cache/{repo}                      Clear cached parse
GET  /health                              Health check
WS   /ws/trace/{session_id}              Live trace event stream
```

Full docs: [thirdwheel-codeflow.vercel.app/docs](https://thirdwheel-codeflow.vercel.app/docs)

---

## Repo Layout

```
backend/
  main.py                 FastAPI app + all routes
  parser/                 GitHub fetch, Tree-sitter AST, graph builder
  models/                 Pydantic schemas (ParsedRepo, Intent, TraceEvent)
  tracer/                 Simulator, OTel bridge, Python sys.settrace
  ai/                     Fix suggester (Anthropic, opt-in)
  services/               Intent fusion, metadata store, OTel state

frontend/
  src/
    pages/                LandingPage, BenchmarkPage, DocsPage, LaunchPage
    components/           FlowCanvas, IntentPanel, TracePanel, TopBar
    store/                Zustand state
    hooks/                API + WebSocket hooks

benchmark/
  full_benchmark.py       21-repo token benchmark
  final_benchmark.py      3-pass benchmark with LLM judge
  judge_benchmark.py      Standalone Gemini judge runner
  CODEFLOW_BENCHMARK_REPORT.md
  FINAL_BENCHMARK_REPORT.md
  JUDGE_REPORT.md
  UNDERSTANDING_REPORT.md
```

---

## Supported Patterns

| Language | Detected |
|----------|----------|
| Python / FastAPI | `@app.get/post/put/delete`, `@router.*` |
| Python / Flask | `@app.route()`, blueprint routes |
| Python / CLI | `@click.command()`, `argparse` subcommands |
| Python / Class APIs | Public methods on exported classes |
| TypeScript / React | `onClick`, `onSubmit`, `onChange`, `onKeyDown` handlers |
| Next.js | `'use server'` directives, server actions |

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, Pydantic v2, Tree-sitter, NetworkX |
| Frontend | React 18, TypeScript, Zustand, React Flow, ELK.js |
| Tracing | OpenTelemetry, Python `sys.settrace` |
| Tokenizer | `tiktoken cl100k_base` (benchmark only) |
| Infra (optional) | OTel Collector, Postgres, Docker Compose |

---

## Notes

- **No data leaves your machine in Sim mode.** The only external call is GitHub's public API.
- **AI fixes are opt-in.** `ANTHROPIC_API_KEY` is never called automatically.
- **OTel mode** accepts spans via `POST /trace/ingest` without a running collector. Falls back to simulation when no spans arrive within the session window.
- **In-memory by default.** Set `DATABASE_URL` to persist trace history across restarts.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / pause trace playback |
| `R` | Reset active trace |
| `F` | Fit graph to view |
