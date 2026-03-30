# Codeflow Deep Understanding Benchmark

> **Run date:** 2026-03-29 17:33 UTC  
> **Repos tested:** 3/3  
> **Question:** Does Codeflow actually understand codebases better than raw reading?  
> **Methodology:** Ground truth (ast.walk + regex) vs Manual read vs Codeflow parse

---

## 1. Executive Summary

This benchmark answers a critical question for AI agents:

> *When an agent reads raw source files vs receives a Codeflow ParsedRepo,*
> *how much does it actually understand, and at what token cost?*

Two dimensions measured:
- **Recall** — how much of the real codebase is surfaced
- **Structure** — how queryable/navigable the representation is

Key finding: Raw reading has **100% recall** but **~5% structure score**.
Codeflow has **lower recall** (bodies/comments stripped) but **95% structure score**
and dramatically lower token cost.

## 2. Overall Quality Scores

| Repo | Manual Read Score | Codeflow Score | Verdict |
|------|:-----------------:|:--------------:|---------|
| `encode/starlette` | 60.8/100 (B) | 73.4/100 (B+) | Codeflow wins |
| `encode/httpx` | 60.8/100 (B) | 81.0/100 (A) | Codeflow wins |
| `fastapi/full-stack-fastapi-template` | 60.8/100 (B) | 89.4/100 (A) | Codeflow wins |

## 3. Token Efficiency

| Repo | Raw Tokens | Codeflow Tokens | Saved | Ratio |
|------|:----------:|:---------------:|:-----:|:-----:|
| `encode/starlette` | 141,009 | 134,207 | 6,802 (4.8%) | 1.05× |
| `encode/httpx` | 134,082 | 77,605 | 56,477 (42.1%) | 1.73× |
| `fastapi/full-stack-fastapi-template` | 75,035 | 31,070 | 43,965 (58.6%) | 2.42× |

## 4. Per-Repo Deep Analysis

### 4.1 Starlette — ASGI Framework
> `encode/starlette` · Type: `library`

#### Ground Truth (from ast.walk + regex on raw source)

| Metric | Value |
|--------|------:|
| Python source files | 67 |
| JS/TS source files | 1 |
| Total source lines | 17,515 |
| **Python functions** (ast.FunctionDef) | **1474** |
| Async functions | 484 |
| Classes | 182 |
| Return-annotated functions | 1457 |
| Total parameters | 2,595 |
| Typed parameters | 2,070 |
| **HTTP routes** (decorator regex) | **0** |
| CLI commands | 0 |
| JS/TS functions | 4 |
| React components | 0 |

Sample functions found:
- `starlette/concurrency.py:14:run_until_first_complete`
- `starlette/concurrency.py:30:run_in_threadpool`
- `starlette/concurrency.py:39:_next`
- `starlette/concurrency.py:49:iterate_in_threadpool`
- `starlette/concurrency.py:22:run`

#### Manual Read vs Codeflow — Dimension by Dimension

```
Dimension                       Manual Read       Codeflow     Winner
──────────────────────────── ────────────── ────────────── ──────────
  Function recall                    100.0%         100.0%      tie  
  Intent/route recall                100.0%          50.0%   ← Manual
  Return type recall                 100.0%         100.0%      tie  
  Param coverage                     100.0%          80.0%   ← Manual
  Call graph                           0.0%          20.9% Codeflow →
  Structure/index                      5.0%          95.0% Codeflow →
  Lookup efficiency                    0.0%          80.0% Codeflow →
──────────────────────────── ────────────── ────────────── ──────────
  OVERALL                             60.8%          73.4% Codeflow →
```

#### Score Breakdown (Visual)

```
  Dimension            Manual Read             Codeflow
  ─────────────────── ─────────────────────── ───────────────────────
  Function recall     ██████████████████████ ██████████████████████
                      100.0%                  100.0%
  Intent/route recall ██████████████████████ ███████████░░░░░░░░░░░
                      100.0%                   50.0%
  Return type recall  ██████████████████████ ██████████████████████
                      100.0%                  100.0%
  Param coverage      ██████████████████████ ██████████████████░░░░
                      100.0%                   80.0%
  Call graph          ░░░░░░░░░░░░░░░░░░░░░░ █████░░░░░░░░░░░░░░░░░
                        0.0%                   20.9%
  Structure/index     █░░░░░░░░░░░░░░░░░░░░░ █████████████████████░
                        5.0%                   95.0%
  Lookup efficiency   ░░░░░░░░░░░░░░░░░░░░░░ ██████████████████░░░░
                        0.0%                   80.0%
```

