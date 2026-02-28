"""Deterministic runtime simulation for lane-A MVP trace streaming."""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable

from ..models.schema import Intent, IntentOccurrence, ParsedRepo, TraceEvent, TraceEventType, TraceSession

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
            await emit(_frame(session.session_id, "trace_warning", {"event": warning.model_dump(), "schema_version": session.schema_version}))
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
        await asyncio.sleep((delay_ms + 140) / 1000)

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
