"""Intent metadata storage abstraction with memory and optional postgres backends."""
from __future__ import annotations

import os
from typing import Protocol

from ..models.schema import Intent, IntentOccurrence


class MetadataStore(Protocol):
    async def save_occurrence(self, occurrence: IntentOccurrence) -> None: ...

    async def upsert_intents(self, repo: str, intents: list[Intent]) -> None: ...

    async def get_intents(self, repo: str) -> list[Intent]: ...

    async def list_occurrences(
        self, repo: str, intent_id: str | None = None, limit: int = 200
    ) -> list[IntentOccurrence]: ...


class InMemoryMetadataStore:
    def __init__(self) -> None:
        self.occurrences: list[IntentOccurrence] = []
        self.intents_by_repo: dict[str, list[Intent]] = {}

    async def save_occurrence(self, occurrence: IntentOccurrence) -> None:
        self.occurrences.append(occurrence)

    async def upsert_intents(self, repo: str, intents: list[Intent]) -> None:
        self.intents_by_repo[repo.lower()] = intents

    async def get_intents(self, repo: str) -> list[Intent]:
        return self.intents_by_repo.get(repo.lower(), [])

    async def list_occurrences(
        self, repo: str, intent_id: str | None = None, limit: int = 200
    ) -> list[IntentOccurrence]:
        rows = [o for o in self.occurrences if o.repo.lower() == repo.lower()]
        if intent_id:
            rows = [o for o in rows if o.intent_id == intent_id]
        return rows[-limit:]


class PostgresMetadataStore:
    """Optional postgres implementation. If asyncpg unavailable, caller should fallback."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._pool = None

    async def connect(self) -> None:
        import asyncpg

        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.dsn)
            await self._init_schema()

    async def _init_schema(self) -> None:
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                create table if not exists intent_occurrences (
                    occurrence_id text primary key,
                    repo text not null,
                    intent_id text not null,
                    trace_id text not null,
                    session_id text not null,
                    outcome text not null,
                    latency_ms double precision not null,
                    started_at text not null
                );
                create index if not exists idx_occ_repo_intent_started
                    on intent_occurrences(repo, intent_id, started_at desc);
                create table if not exists intent_metadata (
                    repo text not null,
                    intent_id text not null,
                    payload jsonb not null,
                    primary key (repo, intent_id)
                );
                """
            )

    async def save_occurrence(self, occurrence: IntentOccurrence) -> None:
        await self.connect()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                insert into intent_occurrences
                (occurrence_id, repo, intent_id, trace_id, session_id, outcome, latency_ms, started_at)
                values ($1,$2,$3,$4,$5,$6,$7,$8)
                on conflict (occurrence_id) do nothing
                """,
                occurrence.occurrence_id,
                occurrence.repo,
                occurrence.intent_id,
                occurrence.trace_id,
                occurrence.session_id,
                occurrence.outcome,
                occurrence.latency_ms,
                occurrence.started_at,
            )

    async def upsert_intents(self, repo: str, intents: list[Intent]) -> None:
        await self.connect()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for intent in intents:
                    await conn.execute(
                        """
                        insert into intent_metadata (repo, intent_id, payload)
                        values ($1, $2, $3::jsonb)
                        on conflict (repo, intent_id) do update
                        set payload = excluded.payload
                        """,
                        repo,
                        intent.id,
                        intent.model_dump_json(),
                    )

    async def get_intents(self, repo: str) -> list[Intent]:
        await self.connect()
        assert self._pool is not None
        out: list[Intent] = []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                select payload
                from intent_metadata
                where repo = $1
                """,
                repo.lower(),
            )
            for row in rows:
                payload = row["payload"]
                if isinstance(payload, str):
                    out.append(Intent.model_validate_json(payload))
                else:
                    out.append(Intent.model_validate(payload))
        return out

    async def list_occurrences(
        self, repo: str, intent_id: str | None = None, limit: int = 200
    ) -> list[IntentOccurrence]:
        await self.connect()
        assert self._pool is not None
        query = """
            select occurrence_id, repo, intent_id, trace_id, session_id, outcome, latency_ms, started_at
            from intent_occurrences
            where repo = $1
        """
        params: list = [repo.lower()]
        if intent_id:
            query += " and intent_id = $2"
            params.append(intent_id)
        query += f" order by started_at desc limit {int(limit)}"

        out: list[IntentOccurrence] = []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            for row in rows:
                out.append(
                    IntentOccurrence(
                        occurrence_id=row["occurrence_id"],
                        repo=row["repo"],
                        intent_id=row["intent_id"],
                        trace_id=row["trace_id"],
                        session_id=row["session_id"],
                        outcome=row["outcome"],
                        latency_ms=row["latency_ms"],
                        started_at=row["started_at"],
                    )
                )
        return out



def create_metadata_store() -> MetadataStore:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        return InMemoryMetadataStore()

    try:
        return PostgresMetadataStore(dsn)
    except Exception:
        return InMemoryMetadataStore()
