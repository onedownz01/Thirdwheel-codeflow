"""Convert ingested OTel spans into CodeFlow trace events."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable

from ..models.schema import (
    IngestedSpan,
    Intent,
    IntentOccurrence,
    ParsedRepo,
    RuntimeValue,
    TraceEvent,
    TraceEventType,
    TraceSession,
)

EmitFunc = Callable[[dict], Awaitable[None]]


async def emit_otel_span_trace(
    parsed: ParsedRepo,
    intent: Intent,
    session: TraceSession,
    spans: list[IngestedSpan],
    emit: EmitFunc,
) -> IntentOccurrence:
    if not spans:
        raise ValueError("No ingested spans found for requested trace")

    fn_by_id = {fn.id: fn for fn in parsed.functions}
    fn_by_name = {fn.name: fn for fn in parsed.functions}
    started_at = min(s.start_time_ms for s in spans)
    sequence = 0
    has_error = False

    await emit(
        _frame(
            session.session_id,
            "trace_start",
            {
                "schema_version": session.schema_version,
                "intent": intent.model_dump(),
                "source": "otel_ingest",
            },
        )
    )

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
        parent_span_id=session.parent_span_id,
        service_name="codeflow",
        attributes={"intent_id": intent.id, "intent_label": intent.label, "source": "otel_ingest"},
    )
    sequence += 1
    session.events.append(intent_start)
    await emit(
        _frame(
            session.session_id,
            "trace_event",
            {"schema_version": session.schema_version, "event": intent_start.model_dump()},
        )
    )

    for span in sorted(spans, key=lambda s: s.start_time_ms):
        fn = _resolve_function(span, fn_by_id, fn_by_name)
        timestamp_ms = max(0.0, span.start_time_ms - started_at)
        duration_ms = max(0.0, span.end_time_ms - span.start_time_ms)

        call_event = TraceEvent(
            event_type=TraceEventType.CALL,
            fn_id=fn.id if fn else f"runtime:{span.name}",
            fn_name=span.name,
            file=fn.file if fn else span.attributes.get("code.filepath", ""),
            line=int(span.attributes.get("code.lineno", fn.line if fn else 0) or 0),
            timestamp_ms=timestamp_ms,
            sequence=sequence,
            trace_id=span.trace_id or session.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id or session.root_span_id,
            service_name=span.service_name,
            attributes=span.attributes,
            inputs=_runtime_values(span.attributes.get("inputs"), "in"),
        )
        sequence += 1
        session.events.append(call_event)
        await emit(
            _frame(
                session.session_id,
                "trace_event",
                {"schema_version": session.schema_version, "event": call_event.model_dump()},
            )
        )

        if span.status == "error":
            has_error = True
            err_event = TraceEvent(
                event_type=TraceEventType.ERROR,
                fn_id=call_event.fn_id,
                fn_name=call_event.fn_name,
                file=call_event.file,
                line=call_event.line,
                timestamp_ms=timestamp_ms + duration_ms,
                sequence=sequence,
                trace_id=call_event.trace_id,
                span_id=_span_id(),
                parent_span_id=call_event.span_id,
                service_name=call_event.service_name,
                error=span.error_message or "Span recorded error",
                error_type=span.error_type or "RuntimeError",
                error_line=call_event.line,
                attributes=span.attributes,
            )
            sequence += 1
            session.events.append(err_event)
            await emit(
                _frame(
                    session.session_id,
                    "trace_event",
                    {"schema_version": session.schema_version, "event": err_event.model_dump()},
                )
            )
            session.error_at_fn_id = call_event.fn_id
            continue

        return_event = TraceEvent(
            event_type=TraceEventType.RETURN,
            fn_id=call_event.fn_id,
            fn_name=call_event.fn_name,
            file=call_event.file,
            line=call_event.line,
            timestamp_ms=timestamp_ms + duration_ms,
            duration_ms=duration_ms,
            sequence=sequence,
            trace_id=call_event.trace_id,
            span_id=_span_id(),
            parent_span_id=call_event.span_id,
            service_name=call_event.service_name,
            attributes=span.attributes,
            outputs=_runtime_values(span.attributes.get("outputs"), "out"),
        )
        sequence += 1
        session.events.append(return_event)
        await emit(
            _frame(
                session.session_id,
                "trace_event",
                {"schema_version": session.schema_version, "event": return_event.model_dump()},
            )
        )

    total_duration = max(0.0, max(s.end_time_ms for s in spans) - started_at)
    session.total_duration_ms = total_duration
    session.status = "error" if has_error else "success"

    intent_end = TraceEvent(
        event_type=TraceEventType.INTENT_END,
        fn_id=intent.handler_fn_id,
        fn_name=intent.label,
        file=intent.source_file,
        line=0,
        timestamp_ms=total_duration,
        sequence=sequence,
        trace_id=session.trace_id,
        span_id=_span_id(),
        parent_span_id=session.root_span_id,
        service_name="codeflow",
        attributes={"status": session.status, "source": "otel_ingest"},
    )
    session.events.append(intent_end)
    await emit(
        _frame(
            session.session_id,
            "trace_event",
            {"schema_version": session.schema_version, "event": intent_end.model_dump()},
        )
    )

    await emit(
        _frame(
            session.session_id,
            "trace_complete",
            {
                "schema_version": session.schema_version,
                "total_duration_ms": session.total_duration_ms,
                "event_count": len(session.events),
                "source": "otel_ingest",
            },
        )
    )

    return IntentOccurrence(
        occurrence_id=str(uuid.uuid4()),
        repo=parsed.repo,
        intent_id=intent.id,
        trace_id=session.trace_id,
        session_id=session.session_id,
        outcome="error" if has_error else "success",
        latency_ms=session.total_duration_ms,
        started_at=datetime.now(timezone.utc).isoformat(),
    )


def _resolve_function(span: IngestedSpan, by_id: dict, by_name: dict):
    fn_id = span.attributes.get("fn_id")
    if fn_id and fn_id in by_id:
        return by_id[fn_id]

    code_fn = span.attributes.get("code.function")
    if code_fn and code_fn in by_name:
        return by_name[code_fn]

    if span.name in by_name:
        return by_name[span.name]

    return None


def _runtime_values(raw, direction: str) -> list[RuntimeValue]:
    if not isinstance(raw, dict):
        return []
    values: list[RuntimeValue] = []
    for name, value in list(raw.items())[:6]:
        values.append(
            RuntimeValue(
                name=name,
                value=value if isinstance(value, (str, int, float, bool)) else str(value),
                type_name=type(value).__name__,
                is_sensitive=False,
            )
        )
    return values


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
