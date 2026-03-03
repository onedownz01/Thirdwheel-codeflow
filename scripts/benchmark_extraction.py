#!/usr/bin/env python3
"""Extraction benchmark harness for recall-first intent parsing."""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.parser.ast_parser import parse_repository
from backend.parser.github_fetcher import MAX_FILES, fetch_repo


async def benchmark_repo(repo: str, token: str | None = None) -> dict:
    t0 = time.perf_counter()
    contents, branch = await fetch_repo(repo, token=token)
    t1 = time.perf_counter()
    parsed = parse_repository(repo, branch, contents)
    t2 = time.perf_counter()

    return {
        'repo': repo,
        'branch': branch,
        'files_fetched': len(contents),
        'functions': len(parsed.functions),
        'intents': len(parsed.intents),
        'fetch_ms': round((t1 - t0) * 1000, 1),
        'parse_ms': round((t2 - t1) * 1000, 1),
        'total_ms': round((t2 - t0) * 1000, 1),
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repos', nargs='+', required=True, help='owner/repo list')
    parser.add_argument('--token', default=None)
    parser.add_argument('--json-out', default='')
    parser.add_argument('--max-files', type=int, default=MAX_FILES)
    args = parser.parse_args()

    import backend.parser.github_fetcher as github_fetcher

    github_fetcher.MAX_FILES = max(10, min(args.max_files, 1000))

    results = []
    for repo in args.repos:
        try:
            results.append(await benchmark_repo(repo, token=args.token))
        except Exception as exc:
            results.append({'repo': repo, 'error': str(exc)})

    totals = [r['total_ms'] for r in results if 'total_ms' in r]
    summary = {
        'results': results,
        'p50_total_ms': round(statistics.median(totals), 1) if totals else None,
        'p95_total_ms': round(sorted(totals)[int(max(0, len(totals) * 0.95 - 1))], 1) if totals else None,
    }

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(summary, indent=2), encoding='utf-8')

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
