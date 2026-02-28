"""AI fix suggestion service with strict sanitization-first behavior."""
from __future__ import annotations

import os

from ..models.schema import FixRequest, FixSuggestion


async def suggest_fix(req: FixRequest) -> FixSuggestion:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_suggestion(req)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = _build_prompt(req)
        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text if response.content else ""
        explanation = _extract(text, "EXPLANATION", "FIX") or "Unable to parse model explanation"
        fix = _extract(text, "FIX", "CODE") or "Unable to parse fix recommendation"
        code = _extract(text, "CODE", "CONFIDENCE")
        confidence_raw = (_extract(text, "CONFIDENCE", None) or "medium").strip().lower()
        confidence = confidence_raw if confidence_raw in {"high", "medium", "low"} else "medium"

        return FixSuggestion(
            explanation=explanation,
            fix=fix,
            code_diff=code if code and len(code) > 6 else None,
            confidence=confidence,
        )
    except Exception:
        return _fallback_suggestion(req)



def _build_prompt(req: FixRequest) -> str:
    session = req.trace_session
    parsed = req.parsed_repo
    intent = next((i for i in parsed.intents if i.id == session.intent_id), None)
    error_event = next((e for e in session.events if e.event_type == "error"), None)

    chain_lines = []
    for event in session.events:
        if event.event_type != "call":
            continue
        in_values = ", ".join(
            f"{v.name}={'••••••' if v.is_sensitive else v.value}" for v in event.inputs
        )
        chain_lines.append(f"- {event.fn_name}({in_values}) @ {event.file}:{event.line}")

    chain = "\n".join(chain_lines) if chain_lines else "- no call events"

    return f"""
You are debugging a runtime failure from an intent-anchored trace.

INTENT: {intent.label if intent else 'unknown'}
SESSION: {session.session_id}
TRACE PATH:
{chain}

ERROR:
- function: {error_event.fn_name if error_event else 'unknown'}
- type: {error_event.error_type if error_event else 'unknown'}
- message: {error_event.error if error_event else 'unknown'}
- file: {error_event.file if error_event else 'unknown'}:{error_event.error_line if error_event else 'unknown'}

Return exactly this structure:
EXPLANATION: ...
FIX: ...
CODE: ...
CONFIDENCE: high|medium|low
""".strip()



def _fallback_suggestion(req: FixRequest) -> FixSuggestion:
    session = req.trace_session
    error_event = next((e for e in session.events if e.event_type == "error"), None)

    if not error_event:
        return FixSuggestion(
            explanation="No explicit error event was recorded in this trace session.",
            fix="Re-run the trace with runtime lane enabled and inspect event-level inputs/outputs.",
            confidence="low",
        )

    return FixSuggestion(
        explanation=(
            f"Execution failed in {error_event.fn_name} with {error_event.error_type}: "
            f"{error_event.error}."
        ),
        fix=(
            "Inspect argument assumptions and null/shape checks at the failing line, then add guard "
            "conditions before downstream calls."
        ),
        code_diff=None,
        confidence="medium",
    )



def _extract(text: str, start_label: str, end_label: str | None) -> str:
    import re

    pattern = rf"{start_label}:\s*(.*?)"
    if end_label:
        pattern += rf"(?=\n{end_label}:)"
    else:
        pattern += r"$"

    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""