#### Codeflow Parse Details

| Metric | Value |
|--------|------:|
| Functions extracted | 1478 / 1478 total |
| Function recall | 100.0% |
| Intents extracted | 341 |
| Route recall | 50.0% |
| Edges (call graph) | 2,635 |
| Return types captured | 1457 / 1457 annotated |
| Parameters captured | 2076 / 2595 total |
| Typed params captured | 2069 |
| Files indexed | 64 |
| fn_type_index buckets | {<FunctionType.OTHER: 'other'>: 1043, <FunctionType.HANDLER: 'handler'>: 29, <FunctionType.UTIL: 'util'>: 30, <FunctionType.AUTH: 'auth'>: 355, <FunctionType.DB: 'db'>: 21} |
| Parse time | 0.19s |
| Longest call chain depth | 3 hops |
| Call chain example | `main → showRandomAnnouncement → shuffle` |

#### Lookup Cost Comparison

How many tokens does the agent need to read to answer each question?

| Query | Manual Read | Codeflow | Speedup |
|-------|:-----------:|:--------:|:-------:|
| "List all HTTP routes" | 141,009 tok | 0 tok | **∞** |
| "Find function signature" | 2,073 tok | 48 tok | **43×** |
| "What does this file export?" | 141,009 tok | 31 tok | **4548×** |

#### What Codeflow Does NOT Capture

- **Function bodies** — 1474 functions have their implementation stripped (by design: reduces noise)
- **Comments & docstrings** — documentation not passed to agent
- **Import graph** — module-level imports not tracked per-function
- **Runtime values** — no data flow, no type inference beyond annotations

#### What Codeflow UNIQUELY Provides

- **Structured call graph** — 2,635 edges, traversable in O(1) vs O(n) file scan
- **fn_type_index** — instant lookup by function type: {<FunctionType.OTHER: 'other'>: 1043, <FunctionType.HANDLER: 'handler'>: 29, <FunctionType.UTIL: 'util'>: 30, <FunctionType.AUTH: 'auth'>: 355, <FunctionType.DB: 'db'>: 21}
- **file_index** — 64 files mapped to their function IDs
- **Intent grouping** — 341 entry points with confidence + evidence
- **Compressed representation** — 134,207 tokens vs 141,009 raw (4.8% smaller)
- **Pre-traced call chains** — deepest chain: 3 hops (main → showRandomAnnouncement → shuffle...)
- **Rich intent objects** — e.g. `WebSocketTestSession.send() | trigger=api:WebSocketTestSession.send | confidence=0.55 | flow_hops=1`

---

### 4.2 HTTPX — Python HTTP Client
> `encode/httpx` · Type: `library+cli`

#### Ground Truth (from ast.walk + regex on raw source)

| Metric | Value |
|--------|------:|
| Python source files | 60 |
| JS/TS source files | 0 |
| Total source lines | 17,753 |
| **Python functions** (ast.FunctionDef) | **1134** |
| Async functions | 212 |
| Classes | 107 |
| Return-annotated functions | 601 |
| Total parameters | 1,537 |
| Typed parameters | 928 |
| **HTTP routes** (decorator regex) | **0** |
| CLI commands | 1 |
| JS/TS functions | 0 |
| React components | 0 |

Sample functions found:
- `httpx/_main.py:26:print_help`
- `httpx/_main.py:103:get_lexer_for_response`
- `httpx/_main.py:116:format_request_headers`
- `httpx/_main.py:129:format_response_headers`
- `httpx/_main.py:147:print_request_headers`

#### Manual Read vs Codeflow — Dimension by Dimension

```
Dimension                       Manual Read       Codeflow     Winner
──────────────────────────── ────────────── ────────────── ──────────
  Function recall                    100.0%         100.0%      tie  
  Intent/route recall                100.0%         100.0%      tie  
  Return type recall                 100.0%         100.0%      tie  
  Param coverage                     100.0%          59.8%   ← Manual
  Call graph                           0.0%          18.4% Codeflow →
  Structure/index                      5.0%          95.0% Codeflow →
  Lookup efficiency                    0.0%          80.0% Codeflow →
──────────────────────────── ────────────── ────────────── ──────────
  OVERALL                             60.8%          81.0% Codeflow →
```

