"""
backend/tracer/correlator.py

Maps raw tracer events (absolute file paths + fn_name)
→ ParsedFunction nodes (relative paths + fn_id).

Produces TraceEvent objects that slot directly into the existing
WebSocket pipeline — identical to what simulator.py produces.

One Correlator instance is created per traced process (per /runner/start call).
It is consulted for every raw event that arrives at /ws/tracer/ingest.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from ..models.schema import ParsedFunction, ParsedRepo, RuntimeValue, TraceEvent, TraceEventType, TraceSession


class Correlator:
    """
    Stateless lookup engine: raw event dict → TraceEvent.

    Lookup strategy (in order):
      1. (relative_file, fn_name)  — exact match, preferred
      2. fn_name alone             — fuzzy fallback when file normalisation fails
      3. No match                  — synthetic fn_id so the event still flows through
    """

    def __init__(self, parsed: ParsedRepo, project_root: str) -> None:
        self._parsed = parsed
        self._root = str(Path(project_root).resolve())

        # Primary index: (relative_file_normalized, fn_name) → ParsedFunction
        # "normalized" = forward-slash separated, no leading slash
        self._exact: dict[tuple[str, str], ParsedFunction] = {}
        # Secondary index: fn_name → list[ParsedFunction]  (for fuzzy fallback)
        self._by_name: dict[str, list[ParsedFunction]] = {}

        for fn in parsed.functions:
            norm_file = _normalize_path(fn.file)
            self._exact[(norm_file, fn.name)] = fn
            self._by_name.setdefault(fn.name, []).append(fn)

    # ── Public API ────────────────────────────────────────────────────────────

    def correlate(self, raw: dict, session: TraceSession, sequence: int) -> Optional[TraceEvent]:
        """
        Convert one raw event dict (from python_sys_tracer) into a TraceEvent.

        Returns None only if raw is malformed enough to be unprocessable.
        Unknown functions still produce a TraceEvent with a synthetic fn_id —
        they appear on the trace timeline even if they can't be mapped to a graph node.
        """
        event_type_str = raw.get("event_type", "")
        try:
            event_type = TraceEventType(event_type_str)
        except ValueError:
            return None  # completely unknown event type — drop it

        fn_name: str = raw.get("fn_name") or "unknown"
        abs_file: str = raw.get("file") or ""
        rel_file = self._relativize(abs_file)

        fn = self._lookup(rel_file, fn_name)

        # fn_id: use the matched ParsedFunction id, or a synthetic one.
        # Synthetic ids start with "live::" so the frontend can distinguish them.
        fn_id = fn.id if fn else f"live::{fn_name}"
        resolved_file = fn.file if fn else (rel_file or abs_file)
        resolved_line = fn.line if fn else (raw.get("line") or 0)

        inputs = _coerce_runtime_values(raw.get("inputs") or [])
        outputs = _coerce_runtime_values(raw.get("outputs") or [])

        return TraceEvent(
            event_type=event_type,
            fn_id=fn_id,
            fn_name=fn_name,
            file=resolved_file,
            line=resolved_line,
            timestamp_ms=float(raw.get("timestamp_ms") or 0.0),
            inputs=inputs,
            outputs=outputs,
            error=raw.get("error"),
            error_type=raw.get("error_type"),
            error_line=raw.get("error_line"),
            duration_ms=raw.get("duration_ms"),
            sequence=sequence,
            trace_id=session.trace_id,
            span_id=raw.get("span_id") or _span_id(),
            parent_span_id=raw.get("parent_span_id"),
            service_name="codeflow-live",
            attributes={"raw_file": abs_file, "matched": fn is not None},
        )

    def known_fn_ids(self) -> frozenset[str]:
        """All ParsedFunction ids in this repo — used to dim unrelated nodes."""
        return frozenset(fn.id for fn in self._parsed.functions)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _lookup(self, rel_file: str, fn_name: str) -> Optional[ParsedFunction]:
        # 1. Exact match
        fn = self._exact.get((_normalize_path(rel_file), fn_name))
        if fn:
            return fn
        # 2. Fuzzy: fn_name only, prefer the candidate whose file is closest
        candidates = self._by_name.get(fn_name, [])
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        # Multiple functions share the same name — pick the one whose file
        # suffix most closely matches rel_file.
        if rel_file:
            for c in candidates:
                if _normalize_path(c.file).endswith(_normalize_path(rel_file)):
                    return c
        # Give up and return first candidate
        return candidates[0]

    def _relativize(self, abs_path: str) -> str:
        """
        Strip project root prefix from an absolute path.
        Returns the relative path, or the original string on failure.
        """
        if not abs_path:
            return ""
        try:
            resolved = str(Path(abs_path).resolve())
            if resolved.startswith(self._root):
                rel = resolved[len(self._root):].lstrip("/\\")
                return rel
        except Exception:
            pass
        return abs_path


# ── Module-level helpers ──────────────────────────────────────────────────────

def _normalize_path(p: str) -> str:
    """Forward-slash, lowercase, strip leading slash."""
    return p.replace("\\", "/").lstrip("/").lower()


def _coerce_runtime_values(raw_list: list) -> list[RuntimeValue]:
    """
    Convert a list of raw dicts (from the in-process tracer) into RuntimeValue objects.
    Drops any entry that can't be coerced — never raises.
    """
    result = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        try:
            result.append(RuntimeValue(
                name=str(item.get("name") or "?"),
                value=item.get("value"),
                type_name=str(item.get("type_name") or "unknown"),
                is_sensitive=bool(item.get("is_sensitive", False)),
            ))
        except Exception:
            pass
    return result


def _span_id() -> str:
    return uuid.uuid4().hex[:16]
