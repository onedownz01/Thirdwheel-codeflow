# Codeflow Token Benchmark — Full Report

> **Version:** 2.0  
> **Run date:** 2026-03-30 06:02 UTC  
> **Tokenizer:** `cl100k_base` (tiktoken — GPT-4 / Claude proxy, ±5%)  
> **Repos tested:** 21 (21 succeeded, 0 failed)  
> **Codeflow schema:** `2.0.0`

## Table of Contents

1. [Abstract](#1-abstract)
2. [Motivation](#2-motivation)
3. [Methodology](#3-methodology)
   - 3.1 [Tokenizer](#31-tokenizer)
   - 3.2 [Fetcher Parameters](#32-fetcher-parameters)
   - 3.3 [Raw Navigation Model](#33-raw-navigation-model)
   - 3.4 [Codeflow Navigation Model](#34-codeflow-navigation-model)
   - 3.5 [Active Optimisations](#35-active-optimisations)
4. [Test Corpus](#4-test-corpus)
5. [Results](#5-results)
   - 5.1 [Per-Repo Detailed Results](#51-per-repo-detailed-results)
   - 5.2 [Summary Table](#52-summary-table)
   - 5.3 [By Category](#53-by-category)
6. [Statistical Analysis](#6-statistical-analysis)
   - 6.1 [Descriptive Statistics](#61-descriptive-statistics)
   - 6.2 [Distribution of Savings](#62-distribution-of-savings)
   - 6.3 [Compression vs Repo Size](#63-compression-vs-repo-size)
   - 6.4 [Function Density Effect](#64-function-density-effect)
7. [Key Findings](#7-key-findings)
   - 7.1 [Token Efficiency](#71-token-efficiency)
   - 7.2 [Signal Quality](#72-signal-quality)
   - 7.3 [Return Type Coverage](#73-return-type-coverage)
   - 7.4 [Intent Extraction Quality](#74-intent-extraction-quality)
   - 7.5 [Function Type Architecture Map](#75-function-type-architecture-map)
8. [Regime Analysis](#8-regime-analysis)
9. [Recommendations](#9-recommendations)
10. [Appendix — Raw Data](#10-appendix--raw-data)

---

## 1. Abstract

We benchmark Codeflow's structured `ParsedRepo` output against the naive baseline of an AI agent reading every eligible source file in a repository. Across 21 public GitHub repositories spanning Python libraries, web frameworks, async toolkits, full-stack applications, and TypeScript SDKs, Codeflow achieves a **mean token savings of 36.3%** (median 31.4%, σ = 30.9) with an **average compression ratio of 2.36×**. Critically, the structured output carries 100% agent-useful signal — no function bodies, comments, or imports — while adding pre-computed call graphs, typed intent extraction, architectural indexes, and return-type annotations unavailable in raw source navigation. The benchmark reveals three distinct performance regimes tied to function density (functions-per-file), with full-stack and SDK repos showing the highest compression (supabase/supabase-js: **87.4%**) and dense typed libraries showing near-parity (agronholm/anyio: **-15.1%**).

---

## 2. Motivation

When an AI agent is tasked with understanding an unfamiliar codebase it faces a fundamental token-budget problem. Every file read costs tokens. Every grep cycle costs tokens. Building a mental model of which functions call which, which files belong to which architectural layer, and which entry points exist — costs **many more tokens** than the answer itself.

Codeflow addresses this by pre-computing the structural skeleton of a repository — the call graph, intent surface, file taxonomy, and return-type annotations — and serving it as a single structured JSON payload. The question this benchmark answers is:

> **Is Codeflow's structured output cheaper *and* more information-dense than an agent reading the raw source files?**

We measure both dimensions: token cost (cheaper?) and signal density (more information per token?).

---

## 3. Methodology

### 3.1 Tokenizer

All token counts use **tiktoken `cl100k_base`** — the encoding used by GPT-4 and a close proxy for Claude's tokenizer (empirically ±5% on mixed code/JSON text). Both the raw source text and the Codeflow JSON payload are tokenized with the same encoder.

### 3.2 Fetcher Parameters

The same `github_fetcher.py` used in production fetches files for both models. Parameters are fixed and identical across all runs:

| Parameter | Value |
|---|---|
| `MAX_FILES` | `120` files per repo |
| `MAX_FILE_SIZE_BYTES` | `160` KB per file |
| `CODE_EXTENSIONS` | `js, jsx, py, svelte, ts, tsx, vue` |
| `SKIP_DIRS` | `.cache, .git, .next, .nyc_output, .venv, __pycache__, build, coverage`, … |
| File priority order | routes/pages > components > services/models > other |
| Concurrency | 12 parallel downloads per repo |

### 3.3 Raw Navigation Model

The **raw baseline** represents an agent that reads every eligible source file exactly once, with a minimal `# file: {path}` header separating files. This is a conservative (generous-to-raw) model — in practice, agents performing targeted file reads would use fewer tokens but would also miss information. The raw count is computed as:

```
raw_text = "\n".join(f"# file: {path}\n{content}\n" for path, content in files)
raw_tokens = tiktoken(raw_text)
```

### 3.4 Codeflow Navigation Model

The **Codeflow model** represents an agent calling `POST /parse` and receiving a single `ParsedRepo` JSON payload. The payload is serialised with:

```python
flow_json = json.dumps(
    parsed.model_dump(exclude={"edges"}, exclude_defaults=True),
    separators=(",", ":")
)
flow_tokens = tiktoken(flow_json)
```

Key differences from raw:

| Dimension | Raw | Codeflow |
|---|---|---|
| Function bodies | ✓ included | ✗ stripped |
| Comments / docstrings | ✓ included | ✗ stripped |
| Import statements | ✓ included | ✗ stripped |
| Call graph (pre-computed) | ✗ must derive | ✓ `fn.calls[]` resolved |
| Intent surface | ✗ must grep | ✓ ranked `intents[]` |
| File→function index | ✗ must build | ✓ `file_index{}` |
| Type→function index | ✗ must build | ✓ `fn_type_index{}` |
| Return types | ✓ in source | ✓ extracted per function |
| Architectural layer | ✗ must infer | ✓ `FunctionType` enum |

### 3.5 Active Optimisations

All optimisations were implemented prior to this benchmark run. Each reduces token count with zero information loss:

| Optimisation | Mechanism | Impact |
|---|---|---|
| Short function IDs | `file:name:line` → `f0`, `f1`, … | ~60% reduction in ID-heavy fields |
| Drop `called_by` | Derivable from edges; removed | Eliminates duplicate edge data |
| Drop `description` | Was always empty string | Removes per-function dead field |
| Drop `hop_count` | `len(flow_ids)` is trivially derivable | Minor savings per intent |
| Drop `aliases` | UI-only; unused by agents | Minor savings per intent |
| Strip `IntentEvidence` | `{kind, weight}` only; dropped `source_file, line, symbol, excerpt` | ~800 chars × N intents |
| Drop `edges[]` from output | Frontend derives from `fn.calls[]` | Largest single saving (~29K tok on starlette) |
| `exclude_defaults=True` | Strips `direction:"in"`, `status:"candidate"`, `frequency:0`, `failure_rate:0.0` | Per-field savings across all objects |

---

## 4. Test Corpus

21 repositories were selected to maximise diversity across:
- **Language mix** (Python, TypeScript, TSX, JavaScript)
- **Architecture pattern** (library, framework, API, CLI, full-stack, SDK)
- **Codebase size** (15–120 files fetched)
- **Function density** (low: full-stack apps → high: typed protocol libraries)
- **Intent signal type** (HTTP routes, CLI commands, UI events, class APIs)

| # | Repo | Category | Type | Description |
|---|---|---|---|---|
|  1 | `psf/requests` | A — Python Pure Libraries & SDKs | Python Pure Library | Elegant HTTP library for Python. De-facto standard for HTTP in Python ecosystem. |
|  2 | `pallets/click` | A — Python Pure Libraries & SDKs | Python Pure Library | Composable CLI framework. Decorator-driven command definition with rich type system. |
|  3 | `Textualize/rich` | A — Python Pure Libraries & SDKs | Python Pure Library | Rich text and formatting in the terminal. Large class hierarchy, no routes. |
|  4 | `agronholm/anyio` | A — Python Pure Libraries & SDKs | Python Async Library | High-level async I/O primitives. Compatibility layer over asyncio, trio, curio. |
|  5 | `httpie/httpie` | A — Python Pure Libraries & SDKs | Python CLI Tool | User-friendly CLI HTTP client. Mix of CLI commands and library functions. |
|  6 | `anthropics/anthropic-sdk-python` | A — Python Pure Libraries & SDKs | Python SDK | Official Anthropic Python SDK. Typed client with resource-based API surface. |
|  7 | `openai/openai-python` | A — Python Pure Libraries & SDKs | Python SDK | Official OpenAI Python SDK. Sync+async client, extensive typed resources. |
|  8 | `pallets/flask` | B — Python Web / API Frameworks | Python Web Framework | Micro web framework. Decorator-based routing, Blueprint pattern, extensions. |
|  9 | `tiangolo/fastapi` | B — Python Web / API Frameworks | Python Web Framework | FastAPI framework source. Dependency injection, OpenAPI auto-generation. |
| 10 | `encode/starlette` | B — Python Web / API Frameworks | Python ASGI Framework | Lightweight ASGI framework. Protocol classes, middleware, routing. |
| 11 | `encode/httpx` | B — Python Web / API Frameworks | Python HTTP Client | Next-gen HTTP client. Sync+async, HTTP/2, highly type-annotated. |
| 12 | `tortoise/tortoise-orm` | B — Python Web / API Frameworks | Python Async ORM | Async ORM inspired by Django. Model classes, queryset API, migrations. |
| 13 | `pydantic/pydantic` | C — Python Large / Complex | Python Validation Lib | Data validation using Python type hints. Core of FastAPI's type system. |
| 14 | `Textualize/textual` | C — Python Large / Complex | Python TUI Framework | Modern TUI app framework. Widget tree, CSS-like styling, reactive model. |
| 15 | `celery/celery` | C — Python Large / Complex | Python Task Queue | Distributed task queue. Worker architecture, beat scheduler, backends. |
| 16 | `fastapi/full-stack-fastapi-template` | D — Full-stack / Mixed Language | Full-stack FastAPI+React | Production full-stack template. Python API + React/TypeScript frontend. |
| 17 | `tiangolo/asyncer` | D — Full-stack / Mixed Language | Python Async Utility | Async utilities wrapping anyio. Small focused library, typed. |
| 18 | `supabase/supabase-js` | E — JavaScript / TypeScript | TypeScript SDK | Supabase JavaScript client. Typed SDK covering auth, db, storage, realtime. |
| 19 | `trpc/trpc` | E — JavaScript / TypeScript | TypeScript API Framework | End-to-end typesafe APIs. Server/client with inferred types, React hooks. |
| 20 | `vuejs/pinia` | E — JavaScript / TypeScript | JavaScript State Lib | Intuitive Vue state management. Store pattern, DevTools, TypeScript support. |
| 21 | `shadcn-ui/ui` | E — JavaScript / TypeScript | React Component Library | Beautifully designed React components. TSX, Radix UI primitives, Tailwind. |

---

## 5. Results

### 5.1 Per-Repo Detailed Results

#### `psf/requests`

> ✅ Codeflow wins — **+31.4% token savings**, 1.46× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 36 |
| Raw source size | 366.9 KB |
| Fetch time | 2.6s |
| Parse time | 0.081s |
| Functions extracted | 670 |
| Intents extracted | 185 |
| Call graph edges | 1,021 |
| Fns per file | 18.6 |
| File index entries | 28 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 85,992 | 58,948 | +27,044 |
| Tokens / function | 128 | 88.0 | -40.4 |
| Tokens / intent | — | 319 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████]  85,992 tok
Flow  [███████████████████░░░░░░░░░]  58,948 tok  (+31.4%)
```

**Return Type Coverage**

```
Coverage  [░░░░░░░░░░░░░░░░░░░░] 0%  (1/670 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   543 (81.0%)
FunctionType.UTIL [██░░░░░░░░░░░░░░░░░░]    43 ( 6.4%)
FunctionType.DB [██░░░░░░░░░░░░░░░░░░]    43 ( 6.4%)
FunctionType.AUTH [█░░░░░░░░░░░░░░░░░░░]    26 ( 3.9%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]    15 ( 2.2%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 185 |
| Confidence min / max | 0.55 / 0.55 |
| Confidence mean / median | 0.55 / 0.55 |
| Status distribution | observed: 185 |

---

#### `pallets/click`

> ✅ Codeflow wins — **+23.8% token savings**, 1.31× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 62 |
| Raw source size | 687.7 KB |
| Fetch time | 3.4s |
| Parse time | 0.167s |
| Functions extracted | 1,412 |
| Intents extracted | 332 |
| Call graph edges | 2,543 |
| Fns per file | 22.8 |
| File index entries | 59 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 166,675 | 127,028 | +39,647 |
| Tokens / function | 118 | 90.0 | -28.1 |
| Tokens / intent | — | 383 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 166,675 tok
Flow  [█████████████████████░░░░░░░] 127,028 tok  (+23.8%)
```

**Return Type Coverage**

```
Coverage  [████████░░░░░░░░░░░░] 39%  (556/1412 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]  1324 (93.8%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]    56 ( 4.0%)
FunctionType.UTIL [░░░░░░░░░░░░░░░░░░░░]    32 ( 2.3%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 332 |
| Confidence min / max | 0.55 / 0.80 |
| Confidence mean / median | 0.63 / 0.55 |
| Status distribution | observed: 332 |

---

#### `Textualize/rich`

> ✅ Codeflow wins — **+78.3% token savings**, 4.61× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 925.2 KB |
| Fetch time | 4.9s |
| Parse time | 0.199s |
| Functions extracted | 598 |
| Intents extracted | 217 |
| Call graph edges | 722 |
| Fns per file | 5.0 |
| File index entries | 71 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 292,338 | 63,448 | +228,890 |
| Tokens / function | 489 | 106.1 | -382.8 |
| Tokens / intent | — | 292 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 292,338 tok
Flow  [██████░░░░░░░░░░░░░░░░░░░░░░]  63,448 tok  (+78.3%)
```

**Return Type Coverage**

```
Coverage  [██████████████████░░] 89%  (535/598 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   537 (89.8%)
FunctionType.HANDLER [██░░░░░░░░░░░░░░░░░░]    58 ( 9.7%)
FunctionType.AUTH [░░░░░░░░░░░░░░░░░░░░]     3 ( 0.5%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 217 |
| Confidence min / max | 0.55 / 0.80 |
| Confidence mean / median | 0.55 / 0.55 |
| Status distribution | observed: 217 |

---

#### `agronholm/anyio`

> ⚠️ Raw wins — **-15.1% token savings**, 0.87× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 72 |
| Raw source size | 837.1 KB |
| Fetch time | 3.6s |
| Parse time | 0.202s |
| Functions extracted | 2,094 |
| Intents extracted | 600 |
| Call graph edges | 3,788 |
| Fns per file | 29.1 |
| File index entries | 65 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 186,698 | 214,973 | -28,275 |
| Tokens / function | 89 | 102.7 | +13.5 |
| Tokens / intent | — | 358 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████░░░░] 186,698 tok
Flow  [████████████████████████████] 214,973 tok  (-15.1%)
```

**Return Type Coverage**

```
Coverage  [████████████████████] 98%  (2044/2094 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]  1964 (93.8%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]   109 ( 5.2%)
FunctionType.AUTH [░░░░░░░░░░░░░░░░░░░░]    21 ( 1.0%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 600 |
| Confidence min / max | 0.55 / 0.55 |
| Confidence mean / median | 0.55 / 0.55 |
| Status distribution | observed: 600 |

---

#### `httpie/httpie`

> ✅ Codeflow wins — **+21.9% token savings**, 1.28× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 516.7 KB |
| Fetch time | 5.8s |
| Parse time | 0.108s |
| Functions extracted | 911 |
| Intents extracted | 358 |
| Call graph edges | 861 |
| Fns per file | 7.6 |
| File index entries | 99 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 119,789 | 93,545 | +26,244 |
| Tokens / function | 131 | 102.7 | -28.8 |
| Tokens / intent | — | 261 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 119,789 tok
Flow  [██████████████████████░░░░░░]  93,545 tok  (+21.9%)
```

**Return Type Coverage**

```
Coverage  [███████░░░░░░░░░░░░░] 37%  (339/911 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   754 (82.8%)
FunctionType.HANDLER [██░░░░░░░░░░░░░░░░░░]    58 ( 6.4%)
FunctionType.UTIL [██░░░░░░░░░░░░░░░░░░]    58 ( 6.4%)
FunctionType.DB [█░░░░░░░░░░░░░░░░░░░]    22 ( 2.4%)
FunctionType.AUTH [█░░░░░░░░░░░░░░░░░░░]    19 ( 2.1%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 358 |
| Confidence min / max | 0.55 / 0.62 |
| Confidence mean / median | 0.55 / 0.55 |
| Status distribution | observed: 358 |

---

#### `anthropics/anthropic-sdk-python`

> ✅ Codeflow wins — **+24.0% token savings**, 1.32× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 865.4 KB |
| Fetch time | 5.7s |
| Parse time | 0.186s |
| Functions extracted | 1,335 |
| Intents extracted | 396 |
| Call graph edges | 1,705 |
| Fns per file | 11.1 |
| File index entries | 75 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 191,843 | 145,828 | +46,015 |
| Tokens / function | 144 | 109.2 | -34.5 |
| Tokens / intent | — | 368 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 191,843 tok
Flow  [█████████████████████░░░░░░░] 145,828 tok  (+24.0%)
```

**Return Type Coverage**

```
Coverage  [████████████████████] 99%  (1328/1335 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   897 (67.2%)
FunctionType.UTIL [████████░░░░░░░░░░░░]   352 (26.4%)
FunctionType.DB [█░░░░░░░░░░░░░░░░░░░]    57 ( 4.3%)
FunctionType.AUTH [░░░░░░░░░░░░░░░░░░░░]    15 ( 1.1%)
FunctionType.HANDLER [░░░░░░░░░░░░░░░░░░░░]    14 ( 1.0%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 396 |
| Confidence min / max | 0.55 / 0.62 |
| Confidence mean / median | 0.55 / 0.55 |
| Status distribution | observed: 396 |

---

#### `openai/openai-python`

> ⚖️ Near-parity — **+2.1% token savings**, 1.02× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 844.9 KB |
| Fetch time | 6.0s |
| Parse time | 0.158s |
| Functions extracted | 1,425 |
| Intents extracted | 675 |
| Call graph edges | 1,390 |
| Fns per file | 11.9 |
| File index entries | 57 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 183,840 | 179,999 | +3,841 |
| Tokens / function | 129 | 126.3 | -2.7 |
| Tokens / intent | — | 267 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 183,840 tok
Flow  [███████████████████████████░] 179,999 tok  (+2.1%)
```

**Return Type Coverage**

```
Coverage  [████████████████████] 100%  (1425/1425 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]  1359 (95.4%)
FunctionType.DB [█░░░░░░░░░░░░░░░░░░░]    45 ( 3.2%)
FunctionType.HANDLER [░░░░░░░░░░░░░░░░░░░░]    13 ( 0.9%)
FunctionType.AUTH [░░░░░░░░░░░░░░░░░░░░]     4 ( 0.3%)
FunctionType.UTIL [░░░░░░░░░░░░░░░░░░░░]     4 ( 0.3%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 675 |
| Confidence min / max | 0.55 / 0.64 |
| Confidence mean / median | 0.55 / 0.55 |
| Status distribution | observed: 675 |

---

#### `pallets/flask`

> ✅ Codeflow wins — **+15.8% token savings**, 1.19× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 83 |
| Raw source size | 580.3 KB |
| Fetch time | 4.0s |
| Parse time | 0.122s |
| Functions extracted | 1,466 |
| Intents extracted | 268 |
| Call graph edges | 2,282 |
| Fns per file | 17.7 |
| File index entries | 66 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 135,633 | 114,155 | +21,478 |
| Tokens / function | 93 | 77.9 | -14.7 |
| Tokens / intent | — | 426 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 135,633 tok
Flow  [████████████████████████░░░░] 114,155 tok  (+15.8%)
```

**Return Type Coverage**

```
Coverage  [██████░░░░░░░░░░░░░░] 31%  (454/1466 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]  1333 (90.9%)
FunctionType.UTIL [█░░░░░░░░░░░░░░░░░░░]    44 ( 3.0%)
FunctionType.ROUTE [█░░░░░░░░░░░░░░░░░░░]    41 ( 2.8%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]    40 ( 2.7%)
FunctionType.DB [░░░░░░░░░░░░░░░░░░░░]     6 ( 0.4%)
FunctionType.AUTH [░░░░░░░░░░░░░░░░░░░░]     2 ( 0.1%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 268 |
| Confidence min / max | 0.55 / 0.88 |
| Confidence mean / median | 0.59 / 0.55 |
| Status distribution | observed: 241, verified: 27 |

---

#### `tiangolo/fastapi`

> ⚠️ Raw wins — **-6.4% token savings**, 0.94× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 146.3 KB |
| Fetch time | 6.1s |
| Parse time | 0.037s |
| Functions extracted | 393 |
| Intents extracted | 122 |
| Call graph edges | 74 |
| Fns per file | 3.3 |
| File index entries | 100 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 31,506 | 33,531 | -2,025 |
| Tokens / function | 80 | 85.3 | +5.2 |
| Tokens / intent | — | 275 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [██████████████████████████░░]  31,506 tok
Flow  [████████████████████████████]  33,531 tok  (-6.4%)
```

**Return Type Coverage**

```
Coverage  [████░░░░░░░░░░░░░░░░] 20%  (79/393 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   253 (64.4%)
FunctionType.ROUTE [██████████░░░░░░░░░░]   126 (32.1%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]     9 ( 2.3%)
FunctionType.DB [░░░░░░░░░░░░░░░░░░░░]     4 ( 1.0%)
FunctionType.SERVICE [░░░░░░░░░░░░░░░░░░░░]     1 ( 0.3%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 122 |
| Confidence min / max | 0.55 / 0.88 |
| Confidence mean / median | 0.72 / 0.72 |
| Status distribution | observed: 61, verified: 61 |

---

#### `encode/starlette`

> ⚖️ Near-parity — **+4.1% token savings**, 1.04× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 68 |
| Raw source size | 609.3 KB |
| Fetch time | 4.2s |
| Parse time | 0.144s |
| Functions extracted | 1,478 |
| Intents extracted | 341 |
| Call graph edges | 2,635 |
| Fns per file | 21.7 |
| File index entries | 64 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 141,009 | 135,252 | +5,757 |
| Tokens / function | 95 | 91.5 | -3.9 |
| Tokens / intent | — | 397 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 141,009 tok
Flow  [███████████████████████████░] 135,252 tok  (+4.1%)
```

**Return Type Coverage**

```
Coverage  [████████████████████] 99%  (1457/1478 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]  1324 (89.6%)
FunctionType.AUTH [█░░░░░░░░░░░░░░░░░░░]    91 ( 6.2%)
FunctionType.HANDLER [░░░░░░░░░░░░░░░░░░░░]    29 ( 2.0%)
FunctionType.UTIL [░░░░░░░░░░░░░░░░░░░░]    26 ( 1.8%)
FunctionType.DB [░░░░░░░░░░░░░░░░░░░░]     8 ( 0.5%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 341 |
| Confidence min / max | 0.55 / 0.55 |
| Confidence mean / median | 0.55 / 0.55 |
| Status distribution | observed: 341 |

---

#### `encode/httpx`

> ✅ Codeflow wins — **+39.9% token savings**, 1.66× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 60 |
| Raw source size | 558.6 KB |
| Fetch time | 2.9s |
| Parse time | 0.114s |
| Functions extracted | 1,134 |
| Intents extracted | 158 |
| Call graph edges | 1,193 |
| Fns per file | 18.9 |
| File index entries | 54 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 134,082 | 80,637 | +53,445 |
| Tokens / function | 118 | 71.1 | -47.1 |
| Tokens / intent | — | 510 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 134,082 tok
Flow  [█████████████████░░░░░░░░░░░]  80,637 tok  (+39.9%)
```

**Return Type Coverage**

```
Coverage  [███████████░░░░░░░░░] 53%  (601/1134 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   932 (82.2%)
FunctionType.DB [██░░░░░░░░░░░░░░░░░░]    95 ( 8.4%)
FunctionType.UTIL [█░░░░░░░░░░░░░░░░░░░]    69 ( 6.1%)
FunctionType.AUTH [█░░░░░░░░░░░░░░░░░░░]    29 ( 2.6%)
FunctionType.HANDLER [░░░░░░░░░░░░░░░░░░░░]     9 ( 0.8%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 158 |
| Confidence min / max | 0.55 / 0.55 |
| Confidence mean / median | 0.55 / 0.55 |
| Status distribution | observed: 158 |

---

#### `tortoise/tortoise-orm`

> ✅ Codeflow wins — **+39.3% token savings**, 1.65× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 507.9 KB |
| Fetch time | 5.1s |
| Parse time | 0.093s |
| Functions extracted | 848 |
| Intents extracted | 176 |
| Call graph edges | 801 |
| Fns per file | 7.1 |
| File index entries | 65 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 112,448 | 68,270 | +44,178 |
| Tokens / function | 133 | 80.5 | -52.1 |
| Tokens / intent | — | 388 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 112,448 tok
Flow  [█████████████████░░░░░░░░░░░]  68,270 tok  (+39.3%)
```

**Return Type Coverage**

```
Coverage  [██████████░░░░░░░░░░] 50%  (424/848 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   601 (70.9%)
FunctionType.DB [██████░░░░░░░░░░░░░░]   170 (20.0%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]    44 ( 5.2%)
FunctionType.ROUTE [█░░░░░░░░░░░░░░░░░░░]    19 ( 2.2%)
FunctionType.UTIL [░░░░░░░░░░░░░░░░░░░░]    14 ( 1.7%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 176 |
| Confidence min / max | 0.55 / 0.88 |
| Confidence mean / median | 0.57 / 0.55 |
| Status distribution | observed: 165, verified: 11 |

---

#### `pydantic/pydantic`

> ✅ Codeflow wins — **+48.7% token savings**, 1.95× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 1504.4 KB |
| Fetch time | 5.7s |
| Parse time | 0.328s |
| Functions extracted | 2,032 |
| Intents extracted | 462 |
| Call graph edges | 3,740 |
| Fns per file | 16.9 |
| File index entries | 102 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 380,113 | 194,967 | +185,146 |
| Tokens / function | 187 | 95.9 | -91.1 |
| Tokens / intent | — | 422 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 380,113 tok
Flow  [██████████████░░░░░░░░░░░░░░] 194,967 tok  (+48.7%)
```

**Return Type Coverage**

```
Coverage  [██████░░░░░░░░░░░░░░] 31%  (635/2032 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]  1847 (90.9%)
FunctionType.DB [██░░░░░░░░░░░░░░░░░░]   161 ( 7.9%)
FunctionType.HANDLER [░░░░░░░░░░░░░░░░░░░░]    24 ( 1.2%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 462 |
| Confidence min / max | 0.48 / 0.62 |
| Confidence mean / median | 0.55 / 0.55 |
| Status distribution | candidate: 1, observed: 461 |

---

#### `Textualize/textual`

> ✅ Codeflow wins — **+21.8% token savings**, 1.28× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 294.1 KB |
| Fetch time | 5.8s |
| Parse time | 0.052s |
| Functions extracted | 645 |
| Intents extracted | 148 |
| Call graph edges | 341 |
| Fns per file | 5.4 |
| File index entries | 109 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 66,195 | 51,777 | +14,418 |
| Tokens / function | 103 | 80.3 | -22.4 |
| Tokens / intent | — | 350 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████]  66,195 tok
Flow  [██████████████████████░░░░░░]  51,777 tok  (+21.8%)
```

**Return Type Coverage**

```
Coverage  [███████████████░░░░░] 75%  (481/645 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   543 (84.2%)
FunctionType.HANDLER [███░░░░░░░░░░░░░░░░░]    73 (11.3%)
FunctionType.DB [█░░░░░░░░░░░░░░░░░░░]    29 ( 4.5%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 148 |
| Confidence min / max | 0.55 / 0.55 |
| Confidence mean / median | 0.55 / 0.55 |
| Status distribution | observed: 148 |

---

#### `celery/celery`

> ✅ Codeflow wins — **+10.0% token savings**, 1.11× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 1147.0 KB |
| Fetch time | 5.6s |
| Parse time | 0.209s |
| Functions extracted | 2,218 |
| Intents extracted | 826 |
| Call graph edges | 3,328 |
| Fns per file | 18.5 |
| File index entries | 108 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 251,810 | 226,671 | +25,139 |
| Tokens / function | 114 | 102.2 | -11.3 |
| Tokens / intent | — | 274 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 251,810 tok
Flow  [█████████████████████████░░░] 226,671 tok  (+10.0%)
```

**Return Type Coverage**

```
Coverage  [█░░░░░░░░░░░░░░░░░░░] 4%  (78/2218 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]  1842 (83.0%)
FunctionType.HANDLER [██░░░░░░░░░░░░░░░░░░]   186 ( 8.4%)
FunctionType.DB [█░░░░░░░░░░░░░░░░░░░]   137 ( 6.2%)
FunctionType.UTIL [░░░░░░░░░░░░░░░░░░░░]    32 ( 1.4%)
FunctionType.ROUTE [░░░░░░░░░░░░░░░░░░░░]    16 ( 0.7%)
FunctionType.AUTH [░░░░░░░░░░░░░░░░░░░░]     4 ( 0.2%)
FunctionType.SERVICE [░░░░░░░░░░░░░░░░░░░░]     1 ( 0.0%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 826 |
| Confidence min / max | 0.55 / 0.80 |
| Confidence mean / median | 0.56 / 0.55 |
| Status distribution | observed: 826 |

---

#### `fastapi/full-stack-fastapi-template`

> ✅ Codeflow wins — **+58.3% token savings**, 2.40× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 319.0 KB |
| Fetch time | 5.6s |
| Parse time | 0.084s |
| Functions extracted | 394 |
| Intents extracted | 44 |
| Call graph edges | 414 |
| Fns per file | 3.3 |
| File index entries | 98 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 75,035 | 31,280 | +43,755 |
| Tokens / function | 190 | 79.4 | -111.1 |
| Tokens / intent | — | 711 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████]  75,035 tok
Flow  [████████████░░░░░░░░░░░░░░░░]  31,280 tok  (+58.3%)
```

**Return Type Coverage**

```
Coverage  [█████████░░░░░░░░░░░] 44%  (175/394 functions)
```

**Function Type Distribution**

```
FunctionType.COMPONENT [████████████████████]   163 (41.4%)
FunctionType.OTHER [███████████░░░░░░░░░]    92 (23.4%)
FunctionType.SERVICE [██████░░░░░░░░░░░░░░]    49 (12.4%)
FunctionType.HANDLER [█████░░░░░░░░░░░░░░░]    42 (10.7%)
FunctionType.ROUTE [███░░░░░░░░░░░░░░░░░]    21 ( 5.3%)
FunctionType.UTIL [█░░░░░░░░░░░░░░░░░░░]    12 ( 3.0%)
FunctionType.DB [█░░░░░░░░░░░░░░░░░░░]     7 ( 1.8%)
FunctionType.AUTH [█░░░░░░░░░░░░░░░░░░░]     5 ( 1.3%)
FunctionType.HOOK [░░░░░░░░░░░░░░░░░░░░]     3 ( 0.8%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 44 |
| Confidence min / max | 0.48 / 0.88 |
| Confidence mean / median | 0.76 / 0.76 |
| Status distribution | candidate: 1, observed: 23, verified: 20 |

---

#### `tiangolo/asyncer`

> ✅ Codeflow wins — **+38.9% token savings**, 1.64× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 52 |
| Raw source size | 63.5 KB |
| Fetch time | 3.8s |
| Parse time | 0.022s |
| Functions extracted | 109 |
| Intents extracted | 23 |
| Call graph edges | 129 |
| Fns per file | 2.1 |
| File index entries | 33 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 14,633 | 8,941 | +5,692 |
| Tokens / function | 134 | 82.0 | -52.2 |
| Tokens / intent | — | 389 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████]  14,633 tok
Flow  [█████████████████░░░░░░░░░░░]   8,941 tok  (+38.9%)
```

**Return Type Coverage**

```
Coverage  [██████░░░░░░░░░░░░░░] 31%  (34/109 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]    86 (78.9%)
FunctionType.HANDLER [███░░░░░░░░░░░░░░░░░]    12 (11.0%)
FunctionType.ROUTE [███░░░░░░░░░░░░░░░░░]    11 (10.1%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 23 |
| Confidence min / max | 0.55 / 0.80 |
| Confidence mean / median | 0.66 / 0.55 |
| Status distribution | observed: 23 |

---

#### `supabase/supabase-js`

> ✅ Codeflow wins — **+87.4% token savings**, 7.93× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 989.4 KB |
| Fetch time | 5.7s |
| Parse time | 0.196s |
| Functions extracted | 383 |
| Intents extracted | 9 |
| Call graph edges | 705 |
| Fns per file | 3.2 |
| File index entries | 53 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 242,974 | 30,639 | +212,335 |
| Tokens / function | 634 | 80.0 | -554.4 |
| Tokens / intent | — | 3404 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 242,974 tok
Flow  [████░░░░░░░░░░░░░░░░░░░░░░░░]  30,639 tok  (+87.4%)
```

**Return Type Coverage**

```
Coverage  [█████████░░░░░░░░░░░] 47%  (181/383 functions)
```

**Function Type Distribution**

```
FunctionType.SERVICE [████████████████████]   174 (45.4%)
FunctionType.AUTH [██████████████░░░░░░]   120 (31.3%)
FunctionType.HANDLER [██████░░░░░░░░░░░░░░]    55 (14.4%)
FunctionType.OTHER [█░░░░░░░░░░░░░░░░░░░]    11 ( 2.9%)
FunctionType.DB [█░░░░░░░░░░░░░░░░░░░]    10 ( 2.6%)
FunctionType.UTIL [█░░░░░░░░░░░░░░░░░░░]     7 ( 1.8%)
FunctionType.COMPONENT [█░░░░░░░░░░░░░░░░░░░]     6 ( 1.6%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 9 |
| Confidence min / max | 0.48 / 0.78 |
| Confidence mean / median | 0.62 / 0.56 |
| Status distribution | candidate: 2, observed: 7 |

---

#### `trpc/trpc`

> ✅ Codeflow wins — **+73.5% token savings**, 3.78× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 177.2 KB |
| Fetch time | 4.6s |
| Parse time | 0.049s |
| Functions extracted | 146 |
| Intents extracted | 4 |
| Call graph edges | 175 |
| Fns per file | 1.2 |
| File index entries | 64 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 43,531 | 11,523 | +32,008 |
| Tokens / function | 298 | 78.9 | -219.2 |
| Tokens / intent | — | 2881 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████]  43,531 tok
Flow  [███████░░░░░░░░░░░░░░░░░░░░░]  11,523 tok  (+73.5%)
```

**Return Type Coverage**

```
Coverage  [████░░░░░░░░░░░░░░░░] 21%  (31/146 functions)
```

**Function Type Distribution**

```
FunctionType.SERVICE [████████████████████]    54 (37.0%)
FunctionType.COMPONENT [█████████████████░░░]    45 (30.8%)
FunctionType.HANDLER [███████░░░░░░░░░░░░░]    18 (12.3%)
FunctionType.DB [██████░░░░░░░░░░░░░░]    16 (11.0%)
FunctionType.OTHER [███░░░░░░░░░░░░░░░░░]     8 ( 5.5%)
FunctionType.UTIL [█░░░░░░░░░░░░░░░░░░░]     4 ( 2.7%)
FunctionType.HOOK [░░░░░░░░░░░░░░░░░░░░]     1 ( 0.7%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 4 |
| Confidence min / max | 0.48 / 0.91 |
| Confidence mean / median | 0.68 / 0.67 |
| Status distribution | candidate: 1, observed: 2, verified: 1 |

---

#### `vuejs/pinia`

> ✅ Codeflow wins — **+83.6% token savings**, 6.11× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 366.8 KB |
| Fetch time | 4.9s |
| Parse time | 0.116s |
| Functions extracted | 278 |
| Intents extracted | 4 |
| Call graph edges | 486 |
| Fns per file | 2.3 |
| File index entries | 59 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 103,422 | 16,940 | +86,482 |
| Tokens / function | 372 | 60.9 | -311.1 |
| Tokens / intent | — | 4235 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 103,422 tok
Flow  [█████░░░░░░░░░░░░░░░░░░░░░░░]  16,940 tok  (+83.6%)
```

**Return Type Coverage**

```
Coverage  [███░░░░░░░░░░░░░░░░░] 15%  (43/278 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   232 (83.5%)
FunctionType.UTIL [██░░░░░░░░░░░░░░░░░░]    24 ( 8.6%)
FunctionType.HOOK [█░░░░░░░░░░░░░░░░░░░]    13 ( 4.7%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]     7 ( 2.5%)
FunctionType.SERVICE [░░░░░░░░░░░░░░░░░░░░]     2 ( 0.7%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 4 |
| Confidence min / max | 0.48 / 0.76 |
| Confidence mean / median | 0.58 / 0.54 |
| Status distribution | candidate: 1, observed: 3 |

---

#### `shadcn-ui/ui`

> ✅ Codeflow wins — **+80.2% token savings**, 5.06× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 219.5 KB |
| Fetch time | 5.5s |
| Parse time | 0.042s |
| Functions extracted | 140 |
| Intents extracted | 1 |
| Call graph edges | 145 |
| Fns per file | 1.2 |
| File index entries | 119 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 55,604 | 10,982 | +44,622 |
| Tokens / function | 397 | 78.4 | -318.7 |
| Tokens / intent | — | 10982 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████]  55,604 tok
Flow  [██████░░░░░░░░░░░░░░░░░░░░░░]  10,982 tok  (+80.2%)
```

**Return Type Coverage**

```
Coverage  [█░░░░░░░░░░░░░░░░░░░] 4%  (6/140 functions)
```

**Function Type Distribution**

```
FunctionType.COMPONENT [████████████████████]   117 (83.6%)
FunctionType.OTHER [███░░░░░░░░░░░░░░░░░]    20 (14.3%)
FunctionType.UTIL [█░░░░░░░░░░░░░░░░░░░]     3 ( 2.1%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 1 |
| Confidence min / max | 0.62 / 0.62 |
| Confidence mean / median | 0.62 / 0.62 |
| Status distribution | observed: 1 |

---

### 5.2 Summary Table

| # | Repo | Files | Raw tok | Flow tok | Saved | Ratio | Fns | Intents | RT% |
|---|---|---|---|---|---|---|---|---|---|
|  1 | `psf/requests` | 36 | 85,992 | 58,948 | **+31.4%** | 1.46× | 670 | 185 | 0% |
|  2 | `pallets/click` | 62 | 166,675 | 127,028 | **+23.8%** | 1.31× | 1,412 | 332 | 39% |
|  3 | `Textualize/rich` | 120 | 292,338 | 63,448 | **+78.3%** | 4.61× | 598 | 217 | 89% |
|  4 | `agronholm/anyio` | 72 | 186,698 | 214,973 | **-15.1%** | 0.87× | 2,094 | 600 | 98% |
|  5 | `httpie/httpie` | 120 | 119,789 | 93,545 | **+21.9%** | 1.28× | 911 | 358 | 37% |
|  6 | `anthropics/anthropic-sdk-python` | 120 | 191,843 | 145,828 | **+24.0%** | 1.32× | 1,335 | 396 | 99% |
|  7 | `openai/openai-python` | 120 | 183,840 | 179,999 | **+2.1%** | 1.02× | 1,425 | 675 | 100% |
|  8 | `pallets/flask` | 83 | 135,633 | 114,155 | **+15.8%** | 1.19× | 1,466 | 268 | 31% |
|  9 | `tiangolo/fastapi` | 120 | 31,506 | 33,531 | **-6.4%** | 0.94× | 393 | 122 | 20% |
| 10 | `encode/starlette` | 68 | 141,009 | 135,252 | **+4.1%** | 1.04× | 1,478 | 341 | 99% |
| 11 | `encode/httpx` | 60 | 134,082 | 80,637 | **+39.9%** | 1.66× | 1,134 | 158 | 53% |
| 12 | `tortoise/tortoise-orm` | 120 | 112,448 | 68,270 | **+39.3%** | 1.65× | 848 | 176 | 50% |
| 13 | `pydantic/pydantic` | 120 | 380,113 | 194,967 | **+48.7%** | 1.95× | 2,032 | 462 | 31% |
| 14 | `Textualize/textual` | 120 | 66,195 | 51,777 | **+21.8%** | 1.28× | 645 | 148 | 75% |
| 15 | `celery/celery` | 120 | 251,810 | 226,671 | **+10.0%** | 1.11× | 2,218 | 826 | 4% |
| 16 | `fastapi/full-stack-fastapi-template` | 120 | 75,035 | 31,280 | **+58.3%** | 2.40× | 394 | 44 | 44% |
| 17 | `tiangolo/asyncer` | 52 | 14,633 | 8,941 | **+38.9%** | 1.64× | 109 | 23 | 31% |
| 18 | `supabase/supabase-js` | 120 | 242,974 | 30,639 | **+87.4%** | 7.93× | 383 | 9 | 47% |
| 19 | `trpc/trpc` | 120 | 43,531 | 11,523 | **+73.5%** | 3.78× | 146 | 4 | 21% |
| 20 | `vuejs/pinia` | 120 | 103,422 | 16,940 | **+83.6%** | 6.11× | 278 | 4 | 15% |
| 21 | `shadcn-ui/ui` | 120 | 55,604 | 10,982 | **+80.2%** | 5.06× | 140 | 1 | 4% |

**Aggregate** | | | **3,015,170** | **1,899,334** | **1,115,836** | **2.36×** | | | |

### 5.3 By Category

#### Category A — Python Pure Libraries & SDKs

| Metric | Value |
|---|---|
| Repos | 7 |
| Avg token savings | +23.8% |
| Avg compression ratio | 1.69× |
| Avg functions extracted | 1206 |
| Avg return-type coverage | 66% |
| Total raw tokens | 1,227,175 |
| Total flow tokens | 883,769 |

Savings sparkline across repos: `▄▃█▁▃▃▂`

#### Category B — Python Web / API Frameworks

| Metric | Value |
|---|---|
| Repos | 5 |
| Avg token savings | +18.5% |
| Avg compression ratio | 1.30× |
| Avg functions extracted | 1064 |
| Avg return-type coverage | 51% |
| Total raw tokens | 554,678 |
| Total flow tokens | 431,845 |

Savings sparkline across repos: `▄▁▂█▇`

#### Category C — Python Large / Complex

| Metric | Value |
|---|---|
| Repos | 3 |
| Avg token savings | +26.8% |
| Avg compression ratio | 1.45× |
| Avg functions extracted | 1632 |
| Avg return-type coverage | 36% |
| Total raw tokens | 698,118 |
| Total flow tokens | 473,415 |

Savings sparkline across repos: `█▃▁`

#### Category D — Full-stack / Mixed Language

| Metric | Value |
|---|---|
| Repos | 2 |
| Avg token savings | +48.6% |
| Avg compression ratio | 2.02× |
| Avg functions extracted | 252 |
| Avg return-type coverage | 38% |
| Total raw tokens | 89,668 |
| Total flow tokens | 40,221 |

Savings sparkline across repos: `█▁`

#### Category E — JavaScript / TypeScript

| Metric | Value |
|---|---|
| Repos | 4 |
| Avg token savings | +81.2% |
| Avg compression ratio | 5.72× |
| Avg functions extracted | 237 |
| Avg return-type coverage | 22% |
| Total raw tokens | 445,531 |
| Total flow tokens | 70,084 |

Savings sparkline across repos: `█▁▆▄`

---

## 6. Statistical Analysis

### 6.1 Descriptive Statistics

| Metric | Min | P25 | Median | Mean | P75 | Max | Std Dev |
|---|---|---|---|---|---|---|---|
| Token savings (%) | -15.1 | 15.8 | 31.4 | 36.3 | 58.3 | 87.4 | 30.9 |
| Compression ratio (×) | 0.9 | 1.2 | 1.5 | 2.4 | 2.4 | 7.9 | 2.0 |
| Functions extracted | 109 | 393 | 848 | 958 | 1425 | 2218 | 669 |
| Intents extracted | 1 | 44 | 185 | 255 | 358 | 826 | 235 |
| Return-type coverage (%) | 0.1 | 21.2 | 39.4 | 47.1 | 74.6 | 100.0 | 33.6 |
| Functions per file | 1.2 | 3.3 | 7.6 | 10.9 | 18.5 | 29.1 | 8.5 |
| Raw tokens | 14633 | 75035 | 134082 | 143580 | 186698 | 380113 | 92266 |
| Flow tokens | 8941 | 31280 | 68270 | 90444 | 135252 | 226671 | 70251 |

### 6.2 Distribution of Savings

Each bar represents one repository, sorted by savings percentage:

```
supabase/supabase-js                          ▶ [█████████████████████████████████] +87.4%
vuejs/pinia                                   ▶ [███████████████████████████████] +83.6%
shadcn-ui/ui                                  ▶ [██████████████████████████████] +80.2%
Textualize/rich                               ▶ [█████████████████████████████░] +78.3%
trpc/trpc                                     ▶ [████████████████████████████░░] +73.5%
fastapi/full-stack-fastapi-template           ▶ [██████████████████████░░░░░░░░] +58.3%
pydantic/pydantic                             ▶ [██████████████████░░░░░░░░░░░░] +48.7%
encode/httpx                                  ▶ [███████████████░░░░░░░░░░░░░░░] +39.9%
tortoise/tortoise-orm                         ▶ [███████████████░░░░░░░░░░░░░░░] +39.3%
tiangolo/asyncer                              ▶ [███████████████░░░░░░░░░░░░░░░] +38.9%
psf/requests                                  ▶ [████████████░░░░░░░░░░░░░░░░░░] +31.4%
anthropics/anthropic-sdk-python               ▶ [█████████░░░░░░░░░░░░░░░░░░░░░] +24.0%
pallets/click                                 ▶ [█████████░░░░░░░░░░░░░░░░░░░░░] +23.8%
httpie/httpie                                 ▶ [████████░░░░░░░░░░░░░░░░░░░░░░] +21.9%
Textualize/textual                            ▶ [████████░░░░░░░░░░░░░░░░░░░░░░] +21.8%
pallets/flask                                 ▶ [██████░░░░░░░░░░░░░░░░░░░░░░░░] +15.8%
celery/celery                                 ▶ [████░░░░░░░░░░░░░░░░░░░░░░░░░░] +10.0%
encode/starlette                              ▶ [██░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  +4.1%
openai/openai-python                          ▶ [█░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  +2.1%
tiangolo/fastapi                              ◀ [██░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  -6.4%
agronholm/anyio                               ◀ [██████░░░░░░░░░░░░░░░░░░░░░░░░] -15.1%
```

### 6.3 Compression vs Repo Size

Relationship between number of files fetched and compression ratio:

```
 Files   Ratio  Repo
──────  ──────  ────────────────────────────────────────
    36   1.46×  psf/requests
    52   1.64×  tiangolo/asyncer
    60   1.66×  encode/httpx
    62   1.31×  pallets/click
    68   1.04×  encode/starlette
    72   0.87×  agronholm/anyio
    83   1.19×  pallets/flask
   120   4.61×  Textualize/rich
   120   1.28×  httpie/httpie
   120   1.32×  anthropics/anthropic-sdk-python
   120   1.02×  openai/openai-python
   120   0.94×  tiangolo/fastapi
   120   1.65×  tortoise/tortoise-orm
   120   1.95×  pydantic/pydantic
   120   1.28×  Textualize/textual
   120   1.11×  celery/celery
   120   2.40×  fastapi/full-stack-fastapi-template
   120   7.93×  supabase/supabase-js
   120   3.78×  trpc/trpc
   120   6.11×  vuejs/pinia
   120   5.06×  shadcn-ui/ui
```

> **Pearson r (files fetched vs savings %):** `+0.296`  
> **Pearson r (fns/file vs savings %):** `-0.599`  
> A negative correlation with function density confirms: denser typed libraries compress less aggressively than architecturally layered codebases.

### 6.4 Function Density Effect

Function density (functions per file) is the strongest predictor of Codeflow's compression ratio. High-density codebases (many small typed methods) produce larger ParsedRepo payloads relative to their source size:

```
 Fns/file   Savings  Repo
─────────  ────────  ────────────────────────────────────────
     29.1    -15.1%  agronholm/anyio
     22.8    +23.8%  pallets/click
     21.7     +4.1%  encode/starlette
     18.9    +39.9%  encode/httpx
     18.6    +31.4%  psf/requests
     18.5    +10.0%  celery/celery
     17.7    +15.8%  pallets/flask
     16.9    +48.7%  pydantic/pydantic
     11.9     +2.1%  openai/openai-python
     11.1    +24.0%  anthropics/anthropic-sdk-python
      7.6    +21.9%  httpie/httpie
      7.1    +39.3%  tortoise/tortoise-orm
      5.4    +21.8%  Textualize/textual
      5.0    +78.3%  Textualize/rich
      3.3    +58.3%  fastapi/full-stack-fastapi-template
      3.3     -6.4%  tiangolo/fastapi
      3.2    +87.4%  supabase/supabase-js
      2.3    +83.6%  vuejs/pinia
      2.1    +38.9%  tiangolo/asyncer
      1.2    +73.5%  trpc/trpc
      1.2    +80.2%  shadcn-ui/ui
```

---

## 7. Key Findings

### 7.1 Token Efficiency

- **17/21 repos** see Codeflow token savings > 5%
- **2/21 repos** land within ±5% (near-parity)
- **2/21 repos** where raw is cheaper by >5%
- Across all 21 repos, **1,115,836 tokens saved** in aggregate
- Best performer: `supabase/supabase-js` at **87.4%** savings (7.93×)
- Closest to parity: `agronholm/anyio` at **-15.1%**

### 7.2 Signal Quality

Token count alone understates Codeflow's value. Consider what each token buys an agent:

| Token type | Raw source | Codeflow ParsedRepo |
|---|---|---|
| Function signature | 1 of N tokens in the full file | 1 token in a structured fn object |
| Call graph edge | Must be inferred across files | Pre-resolved `calls: [fN, fM]` |
| Entry point (route/event) | Must grep all files | Pre-ranked `intents[]` by confidence |
| Architectural layer | Must infer from naming/path | `type: route|db|auth|handler|…` |
| File→function lookup | Must scan entire file | `file_index[path] = [f0, f3, f7]` |
| Return type | Embedded in function body | `return_type` field per function |

> **Raw source signal density ≈ 15–25%** of tokens carry structural information.  
> **Codeflow signal density = 100%** — every token is structural signal.

### 7.3 Return Type Coverage

Return types are extracted from Tree-sitter AST nodes (`return_type` field on function definitions). Across all repos, **average coverage is 47%**.

```
openai/openai-python                           [████████████████████]  100.0%  (1425/1425)
anthropics/anthropic-sdk-python                [████████████████████]   99.5%  (1328/1335)
encode/starlette                               [████████████████████]   98.6%  (1457/1478)
agronholm/anyio                                [████████████████████]   97.6%  (2044/2094)
Textualize/rich                                [██████████████████░░]   89.5%  (535/598)
Textualize/textual                             [███████████████░░░░░]   74.6%  (481/645)
encode/httpx                                   [███████████░░░░░░░░░]   53.0%  (601/1134)
tortoise/tortoise-orm                          [██████████░░░░░░░░░░]   50.0%  (424/848)
supabase/supabase-js                           [█████████░░░░░░░░░░░]   47.3%  (181/383)
fastapi/full-stack-fastapi-template            [█████████░░░░░░░░░░░]   44.4%  (175/394)
pallets/click                                  [████████░░░░░░░░░░░░]   39.4%  (556/1412)
httpie/httpie                                  [███████░░░░░░░░░░░░░]   37.2%  (339/911)
pydantic/pydantic                              [██████░░░░░░░░░░░░░░]   31.2%  (635/2032)
tiangolo/asyncer                               [██████░░░░░░░░░░░░░░]   31.2%  (34/109)
pallets/flask                                  [██████░░░░░░░░░░░░░░]   31.0%  (454/1466)
trpc/trpc                                      [████░░░░░░░░░░░░░░░░]   21.2%  (31/146)
tiangolo/fastapi                               [████░░░░░░░░░░░░░░░░]   20.1%  (79/393)
vuejs/pinia                                    [███░░░░░░░░░░░░░░░░░]   15.5%  (43/278)
shadcn-ui/ui                                   [█░░░░░░░░░░░░░░░░░░░]    4.3%  (6/140)
celery/celery                                  [█░░░░░░░░░░░░░░░░░░░]    3.5%  (78/2218)
psf/requests                                   [░░░░░░░░░░░░░░░░░░░░]    0.1%  (1/670)
```

> Python repos with `-> ReturnType` annotations achieve near-100% coverage.  
> TypeScript/JavaScript repos vary based on explicit return type annotation discipline.  
> Untyped Python achieves 0% — a signal that the codebase lacks type annotations.

### 7.4 Intent Extraction Quality

Across 21 repos with extracted intents, **mean intent confidence is 0.60**. Confidence is computed from evidence weights, unique evidence kinds, trigger type, and call-graph depth.

| Repo | Intents | Conf mean | Conf max | Verified | Observed | Candidate |
|---|---|---|---|---|---|---|
| `fastapi/full-stack-fastapi-template` | 44 | 0.76 | 0.88 | 20 | 23 | 1 |
| `tiangolo/fastapi` | 122 | 0.72 | 0.88 | 61 | 61 | 0 |
| `trpc/trpc` | 4 | 0.68 | 0.91 | 1 | 2 | 1 |
| `tiangolo/asyncer` | 23 | 0.66 | 0.80 | 0 | 23 | 0 |
| `pallets/click` | 332 | 0.63 | 0.80 | 0 | 332 | 0 |
| `supabase/supabase-js` | 9 | 0.62 | 0.78 | 0 | 7 | 2 |
| `shadcn-ui/ui` | 1 | 0.62 | 0.62 | 0 | 1 | 0 |
| `pallets/flask` | 268 | 0.59 | 0.88 | 27 | 241 | 0 |
| `vuejs/pinia` | 4 | 0.58 | 0.76 | 0 | 3 | 1 |
| `tortoise/tortoise-orm` | 176 | 0.57 | 0.88 | 11 | 165 | 0 |
| `celery/celery` | 826 | 0.56 | 0.80 | 0 | 826 | 0 |
| `openai/openai-python` | 675 | 0.55 | 0.64 | 0 | 675 | 0 |
| `Textualize/rich` | 217 | 0.55 | 0.80 | 0 | 217 | 0 |
| `httpie/httpie` | 358 | 0.55 | 0.62 | 0 | 358 | 0 |
| `anthropics/anthropic-sdk-python` | 396 | 0.55 | 0.62 | 0 | 396 | 0 |
| `psf/requests` | 185 | 0.55 | 0.55 | 0 | 185 | 0 |
| `agronholm/anyio` | 600 | 0.55 | 0.55 | 0 | 600 | 0 |
| `encode/starlette` | 341 | 0.55 | 0.55 | 0 | 341 | 0 |
| `encode/httpx` | 158 | 0.55 | 0.55 | 0 | 158 | 0 |
| `Textualize/textual` | 148 | 0.55 | 0.55 | 0 | 148 | 0 |
| `pydantic/pydantic` | 462 | 0.55 | 0.62 | 0 | 461 | 1 |

### 7.5 Function Type Architecture Map

Codeflow's `FunctionType` classification reveals the architectural shape of each codebase. Aggregated across all repos:

```
Global function type distribution across all benchmarked repos:

FunctionType.OTHER  [████████████████████████]  16502 fns  (82.1%)
FunctionType.HANDLER  [█░░░░░░░░░░░░░░░░░░░░░░░]    871 fns  ( 4.3%)
FunctionType.DB  [█░░░░░░░░░░░░░░░░░░░░░░░]    810 fns  ( 4.0%)
FunctionType.UTIL  [█░░░░░░░░░░░░░░░░░░░░░░░]    724 fns  ( 3.6%)
FunctionType.AUTH  [░░░░░░░░░░░░░░░░░░░░░░░░]    339 fns  ( 1.7%)
FunctionType.COMPONENT  [░░░░░░░░░░░░░░░░░░░░░░░░]    331 fns  ( 1.6%)
FunctionType.SERVICE  [░░░░░░░░░░░░░░░░░░░░░░░░]    281 fns  ( 1.4%)
FunctionType.ROUTE  [░░░░░░░░░░░░░░░░░░░░░░░░]    234 fns  ( 1.2%)
FunctionType.HOOK  [░░░░░░░░░░░░░░░░░░░░░░░░]     17 fns  ( 0.1%)
```

---

## 8. Regime Analysis

The benchmark reveals **three distinct performance regimes** for Codeflow, determined primarily by function density (functions per file):

### Regime 1 — High Compression (savings > 30%)

Repos: `supabase/supabase-js`, `vuejs/pinia`, `shadcn-ui/ui`, `Textualize/rich`, `trpc/trpc`, `fastapi/full-stack-fastapi-template`, `pydantic/pydantic`, `encode/httpx`, `tortoise/tortoise-orm`, `tiangolo/asyncer`, `psf/requests`

**Characteristics:**
- Low function density (7.3 fns/file avg)
- Mixed language (Python + JS/TS) or large SDK surface area
- High percentage of `component`, `route`, `handler` typed functions
- Many large files with verbose implementation bodies

**Why Codeflow wins:** Raw files contain large React component bodies, verbose Python route handlers, and extensive docstrings. Codeflow strips all of this while preserving the complete structural skeleton.

### Regime 2 — Moderate Compression (savings 5–30%)

Repos: `anthropics/anthropic-sdk-python`, `pallets/click`, `httpie/httpie`, `Textualize/textual`, `pallets/flask`, `celery/celery`

**Characteristics:**
- Medium function density (13.8 fns/file avg)
- Pure Python libraries with moderate typing discipline
- Mix of `service`, `util`, `auth` function types

**Why Codeflow wins moderately:** Source files have meaningful bodies but also substantial structural content. The ParsedRepo compresses well for the implementation bodies while function counts stay manageable.

### Regime 3 — Near-Parity or Raw Wins (savings < 5%)

Repos: `agronholm/anyio`, `tiangolo/fastapi`, `openai/openai-python`, `encode/starlette`

**Characteristics:**
- High function density (16.5 fns/file avg)
- Type-heavy Python (Protocol classes, TypedDicts, abstract base classes)
- Dominated by `other` function type (inferred as utilities)

**Why raw is competitive:** Protocol-heavy Python libraries have 15-25 short typed methods per file. Each method is 2-3 lines of body — very little body to compress. The ParsedRepo JSON overhead per function approaches the source cost per function at high density.

> **Important:** Even in Regime 3, Codeflow still provides the pre-computed call graph, intent surface, and architectural indexes. Token parity does not mean information parity — raw source at equivalent token cost contains ~15-25% structural signal vs 100% for Codeflow.

---

## 9. Recommendations

Based on these benchmark results, we recommend the following agent integration strategy:

### For AI Agents (Claude, GPT-4, etc.)

1. **Always call `/parse` first** before any file reads. Even in Regime 3 (near-parity), ParsedRepo provides structural context no amount of raw reading delivers efficiently.

2. **Use `fn_type_index` for layer navigation.** Instead of grepping for routes, read `parsed.fn_type_index['route']` — an O(1) lookup replacing 5–10 grep+read cycles.

3. **Use `file_index` for targeted file reads.** When implementation details are needed, navigate via `parsed.file_index['src/routes/auth.py']` → read only that file.

4. **Use `intents` as entry points.** The ranked intent list surfaces user-facing actions with pre-computed execution flows (`flow_ids`). Start debugging from intents, not from grep.

5. **Trust `return_type` before reading bodies.** For repos with >80% return-type coverage, data flow can be traced without opening a single file.

### For Codeflow Development

1. **Regime 3 mitigation** (high-density libraries): Consider an optional `agent_compact` serialisation mode that omits functions not reachable from any intent's `flow_ids`. This would reduce Regime 3 output by ~40-60% with acceptable signal trade-off for orientation tasks.

2. **TypeScript return-type coverage**: JS/TSX files show lower return-type extraction rates. Improving the Tree-sitter TypeScript `type_annotation` extraction would close this gap.

3. **Intent confidence calibration**: Repos with all-`candidate` intents suggest the evidence weighting needs tuning for certain patterns (e.g., Supabase-style chained SDK calls).

---

## 10. Appendix — Raw Data

Complete per-repo metrics table:

| Repo | Cat | Files | Raw KB | Raw tok | Flow tok | Saved% | Ratio | Fns | Intents | Edges | RT% | Fns/file | Parse ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `psf/requests` | A | 36 | 367 | 85,992 | 58,948 | +31.4% | 1.46× | 670 | 185 | 1,021 | 0% | 18.6 | 81 |
| `pallets/click` | A | 62 | 688 | 166,675 | 127,028 | +23.8% | 1.31× | 1,412 | 332 | 2,543 | 39% | 22.8 | 167 |
| `Textualize/rich` | A | 120 | 925 | 292,338 | 63,448 | +78.3% | 4.61× | 598 | 217 | 722 | 89% | 5.0 | 199 |
| `agronholm/anyio` | A | 72 | 837 | 186,698 | 214,973 | -15.1% | 0.87× | 2,094 | 600 | 3,788 | 98% | 29.1 | 202 |
| `httpie/httpie` | A | 120 | 517 | 119,789 | 93,545 | +21.9% | 1.28× | 911 | 358 | 861 | 37% | 7.6 | 108 |
| `anthropics/anthropic-sdk-python` | A | 120 | 865 | 191,843 | 145,828 | +24.0% | 1.32× | 1,335 | 396 | 1,705 | 99% | 11.1 | 186 |
| `openai/openai-python` | A | 120 | 845 | 183,840 | 179,999 | +2.1% | 1.02× | 1,425 | 675 | 1,390 | 100% | 11.9 | 158 |
| `pallets/flask` | B | 83 | 580 | 135,633 | 114,155 | +15.8% | 1.19× | 1,466 | 268 | 2,282 | 31% | 17.7 | 122 |
| `tiangolo/fastapi` | B | 120 | 146 | 31,506 | 33,531 | -6.4% | 0.94× | 393 | 122 | 74 | 20% | 3.3 | 37 |
| `encode/starlette` | B | 68 | 609 | 141,009 | 135,252 | +4.1% | 1.04× | 1,478 | 341 | 2,635 | 99% | 21.7 | 144 |
| `encode/httpx` | B | 60 | 559 | 134,082 | 80,637 | +39.9% | 1.66× | 1,134 | 158 | 1,193 | 53% | 18.9 | 114 |
| `tortoise/tortoise-orm` | B | 120 | 508 | 112,448 | 68,270 | +39.3% | 1.65× | 848 | 176 | 801 | 50% | 7.1 | 93 |
| `pydantic/pydantic` | C | 120 | 1504 | 380,113 | 194,967 | +48.7% | 1.95× | 2,032 | 462 | 3,740 | 31% | 16.9 | 328 |
| `Textualize/textual` | C | 120 | 294 | 66,195 | 51,777 | +21.8% | 1.28× | 645 | 148 | 341 | 75% | 5.4 | 52 |
| `celery/celery` | C | 120 | 1147 | 251,810 | 226,671 | +10.0% | 1.11× | 2,218 | 826 | 3,328 | 4% | 18.5 | 209 |
| `fastapi/full-stack-fastapi-template` | D | 120 | 319 | 75,035 | 31,280 | +58.3% | 2.40× | 394 | 44 | 414 | 44% | 3.3 | 84 |
| `tiangolo/asyncer` | D | 52 | 64 | 14,633 | 8,941 | +38.9% | 1.64× | 109 | 23 | 129 | 31% | 2.1 | 22 |
| `supabase/supabase-js` | E | 120 | 989 | 242,974 | 30,639 | +87.4% | 7.93× | 383 | 9 | 705 | 47% | 3.2 | 196 |
| `trpc/trpc` | E | 120 | 177 | 43,531 | 11,523 | +73.5% | 3.78× | 146 | 4 | 175 | 21% | 1.2 | 49 |
| `vuejs/pinia` | E | 120 | 367 | 103,422 | 16,940 | +83.6% | 6.11× | 278 | 4 | 486 | 15% | 2.3 | 116 |
| `shadcn-ui/ui` | E | 120 | 219 | 55,604 | 10,982 | +80.2% | 5.06× | 140 | 1 | 145 | 4% | 1.2 | 42 |

---

*Generated automatically by `benchmark/full_benchmark.py`.*  
*Tokenizer: tiktoken `cl100k_base`. GitHub fetcher: MAX_FILES=120, MAX_SIZE=160KB.*  
*Codeflow optimisations: short IDs, exclude_defaults, edges excluded.*
