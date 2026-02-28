import asyncio

from backend.models.schema import FunctionType, Intent, ParsedFunction, ParsedRepo, TraceSession
from backend.tracer.simulator import run_simulated_trace


async def _run():
    fn = ParsedFunction(id='f.py:entry:1', name='entry', file='f.py', type=FunctionType.HANDLER, line=1)
    intent = Intent(
        id='intent:1',
        canonical_id='actions.entry',
        label='Entry',
        icon='▶',
        trigger='onClick',
        handler_fn_id=fn.id,
        source_file='f.py',
        group='Actions',
        flow_ids=[fn.id],
    )
    parsed = ParsedRepo(repo='x/y', branch='main', functions=[fn], intents=[intent], edges=[], file_count=1, parsed_at='now')
    session = TraceSession(session_id='s1', intent_id=intent.id, intent_label=intent.label, trace_id='a' * 32)

    messages = []

    async def emit(msg):
        messages.append(msg)

    occurrence = await run_simulated_trace(parsed, intent, session, emit)
    return session, messages, occurrence


def test_simulator_emits_monotonic_sequences():
    session, messages, occurrence = asyncio.run(_run())

    events = [m['event'] for m in messages if m.get('type') == 'trace_event']
    seqs = [e['sequence'] for e in events]

    assert seqs == sorted(seqs)
    assert session.status == 'success'
    assert occurrence.outcome == 'success'
    assert any(e['event_type'] == 'intent_start' for e in events)
    assert any(e['event_type'] == 'intent_end' for e in events)
