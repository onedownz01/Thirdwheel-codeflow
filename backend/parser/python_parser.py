"""Tree-sitter Python parser for function extraction and backend intent evidence."""
from __future__ import annotations

import re

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

from ..models.schema import (
    EvidenceKind,
    FunctionType,
    Intent,
    IntentEvidence,
    Param,
    ParsedFunction,
)

PY_LANGUAGE = Language(tspython.language())

ROUTE_DECORATOR_PATTERN = re.compile(
    r"@(app|router|bp)\.(get|post|put|delete|patch|options|head)\s*\(([^)]*)\)",
    re.IGNORECASE,
)
# Flask / Werkzeug: @app.route("/path", methods=["POST", "GET"])
# Group 1: app|bp, Group 2: path, Group 3: methods list contents (optional)
FLASK_ROUTE_PATTERN = re.compile(
    r'@(app|bp)\.route\s*\(\s*[\'"]([^\'"]*)[\'"]([^)]*)\)',
    re.IGNORECASE | re.DOTALL,
)
_FLASK_METHODS_RE = re.compile(r'methods\s*=\s*\[([^\]]+)\]', re.IGNORECASE)
CLI_DECORATOR_PATTERN = re.compile(
    r"@(?:\w+\.)?(?:command|cli\.command)\s*\(([^)]*)\)",
    re.IGNORECASE,
)
ARGPARSE_SUBPARSER_PATTERN = re.compile(
    r"\.add_parser\(\s*['\"`]([^'\"`]+)['\"`]",
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
                cli_intent = _build_cli_intent(fn, lines)
                if cli_intent:
                    intents.append(cli_intent)

        for child in node.children:
            walk(child)

    walk(tree.root_node)
    intents.extend(_extract_argparse_intents(path, content))

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
    """
    Collect all decorator text immediately above a function definition.

    Handles both single-line and multi-line decorators, e.g.:

        @router.post("/login", ...)          # single-line — was already working
        async def login(...):

        @router.post(                        # multi-line — was broken before this fix
            "",
            status_code=HTTP_201_CREATED,
            name="auth:register",
        )
        async def register(...):

    Strategy: scan backward from the line above `async def`.
    * Lines that start with "@" are decorator start lines — collect and keep going.
    * Lines that are clearly continuation content (start with whitespace, or are
      bare ")" / argument tokens) while we haven't yet found an "@" are part of a
      multi-line decorator — collect and keep scanning.
    * A blank line or a line that starts with non-decorator, non-continuation
      content (another def/class/statement) terminates the scan.
    """
    buf: list[str] = []
    idx = start_line - 2          # 0-indexed line just above the `def`/`async def`
    found_at_sign = False

    while idx >= 0:
        raw = lines[idx]
        stripped = raw.strip()

        if not stripped:
            break  # blank line = definitely outside decorator block

        if stripped.startswith("@"):
            buf.append(raw)
            found_at_sign = True
            idx -= 1
            # After finding a "@" line keep scanning for stacked decorators.
            continue

        if found_at_sign:
            # We've already collected at least one "@" line; anything that doesn't
            # start with "@" or whitespace is a new statement — stop.
            if not raw[0:1].strip() == "":  # i.e. not leading whitespace
                break
            # Indented line between stacked decorators — rare but valid; collect.
            buf.append(raw)
            idx -= 1
            continue

        # We haven't found "@" yet: we're inside a multi-line decorator's argument
        # list (closing paren, arg values, etc.).  Keep collecting unless the line
        # looks like the start of a completely different statement.
        if stripped.startswith(("def ", "async def ", "class ", "return ", "raise ")):
            break  # hit a statement — stop
        buf.append(raw)
        idx -= 1

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
        # Try Flask-style: @app.route("/path", methods=["POST"])
        mf = FLASK_ROUTE_PATTERN.search(decorators)
        if not mf:
            return None
        route_path = mf.group(2)
        rest = mf.group(3)  # everything after the path string inside the parens
        mm = _FLASK_METHODS_RE.search(rest)
        if mm:
            raw_methods = [s.strip().strip("'\"") for s in mm.group(1).split(",")]
            method = raw_methods[0].upper() if raw_methods else "GET"
        else:
            method = "GET"  # Flask default when methods= is omitted
        label = f"{method} {route_path}"
        canonical = f"api.{method.lower()}.{fn.name}"
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

    method = m.group(2).upper()
    route_path = _route_path_from_args(m.group(3))
    label = f"{method} {route_path}"
    # Include fn.name so two handlers at the same path (different routers) stay distinct.
    canonical = f"api.{method.lower()}.{fn.name}"

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


def _build_cli_intent(fn: ParsedFunction, lines: list[str]) -> Intent | None:
    decorators = _decorator_lines(fn.line, lines)
    m = CLI_DECORATOR_PATTERN.search(decorators)
    if not m:
        return None

    arg_text = m.group(1) or ""
    command_name = _route_path_from_args(arg_text)
    if command_name == "/":
        command_name = fn.name.replace("_", "-")

    label = f"CLI {command_name}"
    evidence = IntentEvidence(
        kind=EvidenceKind.CLI_COMMAND,
        source_file=fn.file,
        line=fn.line,
        symbol=fn.name,
        excerpt=decorators[:140],
        weight=0.8,
    )
    return Intent(
        id=f"intent:{fn.file}:{fn.name}:cli:{fn.line}",
        canonical_id=f"actions.cli.{_slug(command_name)}",
        label=label,
        icon="⌨",
        trigger="cli:command",
        handler_fn_id=fn.id,
        source_file=fn.file,
        group="Actions",
        status="candidate",
        confidence=0.8,
        evidence=[evidence],
        aliases=[fn.name, command_name],
    )


def _extract_argparse_intents(path: str, content: str) -> list[Intent]:
    intents: list[Intent] = []
    for idx, line in enumerate(content.splitlines(), start=1):
        m = ARGPARSE_SUBPARSER_PATTERN.search(line)
        if not m:
            continue
        command_name = m.group(1).strip()
        intents.append(
            Intent(
                id=f"intent:{path}:argparse:{command_name}:{idx}",
                canonical_id=f"actions.cli.{_slug(command_name)}",
                label=f"CLI {command_name}",
                icon="⌨",
                trigger="cli:argparse",
                handler_fn_id=f"{path}:cli_{command_name}:{idx}",
                source_file=path,
                group="Actions",
                status="candidate",
                confidence=0.64,
                evidence=[
                    IntentEvidence(
                        kind=EvidenceKind.CLI_COMMAND,
                        source_file=path,
                        line=idx,
                        symbol=command_name,
                        excerpt=line.strip()[:140],
                        weight=0.64,
                    )
                ],
                aliases=[command_name],
            )
        )
    return intents



def _route_path_from_args(args: str) -> str:
    # Allow empty match (*) so that @router.post("", ...) correctly yields ""
    # rather than accidentally matching the next quoted string in the args.
    m = re.search(r"['\"`]([^'\"`]*)['\"`]", args)
    return m.group(1) if m else "/"



def _slug(value: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", ".", value).strip(".").lower()
    return s or "root"