#### Score Breakdown (Visual)

```
  Dimension            Manual Read             Codeflow
  ─────────────────── ─────────────────────── ───────────────────────
  Function recall     ██████████████████████ ██████████████████████
                      100.0%                  100.0%
  Intent/route recall ██████████████████████ ██████████████████████
                      100.0%                  100.0%
  Return type recall  ██████████████████████ ██████████████████████
                      100.0%                  100.0%
  Param coverage      ██████████████████████ █████████████░░░░░░░░░
                      100.0%                   59.8%
  Call graph          ░░░░░░░░░░░░░░░░░░░░░░ ████░░░░░░░░░░░░░░░░░░
                        0.0%                   18.4%
  Structure/index     █░░░░░░░░░░░░░░░░░░░░░ █████████████████████░
                        5.0%                   95.0%
  Lookup efficiency   ░░░░░░░░░░░░░░░░░░░░░░ ██████████████████░░░░
                        0.0%                   80.0%
```

#### Codeflow Parse Details

| Metric | Value |
|--------|------:|
| Functions extracted | 1134 / 1134 total |
| Function recall | 100.0% |
| Intents extracted | 158 |
| Route recall | 100.0% |
| Edges (call graph) | 1,193 |
| Return types captured | 601 / 601 annotated |
| Parameters captured | 919 / 1537 total |
| Typed params captured | 722 |
| Files indexed | 54 |
| fn_type_index buckets | {<FunctionType.OTHER: 'other'>: 679, <FunctionType.AUTH: 'auth'>: 102, <FunctionType.HANDLER: 'handler'>: 21, <FunctionType.DB: 'db'>: 309, <FunctionType.UTIL: 'util'>: 23} |
| Parse time | 0.12s |
| Longest call chain depth | 11 hops |
| Call chain example | `print_response → get_lexer_for_response → get → request → build_request → _merge_url...` |

#### Lookup Cost Comparison

How many tokens does the agent need to read to answer each question?

| Query | Manual Read | Codeflow | Speedup |
|-------|:-----------:|:--------:|:-------:|
| "List all HTTP routes" | 134,082 tok | 0 tok | **∞** |
| "Find function signature" | 2,234 tok | 65 tok | **34×** |
| "What does this file export?" | 134,082 tok | 30 tok | **4469×** |

#### What Codeflow Does NOT Capture

- **Function bodies** — 1134 functions have their implementation stripped (by design: reduces noise)
- **Comments & docstrings** — documentation not passed to agent
- **Import graph** — module-level imports not tracked per-function
- **Runtime values** — no data flow, no type inference beyond annotations

#### What Codeflow UNIQUELY Provides

- **Structured call graph** — 1,193 edges, traversable in O(1) vs O(n) file scan
- **fn_type_index** — instant lookup by function type: {<FunctionType.OTHER: 'other'>: 679, <FunctionType.AUTH: 'auth'>: 102, <FunctionType.HANDLER: 'handler'>: 21, <FunctionType.DB: 'db'>: 309, <FunctionType.UTIL: 'util'>: 23}
- **file_index** — 54 files mapped to their function IDs
- **Intent grouping** — 158 entry points with confidence + evidence
- **Compressed representation** — 77,605 tokens vs 134,082 raw (42.1% smaller)
- **Pre-traced call chains** — deepest chain: 11 hops (print_response → get_lexer_for_response → get → request...)
- **Rich intent objects** — e.g. `SyncOrAsyncAuth.sync_auth_flow() / async | trigger=api:SyncOrAsyncAuth.sync_auth_flow | confidence=0.55 | flow_hops=1`

---

### 4.3 FastAPI Full-Stack Template
> `fastapi/full-stack-fastapi-template` · Type: `fullstack`

#### Ground Truth (from ast.walk + regex on raw source)

| Metric | Value |
|--------|------:|
| Python source files | 45 |
| JS/TS source files | 75 |
| Total source lines | 11,139 |
| **Python functions** (ast.FunctionDef) | **141** |
| Async functions | 1 |
| Classes | 22 |
| Return-annotated functions | 128 |
| Total parameters | 237 |
| Typed parameters | 231 |
| **HTTP routes** (decorator regex) | **23** |
| CLI commands | 0 |
| JS/TS functions | 213 |
| React components | 161 |

