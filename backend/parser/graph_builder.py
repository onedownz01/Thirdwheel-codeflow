"""Graph resolver + intent canonicalization/fusion basics."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone

from ..models.schema import Edge, Intent, IntentStatus, ParsedFunction, ParsedRepo


def build_graph(
    functions: list[ParsedFunction],
    intents: list[Intent],
    repo: str,
    branch: str,
) -> ParsedRepo:
    by_name: dict[str, list[ParsedFunction]] = {}
    by_id: dict[str, ParsedFunction] = {}

    for fn in functions:
        by_id[fn.id] = fn
        by_name.setdefault(fn.name, []).append(fn)

    edges: list[Edge] = []
    seen_edges: set[str] = set()

    for fn in functions:
        resolved_calls: list[str] = []
        for call_name in fn.calls:
            targets = by_name.get(call_name, [])
            if not targets:
                continue
            same_file = [t for t in targets if t.file == fn.file]
            target = same_file[0] if same_file else targets[0]
            resolved_calls.append(target.id)

            edge_key = f"{fn.id}->{target.id}"
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append(Edge(id=f"e_{len(edges)}", source=fn.id, target=target.id, type="calls"))

            if fn.id not in target.called_by:
                target.called_by.append(fn.id)

        fn.calls = resolved_calls

    resolved_intents: list[Intent] = []
    for intent in intents:
        handler_name = _extract_handler_name(intent.handler_fn_id)
        matches = by_name.get(handler_name, [])
        if matches:
            same_file = [m for m in matches if m.file == intent.source_file]
            entry = same_file[0] if same_file else matches[0]
            intent.handler_fn_id = entry.id
            intent.flow_ids = bfs_flow(entry.id, by_id, max_depth=10)
            intent.hop_count = len(intent.flow_ids)
        else:
            # Handler is likely a callback prop — find any function from same file as fallback
            same_file_fns = [fn for fn in functions if fn.file == intent.source_file]
            if same_file_fns:
                entry = same_file_fns[0]
                intent.handler_fn_id = entry.id
                intent.flow_ids = bfs_flow(entry.id, by_id, max_depth=6)
                intent.hop_count = len(intent.flow_ids)
            else:
                intent.flow_ids = []
                intent.hop_count = 0

        resolved_intents.append(intent)

    merged_intents = _merge_intents(resolved_intents)

    return ParsedRepo(
        repo=repo,
        branch=branch,
        functions=functions,
        intents=merged_intents,
        edges=edges,
        file_count=len({f.file for f in functions}),
        parsed_at=datetime.now(timezone.utc).isoformat(),
    )



def bfs_flow(start_id: str, by_id: dict[str, ParsedFunction], max_depth: int = 10) -> list[str]:
    visited: set[str] = set()
    path: list[str] = []
    queue: deque[tuple[str, int]] = deque([(start_id, 0)])

    while queue and len(path) < max_depth:
        fn_id, depth = queue.popleft()
        if fn_id in visited or depth > max_depth:
            continue

        visited.add(fn_id)
        path.append(fn_id)

        fn = by_id.get(fn_id)
        if not fn:
            continue
        for child in fn.calls[:4]:
            if child not in visited:
                queue.append((child, depth + 1))

    return path



def _extract_handler_name(handler_fn_id: str) -> str:
    parts = handler_fn_id.split(":")
    if len(parts) >= 2:
        return parts[-2]
    return handler_fn_id



def _merge_intents(intents: list[Intent]) -> list[Intent]:
    by_canonical: dict[str, Intent] = {}

    for intent in intents:
        key = intent.canonical_id or intent.id
        existing = by_canonical.get(key)
        if not existing:
            by_canonical[key] = intent
            continue

        existing.aliases = sorted(set(existing.aliases + intent.aliases + [intent.label]))
        existing.evidence.extend(intent.evidence)
        existing.confidence = min(0.99, max(existing.confidence, intent.confidence))

        if len(intent.flow_ids) > len(existing.flow_ids):
            existing.flow_ids = intent.flow_ids
            existing.hop_count = intent.hop_count
            existing.handler_fn_id = intent.handler_fn_id

    merged = list(by_canonical.values())
    for intent in merged:
        if intent.confidence >= 0.85:
            intent.status = IntentStatus.VERIFIED
        elif intent.confidence >= 0.5:
            intent.status = IntentStatus.OBSERVED
        else:
            intent.status = IntentStatus.CANDIDATE
    return sorted(merged, key=lambda x: x.confidence, reverse=True)
