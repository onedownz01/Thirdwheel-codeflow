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
