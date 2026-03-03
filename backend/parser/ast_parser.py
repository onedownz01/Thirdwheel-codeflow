"""Orchestrates language parsers across fetched repository files."""
from __future__ import annotations

from ..models.schema import ParsedRepo
from .graph_builder import build_graph
from .js_parser import parse_js_file
from .python_parser import parse_python_file


def parse_repository(repo: str, branch: str, contents: dict[str, str]) -> ParsedRepo:
    functions = []
    intents = []

    for path, content in contents.items():
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        try:
            if ext == "py":
                fns, i = parse_python_file(path, content)
                functions.extend(fns)
                intents.extend(i)
            elif ext in {"js", "jsx", "ts", "tsx", "vue", "svelte"}:
                fns, i = parse_js_file(path, content)
                functions.extend(fns)
                intents.extend(i)
        except Exception:
            continue

    return build_graph(functions, intents, repo, branch)
