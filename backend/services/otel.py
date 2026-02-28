"""Optional OpenTelemetry bootstrap for FastAPI runtime lane-B."""
from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import FastAPI

OTEL_STATE: dict[str, Any] = {
    "enabled": False,
    "instrumented": False,
    "reason": "OTEL_EXPORTER_OTLP_ENDPOINT not set",
}



def setup_otel(app: FastAPI, service_name: str = "codeflow-backend") -> Optional[object]:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        OTEL_STATE.update({"enabled": False, "instrumented": False, "reason": "endpoint missing"})
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        exporter = OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        OTEL_STATE.update(
            {
                "enabled": True,
                "instrumented": True,
                "reason": "ok",
                "endpoint": endpoint,
                "service_name": service_name,
            }
        )
        return provider
    except Exception as exc:
        OTEL_STATE.update(
            {
                "enabled": bool(endpoint),
                "instrumented": False,
                "reason": f"instrumentation error: {exc}",
                "endpoint": endpoint,
                "service_name": service_name,
            }
        )
        return None



def get_otel_state() -> dict[str, Any]:
    return dict(OTEL_STATE)
