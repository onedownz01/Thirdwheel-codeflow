"""GitHub repository fetcher with conservative limits for local-first parsing."""
from __future__ import annotations

import asyncio
from typing import Callable, Optional

import httpx

SKIP_DIRS = {
    "node_modules",
    "vendor",
    ".git",
    "dist",
    "build",
    "__pycache__",
    ".next",
    "coverage",
    ".nyc_output",
    "target",
    "out",
    ".cache",
    "venv",
    "env",
    ".venv",
    "migrations",
}

CODE_EXTENSIONS = {
    "js",
    "jsx",
    "ts",
    "tsx",
    "py",
    "vue",
    "svelte",
}

MAX_FILES = 120
MAX_FILE_SIZE_BYTES = 160_000


async def fetch_repo(
    repo: str,
    token: Optional[str] = None,
    progress_callback: Optional[Callable[[int, str], asyncio.Future]] = None,
) -> tuple[dict[str, str], str]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
        if progress_callback:
            await progress_callback(5, "Fetching repository metadata")

        repo_res = await client.get(f"https://api.github.com/repos/{repo}")
        if repo_res.status_code == 404:
            raise ValueError(f"Repository '{repo}' not found or inaccessible")
        if repo_res.status_code == 403:
            raise ValueError("GitHub API rate limit exceeded; provide a token")
        repo_res.raise_for_status()

        branch = repo_res.json().get("default_branch", "main")

        if progress_callback:
            await progress_callback(15, f"Fetching source tree ({branch})")

        tree_res = await client.get(
            f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
        )
        tree_res.raise_for_status()
        tree_data = tree_res.json()

        files: list[str] = []
        for item in tree_data.get("tree", []):
            if item.get("type") != "blob":
                continue
            path = item.get("path", "")
            parts = path.split("/")
            if any(part in SKIP_DIRS for part in parts):
                continue

            ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
            if ext not in CODE_EXTENSIONS:
                continue
            if item.get("size", 0) > MAX_FILE_SIZE_BYTES:
                continue
            files.append(path)

        files = sorted(files, key=_priority)[:MAX_FILES]

        if progress_callback:
            await progress_callback(30, f"Downloading {len(files)} candidate files")

        semaphore = asyncio.Semaphore(12)
        contents: dict[str, str] = {}

        async def fetch_file(path: str, idx: int) -> None:
            async with semaphore:
                try:
                    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
                    res = await client.get(raw_url)
                    if res.status_code == 200:
                        contents[path] = res.text[:MAX_FILE_SIZE_BYTES]
                    if progress_callback and idx % 10 == 0:
                        pct = 30 + int((idx / max(len(files), 1)) * 60)
                        await progress_callback(min(pct, 90), f"Read {path}")
                except Exception:
                    return

        await asyncio.gather(*[fetch_file(path, idx) for idx, path in enumerate(files)])

        if progress_callback:
            await progress_callback(100, "Repository fetch complete")

        return contents, branch



def _priority(path: str) -> tuple[int, str]:
    p = path.lower()
    if any(x in p for x in ("page", "route", "controller", "handler", "app.", "main.")):
        return (0, p)
    if any(x in p for x in ("component", "view", "screen")):
        return (1, p)
    if any(x in p for x in ("service", "api", "client", "db", "model")):
        return (2, p)
    return (3, p)