Sample routes found:
- `backend/app/api/routes/items.py:13: @router.get(`
- `backend/app/api/routes/items.py:47: @router.get(`
- `backend/app/api/routes/items.py:60: @router.post(`
- `backend/app/api/routes/items.py:74: @router.put(`
- `backend/app/api/routes/items.py:98: @router.delete(`

Sample functions found:
- `backend/app/api/routes/items.py:14:read_items`
- `backend/app/api/routes/items.py:48:read_item`
- `backend/app/api/routes/items.py:61:create_item`
- `backend/app/api/routes/items.py:75:update_item`
- `backend/app/api/routes/items.py:99:delete_item`

#### Manual Read vs Codeflow — Dimension by Dimension

```
Dimension                       Manual Read       Codeflow     Winner
──────────────────────────── ────────────── ────────────── ──────────
  Function recall                    100.0%         100.0%      tie  
  Intent/route recall                100.0%         100.0%      tie  
  Return type recall                 100.0%         100.0%      tie  
  Param coverage                     100.0%         100.0%      tie  
  Call graph                           0.0%          34.1% Codeflow →
  Structure/index                      5.0%          95.0% Codeflow →
  Lookup efficiency                    0.0%         100.0% Codeflow →
──────────────────────────── ────────────── ────────────── ──────────
  OVERALL                             60.8%          89.4% Codeflow →
```

#### Score Breakdown (Visual)

```
  Dimension            Manual Read             Codeflow
  ─────────────────── ─────────────────────── ───────────────────────
  Function recall     ██████████████████████ ██████████████████████
                      100.0%                  100.0%
  Intent/route recall ██████████████████████ ██████████████████████
                      100.0%                  100.0%
  Return type recall  ██████████████████████ ██████████████████████
                      100.0%                  100.0%
  Param coverage      ██████████████████████ ██████████████████████
                      100.0%                  100.0%
  Call graph          ░░░░░░░░░░░░░░░░░░░░░░ ███████░░░░░░░░░░░░░░░
                        0.0%                   34.1%
  Structure/index     █░░░░░░░░░░░░░░░░░░░░░ █████████████████████░
                        5.0%                   95.0%
  Lookup efficiency   ░░░░░░░░░░░░░░░░░░░░░░ ██████████████████████
                        0.0%                  100.0%
```

#### Codeflow Parse Details

| Metric | Value |
|--------|------:|
| Functions extracted | 394 / 354 total |
| Function recall | 100.0% |
| Intents extracted | 46 |
| Route recall | 100.0% |
| Edges (call graph) | 414 |
| Return types captured | 175 / 128 annotated |
| Parameters captured | 451 / 237 total |
| Typed params captured | 442 |
| Files indexed | 98 |
| fn_type_index buckets | {<FunctionType.ROUTE: 'route'>: 23, <FunctionType.HANDLER: 'handler'>: 61, <FunctionType.OTHER: 'other'>: 58, <FunctionType.AUTH: 'auth'>: 19, <FunctionType.DB: 'db'>: 9, <FunctionType.COMPONENT: 'component'>: 163, <FunctionType.HOOK: 'hook'>: 3, <FunctionType.SERVICE: 'service'>: 49, <FunctionType.UTIL: 'util'>: 9} |
| Parse time | 0.08s |
| Longest call chain depth | 6 hops |
| Call chain example | `test_read_item → create_random_item → create_random_user → create_user → User → useSidebar` |

#### Lookup Cost Comparison

How many tokens does the agent need to read to answer each question?

| Query | Manual Read | Codeflow | Speedup |
|-------|:-----------:|:--------:|:-------:|
| "List all HTTP routes" | 75,035 tok | 1,431 tok | **52×** |
| "Find function signature" | 625 tok | 64 tok | **10×** |
| "What does this file export?" | 75,035 tok | 54 tok | **1389×** |

#### What Codeflow Does NOT Capture

- **Function bodies** — 141 functions have their implementation stripped (by design: reduces noise)
- **Comments & docstrings** — documentation not passed to agent
- **Import graph** — module-level imports not tracked per-function
- **Runtime values** — no data flow, no type inference beyond annotations

#### What Codeflow UNIQUELY Provides

