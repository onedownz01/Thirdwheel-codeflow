"""Deterministic runtime simulation for lane-A MVP trace streaming."""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable

from ..models.schema import (
    Intent,
    IntentOccurrence,
    ParsedRepo,
    RuntimeValue,
    TraceEvent,
    TraceEventType,
    TraceSession,
)

EmitFunc = Callable[[dict], Awaitable[None]]

TIMING_MS = {
    "route": 18,
    "handler": 12,
    "service": 25,
    "db": 42,
    "auth": 20,
    "hook": 8,
    "component": 7,
    "util": 6,
    "other": 10,
}


async def run_simulated_trace(
    parsed: ParsedRepo,
    intent: Intent,
    session: TraceSession,
    emit: EmitFunc,
    simulate_error_at_step: int | None = None,
    parent_span_id: str | None = None,
) -> IntentOccurrence:
    session.status = "running"
    fn_by_id = {fn.id: fn for fn in parsed.functions}
    started = time.perf_counter()
    sequence = 0

    await emit(_frame(session.session_id, "trace_start", {"intent": intent.model_dump(), "schema_version": session.schema_version}))
    intent_start = TraceEvent(
        event_type=TraceEventType.INTENT_START,
        fn_id=intent.handler_fn_id,
        fn_name=intent.label,
        file=intent.source_file,
        line=0,
        timestamp_ms=0.0,
        sequence=sequence,
        trace_id=session.trace_id,
        span_id=session.root_span_id or _span_id(),
        parent_span_id=parent_span_id,
        service_name="codeflow",
        attributes={"intent_id": intent.id, "intent_label": intent.label},
    )
    sequence += 1
    session.events.append(intent_start)
    await emit(_frame(session.session_id, "trace_event", {"event": intent_start.model_dump(), "schema_version": session.schema_version}))

    for step_idx, fn_id in enumerate(intent.flow_ids, start=1):
        fn = fn_by_id.get(fn_id)
        if not fn:
            warning = TraceEvent(
                event_type=TraceEventType.WARNING,
                fn_id=fn_id,
                fn_name="unknown",
                file="",
                line=0,
                timestamp_ms=(time.perf_counter() - started) * 1000,
                sequence=sequence,
                trace_id=session.trace_id,
                span_id=_span_id(),
                parent_span_id=session.root_span_id,
                service_name="codeflow",
                attributes={"reason": "missing function node"},
            )
            sequence += 1
            session.events.append(warning)
            await emit(_frame(session.session_id, "trace_warning", {
                "warning": f"Function '{fn_id}' not found in parsed repo — skipped",
                "event": warning.model_dump(),
                "schema_version": session.schema_version,
            }))
            continue

        now_ms = (time.perf_counter() - started) * 1000
        call_event = TraceEvent(
            event_type=TraceEventType.CALL,
            fn_id=fn.id,
            fn_name=fn.name,
            file=fn.file,
            line=fn.line,
            timestamp_ms=now_ms,
            sequence=sequence,
            trace_id=session.trace_id,
            span_id=_span_id(),
            parent_span_id=session.root_span_id,
            service_name="codeflow",
            attributes={"function_type": fn.type.value},
            inputs=_simulated_inputs(fn.params, step_idx),
        )
        sequence += 1
        session.events.append(call_event)
        await emit(_frame(session.session_id, "trace_event", {"event": call_event.model_dump(), "schema_version": session.schema_version}))

        if simulate_error_at_step and step_idx == simulate_error_at_step:
            err_ms = (time.perf_counter() - started) * 1000
            err_event = TraceEvent(
                event_type=TraceEventType.ERROR,
                fn_id=fn.id,
                fn_name=fn.name,
                file=fn.file,
                line=fn.line,
                timestamp_ms=err_ms,
                sequence=sequence,
                trace_id=session.trace_id,
                span_id=_span_id(),
                parent_span_id=call_event.span_id,
                service_name="codeflow",
                error="Simulated failure for fix-assistant testing",
                error_type="SimulatedTraceError",
                error_line=fn.line,
            )
            sequence += 1
            session.events.append(err_event)
            session.status = "error"
            session.error_at_fn_id = fn.id
            await emit(
                _frame(
                    session.session_id,
                    "trace_event",
                    {"event": err_event.model_dump(), "schema_version": session.schema_version},
                )
            )
            break

        delay_ms = TIMING_MS.get(fn.type.value, TIMING_MS["other"])
        await asyncio.sleep((delay_ms + 700) / 1000)

        done_ms = (time.perf_counter() - started) * 1000
        ret_event = TraceEvent(
            event_type=TraceEventType.RETURN,
            fn_id=fn.id,
            fn_name=fn.name,
            file=fn.file,
            line=fn.line,
            timestamp_ms=done_ms,
            duration_ms=delay_ms,
            sequence=sequence,
            trace_id=session.trace_id,
            span_id=_span_id(),
            parent_span_id=call_event.span_id,
            service_name="codeflow",
            attributes={"function_type": fn.type.value},
            outputs=_simulated_outputs(fn.params, step_idx),
        )
        sequence += 1
        session.events.append(ret_event)
        await emit(_frame(session.session_id, "trace_event", {"event": ret_event.model_dump(), "schema_version": session.schema_version}))

    if session.status != "error":
        session.status = "success"
    session.total_duration_ms = (time.perf_counter() - started) * 1000
    intent_end = TraceEvent(
        event_type=TraceEventType.INTENT_END,
        fn_id=intent.handler_fn_id,
        fn_name=intent.label,
        file=intent.source_file,
        line=0,
        timestamp_ms=session.total_duration_ms,
        sequence=sequence,
        trace_id=session.trace_id,
        span_id=_span_id(),
        parent_span_id=session.root_span_id,
        service_name="codeflow",
        attributes={"status": session.status},
    )
    session.events.append(intent_end)
    await emit(_frame(session.session_id, "trace_event", {"event": intent_end.model_dump(), "schema_version": session.schema_version}))

    await emit(
        _frame(
            session.session_id,
            "trace_complete",
            {
                "schema_version": session.schema_version,
                "total_duration_ms": session.total_duration_ms,
                "event_count": len(session.events),
            },
        )
    )

    return IntentOccurrence(
        occurrence_id=str(uuid.uuid4()),
        repo=parsed.repo,
        intent_id=intent.id,
        trace_id=session.trace_id,
        session_id=session.session_id,
        outcome="error" if session.status == "error" else "success",
        latency_ms=session.total_duration_ms,
        started_at=datetime.now(timezone.utc).isoformat(),
    )



