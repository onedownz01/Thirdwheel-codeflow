from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any
from urllib.parse import parse_qs

import httpx
from fastapi import Body, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .ai.fix_suggester import suggest_fix
from pydantic import BaseModel
from .models.schema import (
    SCHEMA_VERSION,
    ApiEnvelope,
    FixRequest,
    IngestedSpan,
    IntentOccurrence,
    ParsedRepo,
    ParseRequest,
    TraceEvent,
    TraceEventType,
    TraceIngestRequest,
    TraceMode,
    TraceSession,
    TraceStartRequest,
)
from .parser.ast_parser import parse_repository
from .parser.github_fetcher import fetch_repo
from .services.intent_fusion import rank_intents, update_occurrence_stats
from .services.metadata_store import create_metadata_store
from .services.otel import get_otel_state, setup_otel
from .services.trace_context import is_otel_enabled, new_span_id, new_trace_id, parse_traceparent
from .tracer.correlator import Correlator
from .tracer.otel_bridge import emit_otel_span_trace
from .tracer.process_runner import ProcessRunner
from .tracer.simulator import run_simulated_trace
from .tracer.websocket_emitter import WSEmitter

app = FastAPI(title="CodeFlow API", version=SCHEMA_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_otel(app)

repo_cache: dict[str, ParsedRepo] = {}
trace_sessions: dict[str, TraceSession] = {}
pending_trace_requests: dict[str, dict[str, Any]] = {}
ingested_spans_by_trace: dict[str, list[IngestedSpan]] = {}
ingested_spans_by_session: dict[str, list[IngestedSpan]] = {}
metadata_store = create_metadata_store()

# Live tracer state
# key = repo_key, value = ProcessRunner for the running traced process
active_runners: dict[str, ProcessRunner] = {}
# key = session_id, value = list of raw event dicts waiting to be correlated
live_raw_events: dict[str, list[dict]] = {}
# key = session_id, value = asyncio.Event — set when first batch of live events arrives
live_event_signals: dict[str, asyncio.Event] = {}



def envelope(data: Any = None, success: bool = True, error: str | None = None) -> ApiEnvelope:
    return ApiEnvelope(schema_version=SCHEMA_VERSION, success=success, error=error, data=data)


async def _send_ws_error(emitter: WSEmitter, session_id: str, error: str) -> None:
    await emitter.emit(
        {
            "schema_version": SCHEMA_VERSION,
            "session_id": session_id,
            "timestamp_ms": 0,
            "type": "trace_error",
            "error": error,
        }
    )


def _normalize_repo_input(repo: str) -> str:
    raw = repo.strip()
    if raw.endswith(".git"):
        raw = raw[:-4]
    m = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:/)?$", raw, re.IGNORECASE)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return raw


def _coerce_parse_request(payload: Any) -> ParseRequest:
    candidate = payload
    if isinstance(candidate, (bytes, bytearray)):
        candidate = candidate.decode("utf-8", errors="ignore")
    if isinstance(candidate, str):
        stripped = candidate.strip()
        try:
            candidate = json.loads(stripped)
        except json.JSONDecodeError as exc:
            parsed_qs = parse_qs(stripped, keep_blank_values=True)
            if parsed_qs.get("repo"):
                candidate = {
                    "repo": parsed_qs["repo"][0],
                    "token": parsed_qs.get("token", [None])[0],
                }
            else:
                raise HTTPException(status_code=422, detail=f"Invalid JSON string body: {exc}") from exc
    if isinstance(candidate, dict) and "repo" not in candidate and len(candidate) == 1:
        # Handles malformed form/body payloads shaped like {'{"repo":"owner/repo"}': ''}
        only_key = next(iter(candidate.keys()))
        if isinstance(only_key, str) and only_key.strip().startswith("{"):
            try:
                parsed_key = json.loads(only_key.strip())
                if isinstance(parsed_key, dict):
                    candidate = parsed_key
            except json.JSONDecodeError:
                pass
    if not isinstance(candidate, dict):
        raise HTTPException(status_code=422, detail="Request body must be an object with 'repo'.")
    try:
        return ParseRequest.model_validate(candidate)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _coerce_trace_start_request(payload: Any) -> TraceStartRequest:
    candidate = payload
    if isinstance(candidate, (bytes, bytearray)):
        candidate = candidate.decode("utf-8", errors="ignore")
    if isinstance(candidate, str):
        stripped = candidate.strip()
        try:
            candidate = json.loads(stripped)
        except json.JSONDecodeError as exc:
            parsed_qs = parse_qs(stripped, keep_blank_values=True)
            if parsed_qs.get("repo") and parsed_qs.get("intent_id"):
                candidate = {
                    "repo": parsed_qs["repo"][0],
                    "intent_id": parsed_qs["intent_id"][0],
                    "mode": parsed_qs.get("mode", ["simulation"])[0],
                    "simulate_error_at_step": parsed_qs.get("simulate_error_at_step", [None])[0],
                }
            else:
                raise HTTPException(status_code=422, detail=f"Invalid JSON string body: {exc}") from exc

    if isinstance(candidate, dict) and "repo" not in candidate and len(candidate) == 1:
        only_key = next(iter(candidate.keys()))
        if isinstance(only_key, str) and only_key.strip().startswith("{"):
            try:
                parsed_key = json.loads(only_key.strip())
                if isinstance(parsed_key, dict):
                    candidate = parsed_key
            except json.JSONDecodeError:
                pass

    if not isinstance(candidate, dict):
        raise HTTPException(status_code=422, detail="Request body must include repo and intent_id.")

    try:
        return TraceStartRequest.model_validate(candidate)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/health")
