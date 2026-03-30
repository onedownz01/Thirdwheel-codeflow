"""GitHub repository fetcher with conservative limits for local-first parsing."""
from __future__ import annotations

import asyncio
import io
import os
import tarfile
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
    """Fetch relevant source files for a repository.

    Primary path uses GitHub API (fast, selective). If API quota is exhausted,
    it transparently falls back to a tarball-based fetch path that does not
    consume REST API rate limit.
    """
    token = _resolve_token(token)
    force_archive = os.getenv("CODEFLOW_GITHUB_FETCH_MODE", "").strip().lower() == "archive"
    if force_archive:
        return await _fetch_repo_from_archive(repo, branch_hint=None, progress_callback=progress_callback)

    try:
        return await _fetch_repo_from_api(repo, token=token, progress_callback=progress_callback)
    except _GitHubRateLimitError as err:
        return await _fetch_repo_from_archive(
            repo,
            branch_hint=err.branch_hint,
            progress_callback=progress_callback,
        )
    except httpx.HTTPStatusError as err:
        status = err.response.status_code
        if status == 401 and token:
            # Gracefully recover from stale/invalid token by retrying anonymously.
            return await _fetch_repo_from_api(repo, token=None, progress_callback=progress_callback)
        if status == 403:
            return await _fetch_repo_from_archive(
                repo,
                branch_hint=None,
                progress_callback=progress_callback,
            )
        raise


class _GitHubRateLimitError(RuntimeError):
    def __init__(self, message: str, branch_hint: Optional[str] = None):
        super().__init__(message)
        self.branch_hint = branch_hint


def _resolve_token(token: Optional[str]) -> Optional[str]:
    if token:
        cleaned = token.strip()
        if cleaned:
            return cleaned
    for env_var in ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PAT"):
        value = os.getenv(env_var, "").strip()
        if value:
            return value
    return None


def _is_rate_limited(res: httpx.Response) -> bool:
    if res.headers.get("x-ratelimit-remaining") == "0":
        return True
    try:
        message = str(res.json().get("message", "")).lower()
    except Exception:
        message = ""
    return "rate limit" in message and "exceeded" in message


def _filter_candidate_paths(entries: list[tuple[str, int]]) -> list[str]:
    files: list[str] = []
    for path, size in entries:
        parts = path.split("/")
        if any(part in SKIP_DIRS for part in parts):
            continue
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if ext not in CODE_EXTENSIONS:
            continue
        if size > MAX_FILE_SIZE_BYTES:
            continue
        files.append(path)
    return sorted(files, key=_priority)[:MAX_FILES]


def _decode_content(raw: bytes) -> str:
    # Keep parser robust on mixed encodings; source files remain mostly UTF-8.
    return raw.decode("utf-8", errors="replace")


def _strip_archive_root(member_name: str) -> str:
    parts = member_name.split("/", 1)
    if len(parts) < 2:
        return ""
    return parts[1]


async def _fetch_repo_from_api(
    repo: str,
    token: Optional[str],
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
        if repo_res.status_code == 403 and _is_rate_limited(repo_res):
            raise _GitHubRateLimitError("GitHub API rate limit exceeded", branch_hint=None)
        repo_res.raise_for_status()

        branch = repo_res.json().get("default_branch", "main")

        if progress_callback:
            await progress_callback(15, f"Fetching source tree ({branch})")

        tree_res = await client.get(
            f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
        )
        if tree_res.status_code == 403 and _is_rate_limited(tree_res):
            raise _GitHubRateLimitError("GitHub API rate limit exceeded", branch_hint=branch)
        tree_res.raise_for_status()
        tree_data = tree_res.json()

        entries: list[tuple[str, int]] = []
        for item in tree_data.get("tree", []):
            if item.get("type") != "blob":
                continue
            entries.append((item.get("path", ""), item.get("size", 0)))
        files = _filter_candidate_paths(entries)

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


async def _fetch_repo_from_archive(
    repo: str,
    branch_hint: Optional[str],
    progress_callback: Optional[Callable[[int, str], asyncio.Future]] = None,
) -> tuple[dict[str, str], str]:
    candidates = [b for b in [branch_hint, "HEAD", "main", "master", "trunk", "develop"] if b]
    seen: set[str] = set()
    branch_candidates = [b for b in candidates if not (b in seen or seen.add(b))]

    if progress_callback:
        await progress_callback(5, "Falling back to archive fetch")

    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        last_error: Optional[Exception] = None
        for branch in branch_candidates:
            if branch == "HEAD":
                archive_url = f"https://codeload.github.com/{repo}/tar.gz/HEAD"
            else:
                archive_url = f"https://codeload.github.com/{repo}/tar.gz/refs/heads/{branch}"
            res = await client.get(archive_url)
            if res.status_code == 404:
                last_error = ValueError(f"Repository '{repo}' not found or inaccessible")
                continue
            if res.status_code in (401, 403):
                raise ValueError(f"Repository '{repo}' is inaccessible (private or forbidden)")
            if res.status_code >= 400:
                last_error = ValueError(f"Failed to download archive: HTTP {res.status_code}")
                continue
            return await _extract_from_archive_bytes(
                branch=branch,
                archive_bytes=res.content,
                progress_callback=progress_callback,
            )

    if last_error:
        raise last_error
    raise ValueError(f"Repository '{repo}' not found or inaccessible")


async def _extract_from_archive_bytes(
    branch: str,
    archive_bytes: bytes,
    progress_callback: Optional[Callable[[int, str], asyncio.Future]] = None,
) -> tuple[dict[str, str], str]:
    if progress_callback:
        await progress_callback(15, f"Indexing archive tree ({branch})")

    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
        members_by_path: dict[str, tarfile.TarInfo] = {}
        entries: list[tuple[str, int]] = []

        for member in tar.getmembers():
            if not member.isfile():
                continue
            path = _strip_archive_root(member.name)
            if not path:
                continue
            entries.append((path, member.size))
            members_by_path[path] = member

        files = _filter_candidate_paths(entries)

        if progress_callback:
            await progress_callback(30, f"Reading {len(files)} candidate files")

        contents: dict[str, str] = {}
        for idx, path in enumerate(files, start=1):
            member = members_by_path.get(path)
            if member is None:
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            raw = extracted.read(MAX_FILE_SIZE_BYTES)
            contents[path] = _decode_content(raw)

            if progress_callback and idx % 10 == 0:
                pct = 30 + int((idx / max(len(files), 1)) * 60)
                await progress_callback(min(pct, 90), f"Read {path}")

    if not contents:
        raise ValueError(f"No supported source files found in '{repo}'")

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
