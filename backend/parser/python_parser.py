"""Tree-sitter Python parser for function extraction and backend intent evidence."""
from __future__ import annotations

import re
from typing import Iterable

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

from ..models.schema import EvidenceKind, FunctionType, Intent, IntentEvidence, Param, ParsedFunction

PY_LANGUAGE = Language(tspython.language())

ROUTE_DECORATOR_PATTERN = re.compile(
    r"@(app|router|bp)\.(get|post|put|delete|patch|options|head)\s*\(([^)]*)\)",
    re.IGNORECASE,
)


def parse_python_file(path: str, content: str) -> tuple[list[ParsedFunction], list[Intent]]:
    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(content.encode("utf-8"))
    lines = content.splitlines()

    functions: list[ParsedFunction] = []
    intents: list[Intent] = []

    def walk(node) -> None:
        if node.type in ("function_definition", "async_function_definition"):
            fn = _extract_function(node, path, lines)
            if fn:
                functions.append(fn)

                route_intent = _build_route_intent(fn, lines)
                if route_intent:
                    intents.append(route_intent)

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    return functions, intents



def _extract_function(node, path: str, lines: list[str]) -> ParsedFunction | None:
    name_node = node.child_by_field_name("name")
    if not name_node:
        return None

    name = name_node.text.decode("utf-8")
    line = node.start_point[0] + 1
    params = _extract_params(node)

    body_node = node.child_by_field_name("body")
    body_text = body_node.text.decode("utf-8") if body_node else ""
    decorators = _decorator_lines(line, lines)

    return ParsedFunction(
        id=f"{path}:{name}:{line}",
        name=name,
        file=path,
        type=_infer_type(name, path, decorators, body_text),
        params=params,
        line=line,
        calls=_extract_calls(body_text),
        description=f"Python function {name}",
    )



def _extract_params(node) -> list[Param]:
    out: list[Param] = []
    params_node = node.child_by_field_name("parameters")
    if not params_node:
        return out

    for child in params_node.children:
        text = child.text.decode("utf-8").strip()
        if not text or text in {"(", ")", ",", "*", "/"}:
            continue
        name = text.split(":", 1)[0].split("=", 1)[0].strip()
        if name in {"self", "cls"} or not name:
            continue
        ptype = "any"
        if ":" in text:
            ptype = text.split(":", 1)[1].split("=", 1)[0].strip()
        out.append(Param(name=name, type=ptype, direction="in"))

    return out[:6]



def _decorator_lines(start_line: int, lines: list[str]) -> str:
    buf: list[str] = []
    idx = start_line - 2
    while idx >= 0:
        line = lines[idx].strip()
        if line.startswith("@"):
            buf.append(line)
            idx -= 1
            continue
        break
    buf.reverse()
    return "\n".join(buf)



def _infer_type(name: str, path: str, decorators: str, body: str) -> FunctionType:
    n = name.lower()
    p = path.lower()
    d = decorators.lower()
    b = body.lower()

    if any(x in d for x in ("@app.", "@router.", "@bp.")):
        return FunctionType.ROUTE
    if any(x in p for x in ("auth", "token", "jwt", "middleware")) or any(
        x in n for x in ("auth", "login", "logout", "verify", "token")
    ):
        return FunctionType.AUTH
    if any(x in p for x in ("service", "usecase")) or n.endswith("service"):
        return FunctionType.SERVICE
    if any(x in p for x in ("db", "database", "model", "schema", "repository")) or any(
        x in b for x in ("session.query", "execute(", "objects.create", "objects.filter")
    ):
        return FunctionType.DB
    if any(x in p for x in ("util", "helper", "common", "lib")):
        return FunctionType.UTIL
    if any(x in n for x in ("handle", "process", "submit", "create", "update", "delete")):
        return FunctionType.HANDLER
    return FunctionType.OTHER



def _extract_calls(body_text: str) -> list[str]:
    pattern = r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\("
    calls = re.findall(pattern, body_text)
    skip = {
        "print",
        "len",
        "range",
        "dict",
        "list",
        "set",
        "tuple",
        "int",
        "str",
        "float",
        "bool",
        "super",
        "isinstance",
        "hasattr",
        "getattr",
    }
    return [c for c in calls if c not in skip and len(c) > 1][:50]



def _build_route_intent(fn: ParsedFunction, lines: list[str]) -> Intent | None:
    if fn.type != FunctionType.ROUTE:
        return None

    decorators = _decorator_lines(fn.line, lines)
    m = ROUTE_DECORATOR_PATTERN.search(decorators)
    if not m:
        return None

    method = m.group(2).upper()
    route_path = _route_path_from_args(m.group(3))
    label = f"{method} {route_path}"
    canonical = f"api.{method.lower()}.{_slug(route_path)}"

    evidence = IntentEvidence(
        kind=EvidenceKind.BACKEND_ROUTE,
        source_file=fn.file,
        line=fn.line,
        symbol=fn.name,
        excerpt=decorators,
        weight=0.9,
    )

    return Intent(
        id=f"intent:{fn.file}:{fn.name}:{fn.line}",
        canonical_id=canonical,
        label=label,
        icon="🧭",
        trigger=f"route:{method} {route_path}",
        handler_fn_id=fn.id,
        source_file=fn.file,
        group="Backend",
        status="candidate",
        confidence=0.88,
        evidence=[evidence],
    )



def _route_path_from_args(args: str) -> str:
    m = re.search(r"['\"`]([^'\"`]+)['\"`]", args)
    return m.group(1) if m else "/"



def _slug(value: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", ".", value).strip(".").lower()
    return s or "root"