- **Structured call graph** — 414 edges, traversable in O(1) vs O(n) file scan
- **fn_type_index** — instant lookup by function type: {<FunctionType.ROUTE: 'route'>: 23, <FunctionType.HANDLER: 'handler'>: 61, <FunctionType.OTHER: 'other'>: 58, <FunctionType.AUTH: 'auth'>: 19, <FunctionType.DB: 'db'>: 9, <FunctionType.COMPONENT: 'component'>: 163, <FunctionType.HOOK: 'hook'>: 3, <FunctionType.SERVICE: 'service'>: 49, <FunctionType.UTIL: 'util'>: 9}
- **file_index** — 98 files mapped to their function IDs
- **Intent grouping** — 46 entry points with confidence + evidence
- **Compressed representation** — 31,070 tokens vs 75,035 raw (58.6% smaller)
- **Pre-traced call chains** — deepest chain: 6 hops (test_read_item → create_random_item → create_random_user → create_user...)
- **Rich intent objects** — e.g. `GET / | trigger=route:GET / | confidence=0.88 | flow_hops=1`

---

## 5. Aggregate Analysis

### 5.1 Average Scores Across All Repos

```
  Approach       Avg Score   Grade   Strengths
  ─────────────  ─────────   ─────   ─────────────────────────────────────────
  Manual Read       60.8%   B       100% recall; zero structure; high token cost
  Codeflow          81.2%   A      Structured; indexed; call graph; low token cost
```

### 5.2 The Recall–Structure Tradeoff

```
  100% ┤ ← Manual Read (all code present)
       │   high recall, zero structure
       │
   75% ┤
       │
   50% ┤                     ← Codeflow (structured, indexed)
       │                       lower recall, maximum structure
   25% ┤
       │
    0% ┤─────────────────────────────────────────────────────
       Recall                                     Structure
```

### 5.3 When to Use Each Approach

| Agent Task | Best Approach | Reason |
|------------|:-------------:|--------|
| Understand codebase architecture | Codeflow | fn_type_index + intents give instant map |
| Find all API endpoints | Codeflow | intent_recall + fn_type_index["route"] |
| Trace a call chain | Codeflow | explicit fn.calls[] graph |
| Read a specific function body | Manual | body not in ParsedRepo |
| Understand a complex algorithm | Manual | implementation detail needed |
| Find what calls function X | Codeflow | scan fn.calls (single pass) |
| First-pass repo orientation | Codeflow | compressed, structured overview |
| Deep bug analysis | Both | architecture from CF, body from raw |

### 5.4 Optimal Agent Strategy

```
1. Agent calls /parse  → gets ParsedRepo (cheap: low tokens, full structure)
   → knows: all functions, all routes, call graph, types, file layout

2. For functions it needs to inspect in detail:
   → reads ONLY those files (targeted, not full scan)
   → uses file_index to know exactly which file to fetch

Combined token cost = flow_tokens + (targeted_file_tokens × files_needed)
vs
Naive cost = all_raw_tokens (reads everything blindly)
```

## 6. Understanding Gap Analysis

What is genuinely NOT capturable without an LLM evaluation?

| Gap | Measurable here? | Impact |
|-----|:----------------:|--------|
| Semantic meaning of function bodies | ✗ requires LLM | Medium |
| Business logic correctness | ✗ requires LLM | High |
| Natural language description quality | ✗ requires LLM | Low |
| Call graph accuracy (false edges?) | ✓ (partial) | Medium |
| Function recall completeness | ✓ (ast.walk) | High |
| Route recall completeness | ✓ (regex) | High |
| Structural navigation efficiency | ✓ (token count) | High |
| Type accuracy | ✓ (annotation match) | Medium |

## 7. Conclusion

**Codeflow is not trying to replace reading code — it is trying to eliminate**
**the need to read code you don't care about.**

Manual reading scores 100% on recall but fails on structure and efficiency.
Codeflow scores lower on recall (bodies stripped) but delivers:

- **Starlette — ASGI Framework**: 4.8% token reduction, 2,635 call edges, 341 intents, 100% fn recall
- **HTTPX — Python HTTP Client**: 42.1% token reduction, 1,193 call edges, 158 intents, 100% fn recall
- **FastAPI Full-Stack Template**: 58.6% token reduction, 414 call edges, 46 intents, 100% fn recall

The right mental model:

> Codeflow gives the agent a **map of the city** (cheap, structured, navigable).
> Raw reading gives the agent **every brick of every building** (complete but overwhelming).
> A good agent uses the map first, then reads only the buildings it needs.

---
*Generated by Codeflow Understanding Benchmark — 2026-03-29 17:33 UTC*