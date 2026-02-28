"""Intent ranking and enrichment helpers."""
from __future__ import annotations

from ..models.schema import Intent, IntentStatus, TraceSession



def rank_intents(intents: list[Intent]) -> list[Intent]:
    return sorted(
        intents,
        key=lambda i: (
            _status_score(i.status),
            i.failure_rate,
            i.frequency,
            i.confidence,
        ),
        reverse=True,
    )



def update_occurrence_stats(intent: Intent, session: TraceSession) -> Intent:
    intent.frequency += 1
    if session.status == "error":
        failures = round(intent.failure_rate * max(intent.frequency - 1, 0)) + 1
        intent.failure_rate = failures / intent.frequency
        intent.status = IntentStatus.OBSERVED
    else:
        failures = round(intent.failure_rate * max(intent.frequency - 1, 0))
        intent.failure_rate = failures / intent.frequency if intent.frequency else 0.0
        if intent.confidence >= 0.85:
            intent.status = IntentStatus.VERIFIED
        else:
            intent.status = IntentStatus.OBSERVED
    return intent



def _status_score(status: IntentStatus) -> int:
    if status == IntentStatus.VERIFIED:
        return 3
    if status == IntentStatus.OBSERVED:
        return 2
    return 1
