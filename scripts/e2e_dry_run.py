#!/usr/bin/env python3
"""End-to-end dry run for CodeFlow against a public repository."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from urllib.parse import urlparse

import httpx
import websockets


def normalize_ws_base(http_base: str) -> str:
    parsed = urlparse(http_base)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}"


async def collect_ws_events(ws_url: str, timeout_s: float = 20.0) -> dict:
    events = []
    warnings = []
    started = time.time()

    async with websockets.connect(ws_url) as ws:
        while time.time() - started < timeout_s:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout_s)
            msg = json.loads(raw)
            msg_type = msg.get("type")
            if msg_type == "trace_event":
                events.append(msg.get("event", {}))
            elif msg_type == "trace_warning":
                warnings.append(msg.get("warning", "unknown warning"))
            elif msg_type == "trace_complete":
                break
            elif msg_type == "trace_error":
                raise RuntimeError(f"Trace websocket failed: {msg.get('error')}")

    return {"events": events, "warnings": warnings}


async def dry_run(repo: str, base_url: str) -> None:
    ws_base = normalize_ws_base(base_url)
    async with httpx.AsyncClient(base_url=base_url, timeout=90) as client:
        parse_res = await client.post("/parse", json={"repo": repo})
        parse_res.raise_for_status()
        parse_body = parse_res.json()
        parsed = parse_body["data"]
        intents = parsed.get("intents", [])
        if not intents:
            raise RuntimeError("No intents extracted from repository")

        intent = intents[0]
        print(
            f"[dry-run] parsed repo={parsed['repo']} functions={len(parsed['functions'])} "
            f"edges={len(parsed['edges'])} intents={len(intents)}"
        )
        print(
            f"[dry-run] selected intent={intent['label']} "
            f"trigger={intent['trigger']} confidence={intent['confidence']}"
        )

        start_res = await client.post(
            "/trace/start",
            json={"repo": repo, "intent_id": intent["id"], "mode": "simulation"},
        )
        start_res.raise_for_status()
        start_data = start_res.json()["data"]
        ws_url = f"{ws_base}{start_data['ws_path']}"
        sim_trace = await collect_ws_events(ws_url)
        print(
            f"[dry-run] simulation trace events={len(sim_trace['events'])} "
            f"warnings={len(sim_trace['warnings'])}"
        )
        if len(sim_trace["events"]) < 2:
            raise RuntimeError("Simulation trace produced too few events")

        otel_start = await client.post(
            "/trace/start",
            json={"repo": repo, "intent_id": intent["id"], "mode": "otel"},
        )
        otel_start.raise_for_status()
        otel_data = otel_start.json()["data"]
        session_id = otel_data["session_id"]
        trace_id = otel_data["trace_id"]

        now = time.time() * 1000
        spans = [
            {
                "trace_id": trace_id,
                "span_id": "1111111111111111",
                "parent_span_id": otel_data.get("root_span_id"),
                "name": "intent.entry",
                "service_name": "frontend",
                "start_time_ms": now,
                "end_time_ms": now + 32,
                "attributes": {"inputs": {"repo": repo}, "outputs": {"status": "ok"}},
                "status": "ok",
            },
            {
                "trace_id": trace_id,
                "span_id": "2222222222222222",
                "parent_span_id": "1111111111111111",
                "name": "service.call",
                "service_name": "backend",
                "start_time_ms": now + 8,
                "end_time_ms": now + 55,
                "attributes": {
                    "code.function": "service_call",
                    "inputs": {"intent": intent["label"]},
                    "outputs": {"result": "ok"},
                },
                "status": "ok",
            },
        ]

        ingest = await client.post(
            "/trace/ingest",
            json={"session_id": session_id, "trace_id": trace_id, "spans": spans},
        )
        ingest.raise_for_status()
        ingest_data = ingest.json()["data"]
        print(
            f"[dry-run] otel ingest accepted={ingest_data['accepted']} "
            f"stored_for_session={ingest_data['stored_for_session']}"
        )

        otel_ws_url = f"{ws_base}{otel_data['ws_path']}"
        otel_trace = await collect_ws_events(otel_ws_url)
        print(
            f"[dry-run] otel trace events={len(otel_trace['events'])} "
            f"warnings={len(otel_trace['warnings'])}"
        )
        if len(otel_trace["events"]) < 3:
            raise RuntimeError("OTel trace bridge produced too few events")

        print("[dry-run] PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run end-to-end CodeFlow dry run")
    parser.add_argument("--repo", default="tiangolo/fastapi", help="GitHub repo in owner/repo form")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    args = parser.parse_args()

    try:
        asyncio.run(dry_run(args.repo, args.base_url))
        return 0
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"[dry-run] FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
