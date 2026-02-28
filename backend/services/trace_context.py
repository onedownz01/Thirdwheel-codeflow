"""W3C trace-context helpers used across HTTP and trace sessions."""
from __future__ import annotations

import os
import re
import secrets
from dataclasses import dataclass

TRACEPARENT_RE = re.compile(r"^([\da-f]{2})-([\da-f]{32})-([\da-f]{16})-([\da-f]{2})$", re.IGNORECASE)


@dataclass
class TraceContext:
    version: str
    trace_id: str
    parent_span_id: str
    trace_flags: str



def parse_traceparent(traceparent: str | None) -> TraceContext | None:
    if not traceparent:
        return None
    m = TRACEPARENT_RE.match(traceparent.strip())
    if not m:
        return None
    version, trace_id, parent_span_id, trace_flags = m.groups()
    if trace_id == "0" * 32 or parent_span_id == "0" * 16:
        return None
    return TraceContext(
        version=version.lower(),
        trace_id=trace_id.lower(),
        parent_span_id=parent_span_id.lower(),
        trace_flags=trace_flags.lower(),
    )



def new_trace_id() -> str:
    return secrets.token_hex(16)



def new_span_id() -> str:
    return secrets.token_hex(8)



def build_traceparent(trace_id: str, span_id: str, sampled: bool = True) -> str:
    flags = "01" if sampled else "00"
    return f"00-{trace_id}-{span_id}-{flags}"



def is_otel_enabled() -> bool:
    return bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
