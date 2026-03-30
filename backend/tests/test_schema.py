from backend.models.schema import (
    ApiEnvelope,
    FixRequest,
    Intent,
    IntentEvidence,
    ParsedFunction,
    ParsedRepo,
    TraceEvent,
    TraceSession,
)


def test_schema_models_roundtrip():
    fn = ParsedFunction(id="a:b:1", name="b", file="a.py", type="other")
    evidence = IntentEvidence(kind="ui_event", weight=0.7)
    intent = Intent(
        id="intent:1",
        canonical_id="auth.signup.submit",
        label="Sign Up",
        icon="👤",
        trigger="onSubmit",
        handler_fn_id="App.tsx:handleSubmit:12",
        source_file="App.tsx",
        group="Auth",
        evidence=[evidence],
        confidence=0.8,
    )
    repo = ParsedRepo(repo="owner/repo", branch="main", functions=[fn], intents=[intent], edges=[], file_count=1, parsed_at="now")
    session = TraceSession(session_id="s1", intent_id="intent:1", intent_label="Sign Up")
    event = TraceEvent(event_type="call", fn_id="a:b:1", fn_name="b", file="a.py", line=1, timestamp_ms=0.1)
    session.events.append(event)

    req = FixRequest(session_id="s1", error_fn_id="a:b:1", trace_session=session, parsed_repo=repo)
    env = ApiEnvelope(data=req.model_dump())

    assert env.success is True
    assert repo.intents[0].canonical_id == "auth.signup.submit"
    assert session.events[0].event_type == "call"
