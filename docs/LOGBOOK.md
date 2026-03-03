# CodeFlow Logbook

Last updated: 2026-03-03 (Asia/Kolkata)

## 1) Two-line Product Definition
- Build a debugger that starts from user intent (what the user tried to do), not from raw code internals.
- Parse repo -> generate intent/action buttons -> render linked function graph -> run flow per intent with per-block inputs/outputs/timing/errors for debugging.

## 2) What We Agreed the Product Should Do
- User pastes any GitHub repo.
- System auto-parses and extracts intents/actions.
- UI shows a Supabase-style graph feel (boxes + links) for code flow.
- Clicking an action starts flow visualization in real time.
- Each block should show actionable debugging context (inputs/outputs/errors/timing).

## 3) Practical Feasibility (Agreed)
- Yes, this is practically possible.
- Not possible to guarantee literal 100% intent extraction from static code alone.
- Best strategy: static parser first, optional LLM enrichment second, runtime traces for confirmation third.

## 4) Current State (as discussed)
Implemented/working in current architecture:
- Repo parse endpoint and graph generation.
- Intent extraction (multi-signal heuristic coverage).
- Flow graph rendering with function blocks and links.
- Intent click -> streamed flow events (simulation lane).
- Reverse playback basics and trace panel.

Partially complete / pending:
- Full real runtime tracing coverage (beyond simulation fallback).
- Rich per-block runtime I/O capture in real executions.
- Higher-coverage intent extraction for broader frameworks/patterns.
- Performance hardening for very large repos.

## 5) LLM for Intent Parsing (Decision)
- We should use LLM as an enrichment layer, not as the only parser.
- Reason:
  - AST parser gives deterministic, fast baseline.
  - LLM improves naming/grouping/disambiguation and can recover missed semantic intents.
  - Runtime traces validate and rank intents by real usage.

## 6) UI Direction You Requested (Captured)
- Left sidebar: repo history.
- Right side: intents grouped under broad dropdown categories.
- Keep trace/debug context in right-side stack as well.
- Center: function blocks + flowing dotted lines in real time.
- Visual inspiration: Supabase-style graph feel, but adapted for code intent flow.

## 7) Issues Encountered and Discussed
- Frontend dev server drops intermittently in this environment when detached.
- Repo input format mismatches (full GitHub URL vs owner/repo) created parse failures previously.
- UI showed opaque errors like `[object Object]` when error handling was weak.
- Validation error observed in UI: parse body occasionally arrived as stringified JSON string instead of object (`422`).

## 8) Fixes We Discussed/Appointed
- Normalize repo inputs consistently (support both full URL and owner/repo).
- Improve frontend error readability (never show `[object Object]`; show concrete backend message).
- Make local dev startup more stable via a single script and persistent run mode.
- Harden parse endpoint compatibility for malformed/double-serialized body patterns.

## 9) Public Repo Strategy (Agreed)
- Yes, we should choose one public repo as a canonical benchmark target.
- Use it to verify intent extraction quality, graph readability, flow behavior, and debugging usefulness end-to-end.
- Define expected intents manually first, then measure parser+runtime output against that baseline.

## 10) Next Concrete Steps
1. Finalize canonical public test repo.
2. Run parse baseline and capture: function count, intent count, top intent groups, confidence distribution.
3. Validate UX loop end-to-end on that repo:
   - Parse -> intents visible
   - Graph renders
   - Intent click streams flow
   - Block-level debug info useful
4. Add optional LLM enrichment toggle for intent naming/grouping improvements.
5. Keep updating this logbook on every major decision/fix.

## 11) Operating Rule Going Forward
- This file is the single running logbook and should be updated after each meaningful change, decision, bug, or test result.

## 12) Audit Snapshot (2026-03-03)
- Scope audited: backend APIs/parsers/tracer/services, frontend app/store/canvas/panels, tests/build, and public repo parse behavior.

What passed:
- Backend unit tests pass when executed with package path configured:
  - `PYTHONPATH=. pytest -q backend/tests` -> `6 passed`
- Frontend build passes:
  - `npm run build` succeeds.
- Live parse endpoint works for valid repos:
  - `POST /parse` for `NousResearch/hermes-agent` returns graph payload.
  - `POST /parse` for `tiangolo/fastapi` returns rich route intents.

Key findings (pending/bugs):
1. Confidence scoring bug in JS parser:
   - In `backend/parser/js_parser.py`, confidence is recomputed as `sum(weights)/2.0`.
   - This halves single-signal confidence (e.g., route `0.88 -> 0.44`), pushing many intents into `candidate`.
