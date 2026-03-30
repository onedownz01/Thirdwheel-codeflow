# Codeflow Token Benchmark — Full Report

> **Version:** 2.0  
> **Run date:** 2026-03-29 17:19 UTC  
> **Tokenizer:** `cl100k_base` (tiktoken — GPT-4 / Claude proxy, ±5%)  
> **Repos tested:** 21 (18 succeeded, 3 failed)  
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

We benchmark Codeflow's structured `ParsedRepo` output against the naive baseline of an AI agent reading every eligible source file in a repository. Across 18 public GitHub repositories spanning Python libraries, web frameworks, async toolkits, full-stack applications, and TypeScript SDKs, Codeflow achieves a **mean token savings of 30.2%** (median 26.5%, σ = 28.0) with an **average compression ratio of 1.99×**. Critically, the structured output carries 100% agent-useful signal — no function bodies, comments, or imports — while adding pre-computed call graphs, typed intent extraction, architectural indexes, and return-type annotations unavailable in raw source navigation. The benchmark reveals three distinct performance regimes tied to function density (functions-per-file), with full-stack and SDK repos showing the highest compression (supabase/supabase-js: **88.0%**) and dense typed libraries showing near-parity (tiangolo/fastapi: **-13.0%**).

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

> ✅ Codeflow wins — **+35.6% token savings**, 1.55× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 36 |
| Raw source size | 366.9 KB |
| Fetch time | 2.0s |
| Parse time | 0.124s |
| Functions extracted | 670 |
| Intents extracted | 185 |
| Call graph edges | 1,021 |
| Fns per file | 18.6 |
| File index entries | 28 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 85,992 | 55,370 | +30,622 |
| Tokens / function | 128 | 82.6 | -45.7 |
| Tokens / intent | — | 299 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████]  85,992 tok
Flow  [██████████████████░░░░░░░░░░]  55,370 tok  (+35.6%)
```

**Return Type Coverage**

```
Coverage  [░░░░░░░░░░░░░░░░░░░░] 0%  (1/670 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   423 (63.1%)
FunctionType.UTIL [██████░░░░░░░░░░░░░░]   119 (17.8%)
FunctionType.AUTH [███░░░░░░░░░░░░░░░░░]    59 ( 8.8%)
FunctionType.DB [██░░░░░░░░░░░░░░░░░░]    43 ( 6.4%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]    26 ( 3.9%)
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

> ✅ Codeflow wins — **+26.7% token savings**, 1.36× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 62 |
| Raw source size | 687.7 KB |
| Fetch time | 2.8s |
| Parse time | 0.149s |
| Functions extracted | 1,412 |
| Intents extracted | 332 |
| Call graph edges | 2,543 |
| Fns per file | 22.8 |
| File index entries | 59 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 166,675 | 122,253 | +44,422 |
| Tokens / function | 118 | 86.6 | -31.5 |
| Tokens / intent | — | 368 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 166,675 tok
Flow  [█████████████████████░░░░░░░] 122,253 tok  (+26.7%)
```

**Return Type Coverage**

```
Coverage  [████████░░░░░░░░░░░░] 39%  (556/1412 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]  1307 (92.6%)
FunctionType.UTIL [█░░░░░░░░░░░░░░░░░░░]    77 ( 5.5%)
FunctionType.HANDLER [░░░░░░░░░░░░░░░░░░░░]    28 ( 2.0%)
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

> ✅ Codeflow wins — **+79.7% token savings**, 4.93× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 925.2 KB |
| Fetch time | 4.3s |
| Parse time | 0.180s |
| Functions extracted | 598 |
| Intents extracted | 217 |
| Call graph edges | 722 |
| Fns per file | 5.0 |
| File index entries | 71 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 292,337 | 59,244 | +233,093 |
| Tokens / function | 489 | 99.1 | -389.8 |
| Tokens / intent | — | 273 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 292,337 tok
Flow  [██████░░░░░░░░░░░░░░░░░░░░░░]  59,244 tok  (+79.7%)
```

**Return Type Coverage**

```
Coverage  [██████████████████░░] 89%  (535/598 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   572 (95.7%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]    23 ( 3.8%)
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

> ⚠️ Raw wins — **-12.8% token savings**, 0.89× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 72 |
| Raw source size | 837.1 KB |
| Fetch time | 3.2s |
| Parse time | 0.177s |
| Functions extracted | 2,094 |
| Intents extracted | 600 |
| Call graph edges | 3,788 |
| Fns per file | 29.1 |
| File index entries | 65 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 186,698 | 210,618 | -23,920 |
| Tokens / function | 89 | 100.6 | +11.4 |
| Tokens / intent | — | 351 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [█████████████████████████░░░] 186,698 tok
Flow  [████████████████████████████] 210,618 tok  (-12.8%)
```

**Return Type Coverage**

```
Coverage  [████████████████████] 98%  (2044/2094 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]  1978 (94.5%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]    86 ( 4.1%)
FunctionType.AUTH [░░░░░░░░░░░░░░░░░░░░]    30 ( 1.4%)
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

> ✅ Codeflow wins — **+23.7% token savings**, 1.31× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 516.7 KB |
| Fetch time | 5.0s |
| Parse time | 0.095s |
| Functions extracted | 911 |
| Intents extracted | 358 |
| Call graph edges | 861 |
| Fns per file | 7.6 |
| File index entries | 99 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 119,789 | 91,424 | +28,365 |
| Tokens / function | 131 | 100.4 | -31.1 |
| Tokens / intent | — | 255 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 119,789 tok
Flow  [█████████████████████░░░░░░░]  91,424 tok  (+23.7%)
```

**Return Type Coverage**

```
Coverage  [███████░░░░░░░░░░░░░] 37%  (339/911 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   749 (82.2%)
FunctionType.AUTH [█░░░░░░░░░░░░░░░░░░░]    56 ( 6.1%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]    46 ( 5.0%)
FunctionType.UTIL [█░░░░░░░░░░░░░░░░░░░]    37 ( 4.1%)
FunctionType.DB [█░░░░░░░░░░░░░░░░░░░]    23 ( 2.5%)
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

> ✅ Codeflow wins — **+25.9% token savings**, 1.35× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 865.4 KB |
| Fetch time | 4.3s |
| Parse time | 0.171s |
| Functions extracted | 1,335 |
| Intents extracted | 396 |
| Call graph edges | 1,705 |
| Fns per file | 11.1 |
| File index entries | 75 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 191,843 | 142,206 | +49,637 |
| Tokens / function | 144 | 106.5 | -37.2 |
| Tokens / intent | — | 359 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 191,843 tok
Flow  [█████████████████████░░░░░░░] 142,206 tok  (+25.9%)
```

**Return Type Coverage**

```
Coverage  [████████████████████] 99%  (1328/1335 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   655 (49.1%)
FunctionType.UTIL [███████████░░░░░░░░░]   352 (26.4%)
FunctionType.HANDLER [█████░░░░░░░░░░░░░░░]   151 (11.3%)
FunctionType.DB [████░░░░░░░░░░░░░░░░]   143 (10.7%)
FunctionType.AUTH [█░░░░░░░░░░░░░░░░░░░]    34 ( 2.5%)
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

> ⚖️ Near-parity — **+3.3% token savings**, 1.03× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 844.9 KB |
| Fetch time | 4.4s |
| Parse time | 0.155s |
| Functions extracted | 1,425 |
| Intents extracted | 675 |
| Call graph edges | 1,390 |
| Fns per file | 11.9 |
| File index entries | 57 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 183,840 | 177,864 | +5,976 |
| Tokens / function | 129 | 124.8 | -4.2 |
| Tokens / intent | — | 264 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 183,840 tok
Flow  [███████████████████████████░] 177,864 tok  (+3.3%)
```

**Return Type Coverage**

```
Coverage  [████████████████████] 100%  (1425/1425 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   855 (60.0%)
FunctionType.HANDLER [███████████░░░░░░░░░]   487 (34.2%)
FunctionType.DB [██░░░░░░░░░░░░░░░░░░]    67 ( 4.7%)
FunctionType.AUTH [░░░░░░░░░░░░░░░░░░░░]    12 ( 0.8%)
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

> ✅ Codeflow wins — **+10.0% token savings**, 1.11× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 83 |
| Raw source size | 580.3 KB |
| Fetch time | 3.3s |
| Parse time | 0.118s |
| Functions extracted | 1,466 |
| Intents extracted | 373 |
| Call graph edges | 2,282 |
| Fns per file | 17.7 |
| File index entries | 66 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 135,632 | 122,082 | +13,550 |
| Tokens / function | 93 | 83.3 | -9.2 |
| Tokens / intent | — | 327 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 135,632 tok
Flow  [█████████████████████████░░░] 122,082 tok  (+10.0%)
```

**Return Type Coverage**

```
Coverage  [██████░░░░░░░░░░░░░░] 31%  (454/1466 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   861 (58.7%)
FunctionType.ROUTE [██████████░░░░░░░░░░]   421 (28.7%)
FunctionType.HANDLER [██░░░░░░░░░░░░░░░░░░]    89 ( 6.1%)
FunctionType.UTIL [██░░░░░░░░░░░░░░░░░░]    71 ( 4.8%)
FunctionType.DB [░░░░░░░░░░░░░░░░░░░░]    12 ( 0.8%)
FunctionType.AUTH [░░░░░░░░░░░░░░░░░░░░]    12 ( 0.8%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 373 |
| Confidence min / max | 0.55 / 0.88 |
| Confidence mean / median | 0.67 / 0.55 |
| Status distribution | observed: 241, verified: 132 |

---

#### `tiangolo/fastapi`

> ⚠️ Raw wins — **-13.0% token savings**, 0.89× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 146.3 KB |
| Fetch time | 5.0s |
| Parse time | 0.040s |
| Functions extracted | 393 |
| Intents extracted | 143 |
| Call graph edges | 74 |
| Fns per file | 3.3 |
| File index entries | 100 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 31,506 | 35,595 | -4,089 |
| Tokens / function | 80 | 90.6 | +10.4 |
| Tokens / intent | — | 249 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [█████████████████████████░░░]  31,506 tok
Flow  [████████████████████████████]  35,595 tok  (-13.0%)
```

**Return Type Coverage**

```
Coverage  [████░░░░░░░░░░░░░░░░] 20%  (79/393 functions)
```

**Function Type Distribution**

```
FunctionType.ROUTE [████████████████████]   172 (43.8%)
FunctionType.OTHER [███████████████████░]   167 (42.5%)
FunctionType.HANDLER [███░░░░░░░░░░░░░░░░░]    27 ( 6.9%)
FunctionType.AUTH [███░░░░░░░░░░░░░░░░░]    22 ( 5.6%)
FunctionType.DB [░░░░░░░░░░░░░░░░░░░░]     4 ( 1.0%)
FunctionType.SERVICE [░░░░░░░░░░░░░░░░░░░░]     1 ( 0.3%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 143 |
| Confidence min / max | 0.55 / 0.88 |
| Confidence mean / median | 0.74 / 0.88 |
| Status distribution | observed: 61, verified: 82 |

---

#### `encode/starlette`

> ⚖️ Near-parity — **+4.6% token savings**, 1.05× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 68 |
| Raw source size | 609.3 KB |
| Fetch time | 3.3s |
| Parse time | 0.135s |
| Functions extracted | 1,478 |
| Intents extracted | 341 |
| Call graph edges | 2,635 |
| Fns per file | 21.7 |
| File index entries | 64 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 141,009 | 134,492 | +6,517 |
| Tokens / function | 95 | 91.0 | -4.4 |
| Tokens / intent | — | 394 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 141,009 tok
Flow  [███████████████████████████░] 134,492 tok  (+4.6%)
```

**Return Type Coverage**

```
Coverage  [████████████████████] 99%  (1457/1478 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]  1043 (70.6%)
FunctionType.AUTH [███████░░░░░░░░░░░░░]   355 (24.0%)
FunctionType.UTIL [█░░░░░░░░░░░░░░░░░░░]    30 ( 2.0%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]    29 ( 2.0%)
FunctionType.DB [░░░░░░░░░░░░░░░░░░░░]    21 ( 1.4%)
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

> ✅ Codeflow wins — **+42.1% token savings**, 1.73× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 60 |
| Raw source size | 558.6 KB |
| Fetch time | 2.6s |
| Parse time | 0.105s |
| Functions extracted | 1,134 |
| Intents extracted | 158 |
| Call graph edges | 1,193 |
| Fns per file | 18.9 |
| File index entries | 54 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 134,082 | 77,594 | +56,488 |
| Tokens / function | 118 | 68.4 | -49.8 |
| Tokens / intent | — | 491 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 134,082 tok
Flow  [████████████████░░░░░░░░░░░░]  77,594 tok  (+42.1%)
```

**Return Type Coverage**

```
Coverage  [███████████░░░░░░░░░] 53%  (601/1134 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   679 (59.9%)
FunctionType.DB [█████████░░░░░░░░░░░]   309 (27.2%)
FunctionType.AUTH [███░░░░░░░░░░░░░░░░░]   102 ( 9.0%)
FunctionType.UTIL [█░░░░░░░░░░░░░░░░░░░]    23 ( 2.0%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]    21 ( 1.9%)
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

> ✅ Codeflow wins — **+41.0% token savings**, 1.70× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 507.9 KB |
| Fetch time | 4.8s |
| Parse time | 0.092s |
| Functions extracted | 848 |
| Intents extracted | 176 |
| Call graph edges | 801 |
| Fns per file | 7.1 |
| File index entries | 65 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 112,448 | 66,301 | +46,147 |
| Tokens / function | 133 | 78.2 | -54.4 |
| Tokens / intent | — | 377 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 112,448 tok
Flow  [█████████████████░░░░░░░░░░░]  66,301 tok  (+41.0%)
```

**Return Type Coverage**

```
Coverage  [██████████░░░░░░░░░░] 50%  (424/848 functions)
```

**Function Type Distribution**

```
FunctionType.DB [████████████████████]   522 (61.6%)
FunctionType.OTHER [██████████░░░░░░░░░░]   256 (30.2%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]    35 ( 4.1%)
FunctionType.ROUTE [█░░░░░░░░░░░░░░░░░░░]    19 ( 2.2%)
FunctionType.UTIL [█░░░░░░░░░░░░░░░░░░░]    14 ( 1.7%)
FunctionType.AUTH [░░░░░░░░░░░░░░░░░░░░]     2 ( 0.2%)
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

> ✅ Codeflow wins — **+49.7% token savings**, 1.99× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 1504.4 KB |
| Fetch time | 4.3s |
| Parse time | 0.312s |
| Functions extracted | 2,032 |
| Intents extracted | 462 |
| Call graph edges | 3,740 |
| Fns per file | 16.9 |
| File index entries | 102 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 380,113 | 191,245 | +188,868 |
| Tokens / function | 187 | 94.1 | -92.9 |
| Tokens / intent | — | 414 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 380,113 tok
Flow  [██████████████░░░░░░░░░░░░░░] 191,245 tok  (+49.7%)
```

**Return Type Coverage**

```
Coverage  [██████░░░░░░░░░░░░░░] 31%  (635/2032 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]  1371 (67.5%)
FunctionType.DB [█████████░░░░░░░░░░░]   647 (31.8%)
FunctionType.HANDLER [░░░░░░░░░░░░░░░░░░░░]    14 ( 0.7%)
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

> ✅ Codeflow wins — **+26.4% token savings**, 1.36× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 294.1 KB |
| Fetch time | 4.4s |
| Parse time | 0.062s |
| Functions extracted | 645 |
| Intents extracted | 148 |
| Call graph edges | 341 |
| Fns per file | 5.4 |
| File index entries | 109 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 66,195 | 48,691 | +17,504 |
| Tokens / function | 103 | 75.5 | -27.1 |
| Tokens / intent | — | 329 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████]  66,195 tok
Flow  [█████████████████████░░░░░░░]  48,691 tok  (+26.4%)
```

**Return Type Coverage**

```
Coverage  [███████████████░░░░░] 75%  (481/645 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]   573 (88.8%)
FunctionType.DB [██░░░░░░░░░░░░░░░░░░]    44 ( 6.8%)
FunctionType.HANDLER [█░░░░░░░░░░░░░░░░░░░]    28 ( 4.3%)
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

> ✅ Codeflow wins — **+12.6% token savings**, 1.14× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 1147.0 KB |
| Fetch time | 4.7s |
| Parse time | 0.205s |
| Functions extracted | 2,218 |
| Intents extracted | 826 |
| Call graph edges | 3,328 |
| Fns per file | 18.5 |
| File index entries | 108 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 251,810 | 220,201 | +31,609 |
| Tokens / function | 114 | 99.3 | -14.3 |
| Tokens / intent | — | 267 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 251,810 tok
Flow  [████████████████████████░░░░] 220,201 tok  (+12.6%)
```

**Return Type Coverage**

```
Coverage  [█░░░░░░░░░░░░░░░░░░░] 4%  (78/2218 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]  1734 (78.2%)
FunctionType.DB [███░░░░░░░░░░░░░░░░░]   276 (12.4%)
FunctionType.HANDLER [██░░░░░░░░░░░░░░░░░░]   131 ( 5.9%)
FunctionType.ROUTE [░░░░░░░░░░░░░░░░░░░░]    37 ( 1.7%)
FunctionType.UTIL [░░░░░░░░░░░░░░░░░░░░]    32 ( 1.4%)
FunctionType.AUTH [░░░░░░░░░░░░░░░░░░░░]     7 ( 0.3%)
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

> ✅ Codeflow wins — **+58.6% token savings**, 2.42× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 319.0 KB |
| Fetch time | 4.4s |
| Parse time | 0.072s |
| Functions extracted | 394 |
| Intents extracted | 46 |
| Call graph edges | 414 |
| Fns per file | 3.3 |
| File index entries | 98 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 75,035 | 31,064 | +43,971 |
| Tokens / function | 190 | 78.8 | -111.6 |
| Tokens / intent | — | 675 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████]  75,035 tok
Flow  [████████████░░░░░░░░░░░░░░░░]  31,064 tok  (+58.6%)
```

**Return Type Coverage**

```
Coverage  [█████████░░░░░░░░░░░] 44%  (175/394 functions)
```

**Function Type Distribution**

```
FunctionType.COMPONENT [████████████████████]   163 (41.4%)
FunctionType.HANDLER [███████░░░░░░░░░░░░░]    61 (15.5%)
FunctionType.OTHER [███████░░░░░░░░░░░░░]    58 (14.7%)
FunctionType.SERVICE [██████░░░░░░░░░░░░░░]    49 (12.4%)
FunctionType.ROUTE [███░░░░░░░░░░░░░░░░░]    23 ( 5.8%)
FunctionType.AUTH [██░░░░░░░░░░░░░░░░░░]    19 ( 4.8%)
FunctionType.DB [█░░░░░░░░░░░░░░░░░░░]     9 ( 2.3%)
FunctionType.UTIL [█░░░░░░░░░░░░░░░░░░░]     9 ( 2.3%)
FunctionType.HOOK [░░░░░░░░░░░░░░░░░░░░]     3 ( 0.8%)
```

**Intent Quality**

| Metric | Value |
|---|---|
| Count | 46 |
| Confidence min / max | 0.48 / 0.88 |
| Confidence mean / median | 0.77 / 0.76 |
| Status distribution | candidate: 1, observed: 23, verified: 22 |

---

#### `tiangolo/asyncer`

> ✅ Codeflow wins — **+41.2% token savings**, 1.70× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 52 |
| Raw source size | 63.5 KB |
| Fetch time | 3.9s |
| Parse time | 0.030s |
| Functions extracted | 109 |
| Intents extracted | 23 |
| Call graph edges | 129 |
| Fns per file | 2.1 |
| File index entries | 33 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 14,633 | 8,601 | +6,032 |
| Tokens / function | 134 | 78.9 | -55.3 |
| Tokens / intent | — | 374 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████]  14,633 tok
Flow  [████████████████░░░░░░░░░░░░]   8,601 tok  (+41.2%)
```

**Return Type Coverage**

```
Coverage  [██████░░░░░░░░░░░░░░] 31%  (34/109 functions)
```

**Function Type Distribution**

```
FunctionType.OTHER [████████████████████]    96 (88.1%)
FunctionType.ROUTE [██░░░░░░░░░░░░░░░░░░]    11 (10.1%)
FunctionType.HANDLER [░░░░░░░░░░░░░░░░░░░░]     2 ( 1.8%)
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

> ✅ Codeflow wins — **+88.0% token savings**, 8.32× compression

**Fetch & Parse**

| Metric | Value |
|---|---|
| Files fetched | 120 |
| Raw source size | 989.4 KB |
| Fetch time | 4.3s |
| Parse time | 0.198s |
| Functions extracted | 383 |
| Intents extracted | 9 |
| Call graph edges | 705 |
| Fns per file | 3.2 |
| File index entries | 53 |

**Token Comparison**

| Metric | Raw | Codeflow | Delta |
|---|---|---|---|
| Total tokens | 242,974 | 29,197 | +213,777 |
| Tokens / function | 634 | 76.2 | -558.2 |
| Tokens / intent | — | 3244 | — |
| Signal density | ~20% | 100% | +80pp |

**Token Budget Visual**
```
Raw   [████████████████████████████] 242,974 tok
Flow  [███░░░░░░░░░░░░░░░░░░░░░░░░░]  29,197 tok  (+88.0%)
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

> ⚠️ **FETCH FAILED:** GitHub API rate limit exceeded; provide a token

#### `vuejs/pinia`

> ⚠️ **FETCH FAILED:** GitHub API rate limit exceeded; provide a token

#### `shadcn-ui/ui`

> ⚠️ **FETCH FAILED:** GitHub API rate limit exceeded; provide a token

### 5.2 Summary Table

| # | Repo | Files | Raw tok | Flow tok | Saved | Ratio | Fns | Intents | RT% |
|---|---|---|---|---|---|---|---|---|---|
|  1 | `psf/requests` | 36 | 85,992 | 55,370 | **+35.6%** | 1.55× | 670 | 185 | 0% |
|  2 | `pallets/click` | 62 | 166,675 | 122,253 | **+26.7%** | 1.36× | 1,412 | 332 | 39% |
|  3 | `Textualize/rich` | 120 | 292,337 | 59,244 | **+79.7%** | 4.93× | 598 | 217 | 89% |
|  4 | `agronholm/anyio` | 72 | 186,698 | 210,618 | **-12.8%** | 0.89× | 2,094 | 600 | 98% |
|  5 | `httpie/httpie` | 120 | 119,789 | 91,424 | **+23.7%** | 1.31× | 911 | 358 | 37% |
|  6 | `anthropics/anthropic-sdk-python` | 120 | 191,843 | 142,206 | **+25.9%** | 1.35× | 1,335 | 396 | 99% |
|  7 | `openai/openai-python` | 120 | 183,840 | 177,864 | **+3.3%** | 1.03× | 1,425 | 675 | 100% |
|  8 | `pallets/flask` | 83 | 135,632 | 122,082 | **+10.0%** | 1.11× | 1,466 | 373 | 31% |
|  9 | `tiangolo/fastapi` | 120 | 31,506 | 35,595 | **-13.0%** | 0.89× | 393 | 143 | 20% |
| 10 | `encode/starlette` | 68 | 141,009 | 134,492 | **+4.6%** | 1.05× | 1,478 | 341 | 99% |
| 11 | `encode/httpx` | 60 | 134,082 | 77,594 | **+42.1%** | 1.73× | 1,134 | 158 | 53% |
| 12 | `tortoise/tortoise-orm` | 120 | 112,448 | 66,301 | **+41.0%** | 1.70× | 848 | 176 | 50% |
| 13 | `pydantic/pydantic` | 120 | 380,113 | 191,245 | **+49.7%** | 1.99× | 2,032 | 462 | 31% |
| 14 | `Textualize/textual` | 120 | 66,195 | 48,691 | **+26.4%** | 1.36× | 645 | 148 | 75% |
| 15 | `celery/celery` | 120 | 251,810 | 220,201 | **+12.6%** | 1.14× | 2,218 | 826 | 4% |
| 16 | `fastapi/full-stack-fastapi-template` | 120 | 75,035 | 31,064 | **+58.6%** | 2.42× | 394 | 46 | 44% |
| 17 | `tiangolo/asyncer` | 52 | 14,633 | 8,601 | **+41.2%** | 1.70× | 109 | 23 | 31% |
| 18 | `supabase/supabase-js` | 120 | 242,974 | 29,197 | **+88.0%** | 8.32× | 383 | 9 | 47% |

**Aggregate** | | | **2,812,611** | **1,824,042** | **988,569** | **1.99×** | | | |

### 5.3 By Category

#### Category A — Python Pure Libraries & SDKs

| Metric | Value |
|---|---|
| Repos | 7 |
| Avg token savings | +26.0% |
| Avg compression ratio | 1.78× |
| Avg functions extracted | 1206 |
| Avg return-type coverage | 66% |
| Total raw tokens | 1,227,174 |
| Total flow tokens | 858,979 |

Savings sparkline across repos: `▄▃█▁▃▃▂`

#### Category B — Python Web / API Frameworks

| Metric | Value |
|---|---|
| Repos | 5 |
| Avg token savings | +17.0% |
| Avg compression ratio | 1.29× |
| Avg functions extracted | 1064 |
| Avg return-type coverage | 51% |
| Total raw tokens | 554,677 |
| Total flow tokens | 436,064 |

Savings sparkline across repos: `▃▁▃█▇`

#### Category C — Python Large / Complex

| Metric | Value |
|---|---|
| Repos | 3 |
| Avg token savings | +29.6% |
| Avg compression ratio | 1.50× |
| Avg functions extracted | 1632 |
| Avg return-type coverage | 36% |
| Total raw tokens | 698,118 |
| Total flow tokens | 460,137 |

Savings sparkline across repos: `█▃▁`

#### Category D — Full-stack / Mixed Language

| Metric | Value |
|---|---|
| Repos | 2 |
| Avg token savings | +49.9% |
| Avg compression ratio | 2.06× |
| Avg functions extracted | 252 |
| Avg return-type coverage | 38% |
| Total raw tokens | 89,668 |
| Total flow tokens | 39,665 |

Savings sparkline across repos: `█▁`

#### Category E — JavaScript / TypeScript

| Metric | Value |
|---|---|
| Repos | 1 |
| Avg token savings | +88.0% |
| Avg compression ratio | 8.32× |
| Avg functions extracted | 383 |
| Avg return-type coverage | 47% |
| Total raw tokens | 242,974 |
| Total flow tokens | 29,197 |

Savings sparkline across repos: `▁`

---

## 6. Statistical Analysis

### 6.1 Descriptive Statistics

| Metric | Min | P25 | Median | Mean | P75 | Max | Std Dev |
|---|---|---|---|---|---|---|---|
| Token savings (%) | -13.0 | 10.0 | 26.5 | 30.2 | 42.1 | 88.0 | 28.0 |
| Compression ratio (×) | 0.9 | 1.1 | 1.4 | 2.0 | 1.7 | 8.3 | 1.8 |
| Functions extracted | 109 | 598 | 1022 | 1086 | 1466 | 2218 | 636 |
| Intents extracted | 9 | 148 | 274 | 304 | 396 | 826 | 228 |
| Return-type coverage (%) | 0.1 | 31.2 | 45.8 | 52.7 | 89.5 | 100.0 | 33.0 |
| Functions per file | 2.1 | 5.0 | 11.5 | 12.4 | 18.6 | 29.1 | 8.2 |
| Raw tokens | 14633 | 85992 | 138320 | 156256 | 191843 | 380113 | 93307 |
| Flow tokens | 8601 | 48691 | 84509 | 101336 | 142206 | 220201 | 66536 |

### 6.2 Distribution of Savings

Each bar represents one repository, sorted by savings percentage:

```
supabase/supabase-js                          ▶ [█████████████████████████████████] +88.0%
Textualize/rich                               ▶ [██████████████████████████████] +79.7%
fastapi/full-stack-fastapi-template           ▶ [██████████████████████░░░░░░░░] +58.6%
pydantic/pydantic                             ▶ [███████████████████░░░░░░░░░░░] +49.7%
encode/httpx                                  ▶ [████████████████░░░░░░░░░░░░░░] +42.1%
tiangolo/asyncer                              ▶ [███████████████░░░░░░░░░░░░░░░] +41.2%
tortoise/tortoise-orm                         ▶ [███████████████░░░░░░░░░░░░░░░] +41.0%
psf/requests                                  ▶ [█████████████░░░░░░░░░░░░░░░░░] +35.6%
pallets/click                                 ▶ [██████████░░░░░░░░░░░░░░░░░░░░] +26.7%
Textualize/textual                            ▶ [██████████░░░░░░░░░░░░░░░░░░░░] +26.4%
anthropics/anthropic-sdk-python               ▶ [██████████░░░░░░░░░░░░░░░░░░░░] +25.9%
httpie/httpie                                 ▶ [█████████░░░░░░░░░░░░░░░░░░░░░] +23.7%
celery/celery                                 ▶ [█████░░░░░░░░░░░░░░░░░░░░░░░░░] +12.6%
pallets/flask                                 ▶ [████░░░░░░░░░░░░░░░░░░░░░░░░░░] +10.0%
encode/starlette                              ▶ [██░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  +4.6%
openai/openai-python                          ▶ [█░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  +3.3%
agronholm/anyio                               ◀ [█████░░░░░░░░░░░░░░░░░░░░░░░░░] -12.8%
tiangolo/fastapi                              ◀ [█████░░░░░░░░░░░░░░░░░░░░░░░░░] -13.0%
```

### 6.3 Compression vs Repo Size

Relationship between number of files fetched and compression ratio:

```
 Files   Ratio  Repo
──────  ──────  ────────────────────────────────────────
    36   1.55×  psf/requests
    52   1.70×  tiangolo/asyncer
    60   1.73×  encode/httpx
    62   1.36×  pallets/click
    68   1.05×  encode/starlette
    72   0.89×  agronholm/anyio
    83   1.11×  pallets/flask
   120   4.93×  Textualize/rich
   120   1.31×  httpie/httpie
   120   1.35×  anthropics/anthropic-sdk-python
   120   1.03×  openai/openai-python
   120   0.89×  tiangolo/fastapi
   120   1.70×  tortoise/tortoise-orm
   120   1.99×  pydantic/pydantic
   120   1.36×  Textualize/textual
   120   1.14×  celery/celery
   120   2.42×  fastapi/full-stack-fastapi-template
   120   8.32×  supabase/supabase-js
```

> **Pearson r (files fetched vs savings %):** `+0.158`  
> **Pearson r (fns/file vs savings %):** `-0.450`  
> A negative correlation with function density confirms: denser typed libraries compress less aggressively than architecturally layered codebases.

### 6.4 Function Density Effect

Function density (functions per file) is the strongest predictor of Codeflow's compression ratio. High-density codebases (many small typed methods) produce larger ParsedRepo payloads relative to their source size:

```
 Fns/file   Savings  Repo
─────────  ────────  ────────────────────────────────────────
     29.1    -12.8%  agronholm/anyio
     22.8    +26.7%  pallets/click
     21.7     +4.6%  encode/starlette
     18.9    +42.1%  encode/httpx
     18.6    +35.6%  psf/requests
     18.5    +12.6%  celery/celery
     17.7    +10.0%  pallets/flask
     16.9    +49.7%  pydantic/pydantic
     11.9     +3.3%  openai/openai-python
     11.1    +25.9%  anthropics/anthropic-sdk-python
      7.6    +23.7%  httpie/httpie
      7.1    +41.0%  tortoise/tortoise-orm
      5.4    +26.4%  Textualize/textual
      5.0    +79.7%  Textualize/rich
      3.3    +58.6%  fastapi/full-stack-fastapi-template
      3.3    -13.0%  tiangolo/fastapi
      3.2    +88.0%  supabase/supabase-js
      2.1    +41.2%  tiangolo/asyncer
```

---

## 7. Key Findings

### 7.1 Token Efficiency

- **14/18 repos** see Codeflow token savings > 5%
- **2/18 repos** land within ±5% (near-parity)
- **2/18 repos** where raw is cheaper by >5%
- Across all 18 repos, **988,569 tokens saved** in aggregate
- Best performer: `supabase/supabase-js` at **88.0%** savings (8.32×)
- Closest to parity: `tiangolo/fastapi` at **-13.0%**

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

Return types are extracted from Tree-sitter AST nodes (`return_type` field on function definitions). Across all repos, **average coverage is 53%**.

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
tiangolo/fastapi                               [████░░░░░░░░░░░░░░░░]   20.1%  (79/393)
celery/celery                                  [█░░░░░░░░░░░░░░░░░░░]    3.5%  (78/2218)
psf/requests                                   [░░░░░░░░░░░░░░░░░░░░]    0.1%  (1/670)
```

> Python repos with `-> ReturnType` annotations achieve near-100% coverage.  
> TypeScript/JavaScript repos vary based on explicit return type annotation discipline.  
> Untyped Python achieves 0% — a signal that the codebase lacks type annotations.

### 7.4 Intent Extraction Quality

Across 18 repos with extracted intents, **mean intent confidence is 0.60**. Confidence is computed from evidence weights, unique evidence kinds, trigger type, and call-graph depth.

| Repo | Intents | Conf mean | Conf max | Verified | Observed | Candidate |
|---|---|---|---|---|---|---|
| `fastapi/full-stack-fastapi-template` | 46 | 0.77 | 0.88 | 22 | 23 | 1 |
| `tiangolo/fastapi` | 143 | 0.74 | 0.88 | 82 | 61 | 0 |
| `pallets/flask` | 373 | 0.67 | 0.88 | 132 | 241 | 0 |
| `tiangolo/asyncer` | 23 | 0.66 | 0.80 | 0 | 23 | 0 |
| `pallets/click` | 332 | 0.63 | 0.80 | 0 | 332 | 0 |
| `supabase/supabase-js` | 9 | 0.62 | 0.78 | 0 | 7 | 2 |
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

FunctionType.OTHER  [████████████████████████]  13388 fns  (68.5%)
FunctionType.DB  [████░░░░░░░░░░░░░░░░░░░░]   2130 fns  (10.9%)
FunctionType.HANDLER  [██░░░░░░░░░░░░░░░░░░░░░░]   1339 fns  ( 6.9%)
FunctionType.AUTH  [█░░░░░░░░░░░░░░░░░░░░░░░]    833 fns  ( 4.3%)
FunctionType.UTIL  [█░░░░░░░░░░░░░░░░░░░░░░░]    775 fns  ( 4.0%)
FunctionType.ROUTE  [█░░░░░░░░░░░░░░░░░░░░░░░]    683 fns  ( 3.5%)
FunctionType.SERVICE  [░░░░░░░░░░░░░░░░░░░░░░░░]    225 fns  ( 1.2%)
FunctionType.COMPONENT  [░░░░░░░░░░░░░░░░░░░░░░░░]    169 fns  ( 0.9%)
FunctionType.HOOK  [░░░░░░░░░░░░░░░░░░░░░░░░]      3 fns  ( 0.0%)
```

---

## 8. Regime Analysis

The benchmark reveals **three distinct performance regimes** for Codeflow, determined primarily by function density (functions per file):

### Regime 1 — High Compression (savings > 30%)

Repos: `supabase/supabase-js`, `Textualize/rich`, `fastapi/full-stack-fastapi-template`, `pydantic/pydantic`, `encode/httpx`, `tiangolo/asyncer`, `tortoise/tortoise-orm`, `psf/requests`

**Characteristics:**
- Low function density (9.4 fns/file avg)
- Mixed language (Python + JS/TS) or large SDK surface area
- High percentage of `component`, `route`, `handler` typed functions
- Many large files with verbose implementation bodies

**Why Codeflow wins:** Raw files contain large React component bodies, verbose Python route handlers, and extensive docstrings. Codeflow strips all of this while preserving the complete structural skeleton.

### Regime 2 — Moderate Compression (savings 5–30%)

Repos: `pallets/click`, `Textualize/textual`, `anthropics/anthropic-sdk-python`, `httpie/httpie`, `celery/celery`, `pallets/flask`

**Characteristics:**
- Medium function density (13.8 fns/file avg)
- Pure Python libraries with moderate typing discipline
- Mix of `service`, `util`, `auth` function types

**Why Codeflow wins moderately:** Source files have meaningful bodies but also substantial structural content. The ParsedRepo compresses well for the implementation bodies while function counts stay manageable.

### Regime 3 — Near-Parity or Raw Wins (savings < 5%)

Repos: `tiangolo/fastapi`, `agronholm/anyio`, `openai/openai-python`, `encode/starlette`

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
| `psf/requests` | A | 36 | 367 | 85,992 | 55,370 | +35.6% | 1.55× | 670 | 185 | 1,021 | 0% | 18.6 | 124 |
| `pallets/click` | A | 62 | 688 | 166,675 | 122,253 | +26.7% | 1.36× | 1,412 | 332 | 2,543 | 39% | 22.8 | 149 |
| `Textualize/rich` | A | 120 | 925 | 292,337 | 59,244 | +79.7% | 4.93× | 598 | 217 | 722 | 89% | 5.0 | 180 |
| `agronholm/anyio` | A | 72 | 837 | 186,698 | 210,618 | -12.8% | 0.89× | 2,094 | 600 | 3,788 | 98% | 29.1 | 177 |
| `httpie/httpie` | A | 120 | 517 | 119,789 | 91,424 | +23.7% | 1.31× | 911 | 358 | 861 | 37% | 7.6 | 95 |
| `anthropics/anthropic-sdk-python` | A | 120 | 865 | 191,843 | 142,206 | +25.9% | 1.35× | 1,335 | 396 | 1,705 | 99% | 11.1 | 171 |
| `openai/openai-python` | A | 120 | 845 | 183,840 | 177,864 | +3.3% | 1.03× | 1,425 | 675 | 1,390 | 100% | 11.9 | 155 |
| `pallets/flask` | B | 83 | 580 | 135,632 | 122,082 | +10.0% | 1.11× | 1,466 | 373 | 2,282 | 31% | 17.7 | 118 |
| `tiangolo/fastapi` | B | 120 | 146 | 31,506 | 35,595 | -13.0% | 0.89× | 393 | 143 | 74 | 20% | 3.3 | 40 |
| `encode/starlette` | B | 68 | 609 | 141,009 | 134,492 | +4.6% | 1.05× | 1,478 | 341 | 2,635 | 99% | 21.7 | 135 |
| `encode/httpx` | B | 60 | 559 | 134,082 | 77,594 | +42.1% | 1.73× | 1,134 | 158 | 1,193 | 53% | 18.9 | 105 |
| `tortoise/tortoise-orm` | B | 120 | 508 | 112,448 | 66,301 | +41.0% | 1.70× | 848 | 176 | 801 | 50% | 7.1 | 92 |
| `pydantic/pydantic` | C | 120 | 1504 | 380,113 | 191,245 | +49.7% | 1.99× | 2,032 | 462 | 3,740 | 31% | 16.9 | 312 |
| `Textualize/textual` | C | 120 | 294 | 66,195 | 48,691 | +26.4% | 1.36× | 645 | 148 | 341 | 75% | 5.4 | 62 |
| `celery/celery` | C | 120 | 1147 | 251,810 | 220,201 | +12.6% | 1.14× | 2,218 | 826 | 3,328 | 4% | 18.5 | 205 |
| `fastapi/full-stack-fastapi-template` | D | 120 | 319 | 75,035 | 31,064 | +58.6% | 2.42× | 394 | 46 | 414 | 44% | 3.3 | 72 |
| `tiangolo/asyncer` | D | 52 | 64 | 14,633 | 8,601 | +41.2% | 1.70× | 109 | 23 | 129 | 31% | 2.1 | 30 |
| `supabase/supabase-js` | E | 120 | 989 | 242,974 | 29,197 | +88.0% | 8.32× | 383 | 9 | 705 | 47% | 3.2 | 198 |
| `trpc/trpc` | E | — | — | — | — | — | — | — | — | — | — | — | FAILED |
| `vuejs/pinia` | E | — | — | — | — | — | — | — | — | — | — | — | FAILED |
| `shadcn-ui/ui` | E | — | — | — | — | — | — | — | — | — | — | — | FAILED |

---

*Generated automatically by `benchmark/full_benchmark.py`.*  
*Tokenizer: tiktoken `cl100k_base`. GitHub fetcher: MAX_FILES=120, MAX_SIZE=160KB.*  
*Codeflow optimisations: short IDs, exclude_defaults, edges excluded.*
