import asyncio

from backend.models.schema import (
    FunctionType,
    IngestedSpan,
    Intent,
    ParsedFunction,
    ParsedRepo,
    TraceSession,
)
from backend.parser.js_parser import parse_js_file
from backend.parser.python_parser import parse_python_file
from backend.tracer.otel_bridge import emit_otel_span_trace


def test_js_route_confidence_not_halved():
    content = """
    const app = {};
    app.post('/users', handler);
    """
    _, intents = parse_js_file("src/routes.ts", content)
    route = next((i for i in intents if i.trigger.startswith("route:")), None)
    assert route is not None
    assert route.confidence >= 0.85


def test_js_server_action_intent_extracted():
    content = """
    export async function submitForm(data) {
      'use server';
      return { ok: true };
    }
    """
    _, intents = parse_js_file("app/actions.ts", content)
    assert any(i.trigger == "server_action" for i in intents)


def test_python_cli_intents_extracted():
    content = """
import click
import argparse

@click.command("sync-users")
def sync_users():
    return True

parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest="cmd")
sub.add_parser("run-report")
"""
    _, intents = parse_python_file("cli.py", content)
    triggers = {i.trigger for i in intents}
    assert "cli:command" in triggers
    assert "cli:argparse" in triggers


def test_otel_bridge_emits_events():
    fn = ParsedFunction(id="svc.py:service_call:1", name="service_call", file="svc.py", type=FunctionType.SERVICE, line=1)
    intent = Intent(
        id="intent:svc",
        canonical_id="actions.run",
        label="Run",
        icon="▶",
        trigger="onClick",
        handler_fn_id=fn.id,
        source_file="svc.py",
        group="Actions",
        flow_ids=[fn.id],
    )
    parsed = ParsedRepo(
        repo="demo/repo",
        branch="main",
        functions=[fn],
        intents=[intent],
        edges=[],
        file_count=1,
        parsed_at="now",
    )
    session = TraceSession(
        session_id="session-1",
        intent_id=intent.id,
        intent_label=intent.label,
        trace_id="a" * 32,
        root_span_id="b" * 16,
    )
    spans = [
        IngestedSpan(
            trace_id="a" * 32,
            span_id="1" * 16,
            parent_span_id="b" * 16,
            name="service_call",
            service_name="backend",
            start_time_ms=1000.0,
            end_time_ms=1040.0,
            attributes={"inputs": {"x": 1}, "outputs": {"ok": True}},
            status="ok",
        )
    ]

    messages = []

    async def emit(msg):
        messages.append(msg)

    asyncio.run(
        emit_otel_span_trace(
            parsed=parsed,
            intent=intent,
            session=session,
            spans=spans,
            emit=emit,
        )
    )

    event_types = [m["event"]["event_type"] for m in messages if m.get("type") == "trace_event"]
    assert "intent_start" in event_types
    assert "call" in event_types
    assert "return" in event_types
    assert "intent_end" in event_types