2. Runtime lane is still simulation-only for block I/O realism:
   - `backend/tracer/simulator.py` emits deterministic events.
   - Real runtime capture for function-level inputs/outputs in app code is not implemented.
3. Frontend trace warning handling currently uses global error banner:
   - Warnings can look like hard failures in UI state.
4. Environment consistency issue causing flaky local startup:
   - `.venv` exists but does not currently have all backend deps installed.
   - Some commands run with global Python/pytest instead of project env.
   - `scripts/dev_local.sh` uses `python3` (global), not pinned `.venv/bin/python`, so behavior can differ machine-to-machine.
5. Validation and UX hardening gaps:
   - No frontend lint setup (`npm run lint` is placeholder).
   - No end-to-end integration test for parse->intent click->ws trace->playback.
   - No performance/scale tests yet for large graphs.

Current benchmark snapshot:
- `NousResearch/hermes-agent`: ~1107 functions, 1632 edges, 5 intents (backend routes), low confidence due bug above.
- `tiangolo/fastapi`: 393 functions, 74 edges, 75 intents (all backend route-derived, high confidence).

## 13) Remediation Pass (2026-03-03) - 7 Pending Tracks
Public benchmark repo selected for dry run:
- `tiangolo/fastapi` (stable route-heavy baseline with deterministic expected intents).

Implemented in this pass:
1. Intent confidence bug fixed (critical):
   - `backend/parser/js_parser.py` no longer halves confidence (`sum/2` removed).
   - Added confidence aggregation with evidence diversity bonuses.
2. Dynamic intent extraction expanded:
   - JS: added `server_action` and JS CLI `.command(...)` intent signals.
   - Python: added CLI intent extraction from `@...command(...)` and argparse `add_parser(...)`.
3. Runtime lane B upgraded:
   - Added `POST /trace/ingest` and span contracts (`IngestedSpan`, `TraceIngestRequest`).
   - Added `backend/tracer/otel_bridge.py` to convert ingested spans into trace events.
   - OTel mode now uses ingested spans when present; otherwise warns and falls back to simulation.
4. Simulated trace debug quality improved:
   - Simulator now emits synthetic per-block input/output runtime values for better block visibility.
5. Local runtime stability and env standardization:
   - Rebuilt `scripts/dev_local.sh` with pinned `.venv` Python, dependency checks, log files, restart supervision.
   - Added `scripts/bootstrap_env.sh`.
   - Added `Makefile` for setup/dev/test/lint/build/dry-run commands.
   - Added `pyproject.toml` (`pytest` pythonpath + `ruff` config).
6. Quality gates:
   - Added backend dev deps (`backend/requirements-dev.txt`) and CI lint/test updates.
   - Frontend lint now runs typecheck (`npm run lint` -> `tsc --noEmit`).
7. Large-graph performance hardening:
   - `FlowCanvas` now uses large-graph mode with node/edge caps and degree-based prioritization.
   - Layout recomputation no longer runs on every trace event; block state updates are incremental.

Dry run result (end-to-end):
- Command:
  - `.venv/bin/python scripts/e2e_dry_run.py --repo tiangolo/fastapi --base-url http://127.0.0.1:8000`
- Outcome: `PASS`
- Snapshot:
  - parsed: 393 functions, 74 edges, 75 intents
  - simulation trace: 4 events
  - OTel ingest trace: 6 events (ingested spans accepted and streamed)

Validation sample after confidence/extraction fixes:
- `NousResearch/hermes-agent` now yields 59 intents (was 5 in prior snapshot), including backend route intents and CLI intents.

## 14) Post-Redesign Stability Fix (2026-03-03)
Issue reported:
- Clicking some intents caused the UI to appear blank/vanished.

Root cause and mitigation:
1. Some extracted intents (notably CLI-derived placeholders) can have flow IDs that do not intersect rendered function nodes.
2. Previous focus logic dimmed everything when any flow set existed, even if there was no real intersection.

Fixes applied:
- `frontend/src/store/flowStore.ts`: only dim non-flow nodes when intent flow intersects actual repo nodes.
- `frontend/src/components/FlowCanvas/FlowCanvas.tsx`: large-graph selection now ignores non-intersecting flow IDs and falls back to high-signal nodes.
- Added defensive node-data guard in flow state update map.
- Added `AppErrorBoundary` (`frontend/src/components/AppErrorBoundary.tsx`) and wired in `frontend/src/main.tsx` to prevent full white-screen failures.

Verification:
- Frontend lint + build pass.
- End-to-end dry run still passes on `NousResearch/hermes-agent`.
