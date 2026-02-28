# Roadmap

## Implemented Now
- Backend APIs and schema v2
- JS/Python static extraction
- Multi-signal extraction: UI events, form actions, router transitions, backend routes, network calls
- Graph build + canonical intent merge
- Simulation lane trace streaming
- Frontend intent graph + playback + fix action
- OTel trace-context propagation + backend instrumentation hooks
- Metadata persistence abstraction with in-memory and postgres backends
- Extraction benchmark harness

## Next Priority
1. Add framework-specific adapters for Next.js server actions and React Router data loaders.
2. Build precision/recall scoring suite with golden datasets and CI thresholds.
3. Add trace-to-diff patch generation quality checks for AI fix suggestions.
4. Implement graph virtualization for very large repos.
5. Add export package for incident summaries (intent + trace + suggested fix).