def _frame(session_id: str, msg_type: str, payload: dict) -> dict:
    return {
        "schema_version": payload.get("schema_version", "2.0.0"),
        "session_id": session_id,
        "timestamp_ms": time.time() * 1000,
        "type": msg_type,
        **payload,
    }



def _span_id() -> str:
    return uuid.uuid4().hex[:16]


def _simulated_inputs(params, step_idx: int) -> list[RuntimeValue]:
    values: list[RuntimeValue] = []
    if params:
        in_params = [p for p in params if p.direction == "in"][:5]
        for p in in_params:
            sensitive = _is_sensitive(p.name)
            values.append(RuntimeValue(
                name=p.name,
                value=_realistic_value(p.name, p.type, step_idx),
                type_name=p.type or "any",
                is_sensitive=sensitive,
            ))
        if values:
            return values
    return [RuntimeValue(name="event", value={"type": "click", "timestamp": 1711360200000}, type_name="object", is_sensitive=False)]


def _simulated_outputs(params, step_idx: int) -> list[RuntimeValue]:
    values: list[RuntimeValue] = []
    out_params = [p for p in params if p.direction == "out"][:4]
    for p in out_params:
        values.append(RuntimeValue(
            name=p.name,
            value=_realistic_value(p.name, p.type, step_idx + 1),
            type_name=p.type or "any",
            is_sensitive=False,
        ))
    if values:
        return values
    return [RuntimeValue(name="result", value={"success": True, "status": 200}, type_name="object", is_sensitive=False)]


def _is_sensitive(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in ("password", "secret", "token", "key", "auth", "credential"))


def _realistic_value(name: str, type_name: str, seed: int):
    """Generate realistic-looking values based on parameter name semantics."""
    n = name.lower()
    t = (type_name or "").lower()

    # Identity / user
    if any(k in n for k in ("userid", "user_id", "uid", "ownerId", "owner_id")):
        return f"usr_{['a1b2c3', 'd4e5f6', 'x7y8z9'][seed % 3]}"
    if "email" in n:
        return ["alice@example.com", "bob@acme.io", "carol@dev.co"][seed % 3]
    if n in ("name", "username", "fullname", "full_name", "displayname"):
        return ["Alice Chen", "Bob Martinez", "Carol Singh"][seed % 3]
    if "firstname" in n or "first_name" in n:
        return ["Alice", "Bob", "Carol"][seed % 3]
    if "lastname" in n or "last_name" in n:
        return ["Chen", "Martinez", "Singh"][seed % 3]

    # Content / text
    if any(k in n for k in ("content", "body", "message", "text", "description", "note")):
        return ["Remember to follow up on the API integration.", "Meeting notes from sync call.", "Draft: Quarterly review summary."][seed % 3]
    if any(k in n for k in ("title", "label", "heading", "subject")):
        return ["Q4 Planning", "API Migration", "Sprint Review"][seed % 3]
    if any(k in n for k in ("query", "search", "q", "keyword")):
        return ["machine learning", "API authentication", "react hooks"][seed % 3]
    if "url" in n or "endpoint" in n or "href" in n:
        return ["https://api.example.com/v1/data", "https://cdn.assets.io/img/hero.png"][seed % 2]
    if "path" in n or "route" in n:
        return ["/api/v1/users", "/dashboard/settings", "/auth/callback"][seed % 3]

    # IDs
    if any(k in n for k in ("id", "_id", "uuid", "sessionid", "traceid")):
        return f"{['f3a1b2c4', 'e5d6c7b8', 'a9b8c7d6'][seed % 3]}-{'abcd'}-{'1234'}"
    if any(k in n for k in ("tag", "label", "category", "group")):
        return [["web", "api", "v2"], ["auth", "session"], ["draft", "pending"]][seed % 3]

    # Numbers / pagination
    if any(k in n for k in ("page", "offset", "skip")):
        return seed
    if any(k in n for k in ("limit", "count", "size", "max")):
        return [10, 25, 50][seed % 3]
    if any(k in n for k in ("index", "idx", "position", "rank")):
        return seed - 1

    # Booleans
    if any(k in n for k in ("enabled", "active", "isvalid", "valid", "success", "visible", "open", "checked")):
        return True
    if any(k in n for k in ("error", "failed", "loading", "pending")):
        return False

    # Timestamps / dates
    if any(k in n for k in ("timestamp", "createdat", "updatedat", "date", "time")):
        return "2024-03-25T10:30:00Z"

    # Sensitive
    if _is_sensitive(n):
        return "••••••••"

    # Type-based fallback
    if "bool" in t:
        return True
    if "int" in t or "number" in t or "float" in t:
        return seed * 10
    if "list" in t or "array" in t:
        return ["item_1", "item_2", "item_3"]
    if "dict" in t or "object" in t:
        return {"id": f"obj_{seed}", "status": "active"}

    # Generic string fallback — use the param name as a hint
    return f"<{name}>"