async def health() -> ApiEnvelope:
    return envelope(
        {
            "status": "ok",
            "schema_version": SCHEMA_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "otel": get_otel_state(),
        }
    )


@app.get("/telemetry/status")
async def telemetry_status() -> ApiEnvelope:
    return envelope({"otel": get_otel_state(), "runtime_mode": "lane_a+lane_b_ready"})


@app.post("/parse")
async def parse_repo(payload: Annotated[Any, Body()]) -> ApiEnvelope:
    req = _coerce_parse_request(payload)
    normalized_repo = _normalize_repo_input(req.repo)
    key = normalized_repo.lower().strip()
    if key in repo_cache:
        return envelope(repo_cache[key].model_dump())

    try:
        contents, branch = await fetch_repo(normalized_repo, req.token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"GitHub fetch failed: {exc}") from exc

    if not contents:
        raise HTTPException(status_code=400, detail="No eligible code files discovered")

    parsed = parse_repository(normalized_repo, branch, contents)
    if not parsed.functions:
        raise HTTPException(status_code=400, detail="No functions parsed from repository")

    repo_cache[key] = parsed
    await metadata_store.upsert_intents(key, parsed.intents)
    return envelope(parsed.model_dump())


@app.get("/intents")
async def get_intents(repo: str) -> ApiEnvelope:
    key = _normalize_repo_input(repo).lower().strip()
    parsed = repo_cache.get(key)

    if parsed:
        ranked = rank_intents(parsed.intents)
        return envelope(
            {
                "repo": parsed.repo,
                "branch": parsed.branch,
                "count": len(ranked),
                "intents": [intent.model_dump() for intent in ranked],
                "source": "cache",
            }
        )

    stored = await metadata_store.get_intents(key)
    if not stored:
        raise HTTPException(status_code=404, detail="Repository is not parsed. Call /parse first.")

    ranked = rank_intents(stored)
    return envelope(
        {
            "repo": key,
            "branch": "unknown",
            "count": len(ranked),
            "intents": [intent.model_dump() for intent in ranked],
            "source": "metadata_store",
        }
    )


@app.get("/occurrences")
async def get_occurrences(repo: str, intent_id: str | None = None, limit: int = 100) -> ApiEnvelope:
    normalized_repo = _normalize_repo_input(repo)
    rows = await metadata_store.list_occurrences(
        repo=normalized_repo, intent_id=intent_id, limit=max(1, min(limit, 1000))
    )
    return envelope(
        {
            "repo": normalized_repo,
            "intent_id": intent_id,
            "count": len(rows),
            "occurrences": [r.model_dump() for r in rows],
        }
    )


