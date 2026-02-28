from pathlib import Path

from backend.parser.js_parser import parse_js_file


FIXTURE = Path(__file__).parent / 'fixtures' / 'sample_ui.tsx'


def test_js_parser_extracts_multisignal_intents():
    content = FIXTURE.read_text(encoding='utf-8')
    functions, intents = parse_js_file('src/Signup.tsx', content)

    assert len(functions) >= 1
    canonical = {i.canonical_id for i in intents}
    kinds = {ev.kind for i in intents for ev in i.evidence}

    assert any('signup' in c or 'network' in c or 'navigation' in c for c in canonical)
    assert 'ui_event' in kinds
    assert 'form_action' in kinds
    assert 'router_transition' in kinds
