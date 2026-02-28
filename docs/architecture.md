# CodeFlow Architecture

## Goal
CodeFlow anchors debugging around user intent and correlates static intent extraction with live runtime traces.

## Lanes
1. Lane A: simulation-first runtime stream for UX and data model validation.
2. Lane B: OpenTelemetry-based runtime correlation for production observability.

## Backend
- FastAPI APIs for parse/intents/trace/fix.
- Tree-sitter extraction for Python and JS/TS/TSX.
- Graph builder with canonical intent merge and confidence model.
- WebSocket trace streaming with schema-versioned frames.
- Metadata storage abstraction with in-memory and postgres backends.

## Frontend
- React + Zustand state model.
- Intent panel, graph canvas (React Flow + ELK), trace panel, reverse scrubber.
- Manual AI fix request from failed trace context.

## Trace Correlation Contract
Every trace event carries:
- `schema_version`
- `session_id`
- `trace_id`
- `span_id`
- `timestamp_ms`

This keeps lane-A and lane-B payloads forward-compatible.

## W3C Trace Context
- Frontend generates and sends `traceparent` for parse/trace-start requests.
- Backend parses incoming context and reuses `trace_id` in `TraceSession`.
- Simulated trace events set `parent_span_id` and `root_span_id` to preserve causal ordering.