@app.post("/trace/start")
async def trace_start(payload: Annotated[Any, Body()], request: Request) -> ApiEnvelope:
    req = _coerce_trace_start_request(payload)
    normalized_repo = _normalize_repo_input(req.repo)
    key = normalized_repo.lower().strip()
    parsed = repo_cache.get(key)
    if not parsed:
        raise HTTPException(status_code=404, detail="Repository is not parsed. Call /parse first.")

    intent = next((i for i in parsed.intents if i.id == req.intent_id), None)
    if not intent:
        raise HTTPException(status_code=404, detail=f"Intent '{req.intent_id}' not found")

    incoming_ctx = parse_traceparent(request.headers.get("traceparent"))
    trace_id = incoming_ctx.trace_id if incoming_ctx else new_trace_id()
    parent_span_id = incoming_ctx.parent_span_id if incoming_ctx else None
    root_span_id = new_span_id()

    session_id = str(uuid.uuid4())
    session_mode = req.mode
    warnings: list[str] = []

    if req.mode == TraceMode.OTel and not is_otel_enabled():
        warnings.append(
            "OTEL_EXPORTER_OTLP_ENDPOINT is unset. Waiting for external spans via /trace/ingest; "
            "if none arrive, websocket trace will fall back to simulation."
        )

    session = TraceSession(
        session_id=session_id,
        intent_id=intent.id,
        intent_label=intent.label,
        trace_mode=session_mode,
        trace_id=trace_id,
        root_span_id=root_span_id,
        parent_span_id=parent_span_id,
        status="queued",
    )

    trace_sessions[session_id] = session
    pending_trace_requests[session_id] = {
        "repo": key,
        "intent_id": intent.id,
        "mode": session_mode,
        "simulate_error_at_step": req.simulate_error_at_step,
        "warnings": warnings,
    }

    return envelope(
        {
            "session_id": session_id,
            "trace_id": trace_id,
            "root_span_id": root_span_id,
            "parent_span_id": parent_span_id,
            "ws_path": f"/ws/trace/{session_id}",
            "mode": session_mode,
            "warnings": warnings,
            "simulate_error_at_step": req.simulate_error_at_step,
        }
    )


@app.get("/trace/{session_id}")
async def trace_summary(session_id: str) -> ApiEnvelope:
    session = trace_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Trace session not found")

    event_count = len(session.events)
    error_count = len([e for e in session.events if e.event_type == "error"])

    return envelope(
        {
            "session": session.model_dump(),
            "event_count": event_count,
            "error_count": error_count,
        }
    )


@app.post("/trace/ingest")
async def trace_ingest(req: TraceIngestRequest) -> ApiEnvelope:
    if not req.spans:
        raise HTTPException(status_code=400, detail="No spans provided")

    trace_key = req.trace_id.lower().strip()
    by_trace = ingested_spans_by_trace.setdefault(trace_key, [])
    by_trace.extend(req.spans)

    if req.session_id:
        by_session = ingested_spans_by_session.setdefault(req.session_id, [])
        by_session.extend(req.spans)

    return envelope(
        {
            "accepted": len(req.spans),
            "trace_id": trace_key,
            "session_id": req.session_id,
            "stored_for_trace": len(by_trace),
            "stored_for_session": len(ingested_spans_by_session.get(req.session_id, []))
            if req.session_id
            else 0,
        }
    )


@app.post("/fix")
async def get_fix(req: FixRequest) -> ApiEnvelope:
    suggestion = await suggest_fix(req)
    return envelope(suggestion.model_dump())


@app.delete("/cache/{repo:path}")
async def clear_cache(repo: str) -> ApiEnvelope:
    normalized_repo = _normalize_repo_input(repo)
    repo_cache.pop(normalized_repo.lower(), None)
    return envelope({"cleared": True, "repo": normalized_repo})


