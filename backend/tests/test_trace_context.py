from backend.services.trace_context import (
    build_traceparent,
    new_span_id,
    new_trace_id,
    parse_traceparent,
)


def test_traceparent_roundtrip():
    trace_id = new_trace_id()
    span_id = new_span_id()
    header = build_traceparent(trace_id, span_id)
    parsed = parse_traceparent(header)

    assert parsed is not None
    assert parsed.trace_id == trace_id
    assert parsed.parent_span_id == span_id


def test_parse_invalid_traceparent():
    assert parse_traceparent('invalid') is None
    assert parse_traceparent('00-' + '0' * 32 + '-' + '0' * 16 + '-01') is None
