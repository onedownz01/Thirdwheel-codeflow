from backend.models.schema import FunctionType, Intent, IntentEvidence, ParsedFunction
from backend.parser.graph_builder import build_graph


def test_graph_builder_resolves_calls_and_merges_intents():
    f1 = ParsedFunction(
        id='a.py:handle:1',
        name='handle',
        file='a.py',
        type=FunctionType.HANDLER,
        calls=['do_work'],
    )
    f2 = ParsedFunction(
        id='a.py:do_work:2',
        name='do_work',
        file='a.py',
        type=FunctionType.SERVICE,
        calls=[],
    )

    i1 = Intent(
        id='intent:1',
        canonical_id='actions.submit',
        label='Submit',
        icon='▶',
        trigger='onClick',
        handler_fn_id='a.py:handle:0',
        source_file='a.py',
        group='Actions',
        confidence=0.7,
        evidence=[IntentEvidence(kind='ui_event', source_file='a.py', line=1, symbol='handle', excerpt='', weight=0.7)],
    )
    i2 = Intent(
        id='intent:2',
        canonical_id='actions.submit',
        label='Submit Form',
        icon='▶',
        trigger='form:action',
        handler_fn_id='a.py:handle:0',
        source_file='a.py',
        group='Actions',
        confidence=0.8,
        evidence=[IntentEvidence(kind='form_action', source_file='a.py', line=2, symbol='handle', excerpt='', weight=0.8)],
    )

    parsed = build_graph([f1, f2], [i1, i2], repo='demo/repo', branch='main')

    assert len(parsed.edges) == 1
    assert parsed.functions[0].calls == ['a.py:do_work:2']
    assert len(parsed.intents) == 1
    assert parsed.intents[0].status in {'observed', 'verified'}