@app.websocket("/ws/trace/{session_id}")
async def trace_websocket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    emitter = WSEmitter(websocket)

    request = pending_trace_requests.get(session_id)
    session = trace_sessions.get(session_id)

    if not request or not session:
        await _send_ws_error(emitter, session_id, "No pending trace request for this session.")
        await websocket.close(code=1008)
        return

    key = request["repo"]
    intent_id = request["intent_id"]
    parsed = repo_cache.get(key)
    if not parsed:
        await _send_ws_error(emitter, session_id, "Repository cache not available.")
        await websocket.close(code=1008)
        return

    intent = next((i for i in parsed.intents if i.id == intent_id), None)
    if not intent:
        await _send_ws_error(emitter, session_id, "Intent no longer present in parsed repo.")
        await websocket.close(code=1008)
        return

    warnings = request.get("warnings") or []
    for w in warnings:
        await emitter.emit(
            {
                "schema_version": SCHEMA_VERSION,
                "session_id": session_id,
                "timestamp_ms": 0,
                "type": "trace_warning",
                "warning": w,
            }
        )

    try:
        if session.trace_mode == TraceMode.OTel:
            spans = ingested_spans_by_session.pop(session_id, None)
            if not spans:
                spans = ingested_spans_by_trace.pop(session.trace_id.lower().strip(), None)

            if spans:
                occurrence = await emit_otel_span_trace(
                    parsed=parsed,
                    intent=intent,
                    session=session,
                    spans=spans,
                    emit=emitter.emit,
                )
            else:
                await emitter.emit(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "session_id": session_id,
                        "timestamp_ms": 0,
                        "type": "trace_warning",
                        "warning": "No ingested OTel spans found for this trace; falling back to simulation.",
                    }
                )
                occurrence = await run_simulated_trace(
                    parsed,
                    intent,
                    session,
                    emitter.emit,
                    simulate_error_at_step=request.get("simulate_error_at_step"),
                    parent_span_id=session.parent_span_id,
                )
        else:
            occurrence = await run_simulated_trace(
                parsed,
                intent,
                session,
                emitter.emit,
                simulate_error_at_step=request.get("simulate_error_at_step"),
                parent_span_id=session.parent_span_id,
            )
        await metadata_store.save_occurrence(occurrence)

        updated_intent = update_occurrence_stats(intent, session)
        for idx, existing in enumerate(parsed.intents):
            if existing.id == updated_intent.id:
                parsed.intents[idx] = updated_intent
                break
        await metadata_store.upsert_intents(key, parsed.intents)

        pending_trace_requests.pop(session_id, None)
        await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return
    except Exception as exc:
        session.status = "error"
        await _send_ws_error(emitter, session_id, str(exc))


class RunnerStartRequest(BaseModel):
    repo: str
    command: list[str]          # e.g. ["python", "-m", "uvicorn", "main:app"]
    project_root: str           # absolute local path to the cloned repo
    session_id: str             # the intent session to associate with this process


@app.post("/runner/start")
async def runner_start(req: RunnerStartRequest) -> ApiEnvelope:
    """
    Launch the user's Python app with the CodeFlow tracer injected.
    The process runs until /runner/stop is called or it exits on its own.
    """
    key = _normalize_repo_input(req.repo).lower().strip()
    if not repo_cache.get(key):
        raise HTTPException(status_code=404, detail="Repository not parsed. Call /parse first.")

    # Stop any existing runner for this repo
    existing = active_runners.get(key)
    if existing and existing.is_running:
        await existing.stop()

    ingest_ws = "ws://127.0.0.1:8000/ws/tracer/ingest"
    runner = ProcessRunner(
        project_root=req.project_root,
        repo_key=key,
        ingest_ws_url=ingest_ws,
    )
    pid = await runner.start(req.command, req.session_id)
    active_runners[key] = runner

    # Pre-allocate event buffers for this session
    live_raw_events[req.session_id] = []
    live_event_signals[req.session_id] = asyncio.Event()

    return envelope({
        "pid": pid,
        "repo": key,
        "session_id": req.session_id,
        "ingest_ws": ingest_ws,
        "status": "running",
    })


@app.post("/runner/stop")
async def runner_stop(repo: str) -> ApiEnvelope:
    key = _normalize_repo_input(repo).lower().strip()
    runner = active_runners.get(key)
    if not runner:
        raise HTTPException(status_code=404, detail="No active runner for this repo.")
    await runner.stop()
    return envelope({"repo": key, "status": "stopped"})


@app.get("/runner/status")
async def runner_status(repo: str) -> ApiEnvelope:
    key = _normalize_repo_input(repo).lower().strip()
    runner = active_runners.get(key)
    if not runner:
        return envelope({"repo": key, "status": "not_started", "pid": None})
    return envelope({
        "repo": key,
        "status": "running" if runner.is_running else "exited",
        "pid": runner.pid,
    })


@app.websocket("/ws/tracer/ingest")
async def tracer_ingest_ws(websocket: WebSocket) -> None:
    """
    WebSocket endpoint that receives raw event batches from the in-process tracer.
    The tracer (python_sys_tracer.py running inside the user's app) connects here
    and sends JSON payloads of the form:
        {"session_id": "...", "events": [{raw_event}, ...]}

    This handler:
    1. Accepts the connection
    2. Buffers raw events into live_raw_events[session_id]
    3. Signals any waiting /ws/trace/{session_id} handler that events have arrived
    """
    await websocket.accept()
    try:
        async for message in websocket.iter_text():
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                continue

            session_id: str = payload.get("session_id", "")
            raw_events: list[dict] = payload.get("events") or []

            if not session_id or not raw_events:
                continue

            # Only buffer when /ws/trace/live/{session_id} is actively listening.
            # Discard if no listener has pre-allocated the buffer (prevents memory leak).
            if session_id not in live_raw_events:
                continue
            live_raw_events[session_id].extend(raw_events)

            # Signal the WS trace handler that new events are available
            sig = live_event_signals.get(session_id)
            if sig:
                sig.set()

    except WebSocketDisconnect:
        pass


@app.websocket("/ws/trace/live/{session_id}")
async def trace_live_websocket(websocket: WebSocket, session_id: str) -> None:
    """
    Like /ws/trace/{session_id} but for live tracer mode.
    Waits for real events from the tracer, correlates them, and streams
    TraceEvent frames to the frontend — same wire format as the simulator.
    """
    await websocket.accept()
    emitter = WSEmitter(websocket)

    session = trace_sessions.get(session_id)
    request = pending_trace_requests.get(session_id)

    if not session or not request:
        await _send_ws_error(emitter, session_id, "No pending trace session found.")
        await websocket.close(code=1008)
        return

    key = request["repo"]
    parsed = repo_cache.get(key)
    intent = next((i for i in parsed.intents if i.id == request["intent_id"]), None) if parsed else None

    if not parsed or not intent:
        await _send_ws_error(emitter, session_id, "Repo or intent no longer cached.")
        await websocket.close(code=1008)
        return

    project_root = request.get("project_root", "")
    correlator = Correlator(parsed, project_root)

    # Ensure event buffers exist
    if session_id not in live_raw_events:
        live_raw_events[session_id] = []
    if session_id not in live_event_signals:
        live_event_signals[session_id] = asyncio.Event()

    session.status = "running"
    sequence = 0

    # Emit intent_start frame
    intent_start = TraceEvent(
        event_type=TraceEventType.INTENT_START,
        fn_id=intent.handler_fn_id,
        fn_name=intent.label,
        file=intent.source_file,
        line=0,
        timestamp_ms=0.0,
        sequence=sequence,
        trace_id=session.trace_id,
        span_id=session.root_span_id or uuid.uuid4().hex[:16],
        service_name="codeflow-live",
        attributes={"intent_id": intent.id},
    )
    sequence += 1
    await emitter.emit(_live_frame(session_id, "trace_event", intent_start.model_dump()))

    emitted_count = 0
    already_sent = 0

    try:
        # Stream events as they arrive. Stop when:
        # - WebSocket disconnects
        # - 30s timeout with no new events (intent window closed)
        deadline = 30.0
        idle = 0.0

        while idle < deadline:
            sig = live_event_signals[session_id]
            try:
                await asyncio.wait_for(asyncio.shield(sig.wait()), timeout=1.0)
                sig.clear()
            except asyncio.TimeoutError:
                idle += 1.0
                if not live_raw_events.get(session_id):
                    continue
                # If there are pending events even without a signal, process them
            else:
                idle = 0.0  # reset idle timer on any activity

            raw_batch = live_raw_events.get(session_id, [])
            new_events = raw_batch[already_sent:]
            already_sent += len(new_events)

            for raw in new_events:
                te = correlator.correlate(raw, session, sequence)
                if te is None:
                    continue
                sequence += 1
                session.events.append(te)
                await emitter.emit(_live_frame(session_id, "trace_event", te.model_dump()))
                emitted_count += 1

    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup
        live_raw_events.pop(session_id, None)
        live_event_signals.pop(session_id, None)

        session.status = "success" if session.status == "running" else session.status
        session.total_duration_ms = float(
            session.events[-1].timestamp_ms if session.events else 0.0
        )

        await emitter.emit({
            "schema_version": SCHEMA_VERSION,
            "session_id": session_id,
            "timestamp_ms": session.total_duration_ms,
            "type": "trace_complete",
            "total_duration_ms": session.total_duration_ms,
            "event_count": emitted_count,
        })

        occurrence = IntentOccurrence(
            occurrence_id=str(uuid.uuid4()),
            repo=parsed.repo,
            intent_id=intent.id,
            trace_id=session.trace_id,
            session_id=session_id,
            outcome="error" if session.status == "error" else "success",
            latency_ms=session.total_duration_ms,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        await metadata_store.save_occurrence(occurrence)
        pending_trace_requests.pop(session_id, None)


def _live_frame(session_id: str, msg_type: str, payload: dict) -> dict:
    import time as _time
    return {
        "timestamp_ms": _time.time() * 1000,
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id,
        "type": msg_type,
        "event": payload,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
