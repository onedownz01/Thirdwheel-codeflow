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
# Flat ArgumentParser scripts (not subcommand-style)
ARGPARSE_MAIN_PATTERN = re.compile(r"ArgumentParser\s*\(", re.IGNORECASE)
MAIN_GUARD_PATTERN = re.compile(r"if\s+__name__\s*==\s*['\"]__main__['\"]")
ADD_ARGUMENT_FLAG_PATTERN = re.compile(r'\.add_argument\(\s*[\'\"](--[a-zA-Z_-]+)[\'\"]\s*')
# Top-level class definitions
CLASS_DEF_PATTERN = re.compile(r"^class (\w+)", re.MULTILINE)


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
    intents.extend(_extract_script_intents(path, content))
    intents.extend(_extract_class_api_intents(path, content, functions))

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


def _extract_script_intents(path: str, content: str) -> list[Intent]:
    """Intent for __main__ scripts that use flat ArgumentParser (not subcommands).

    This covers scripts like:
        if __name__ == "__main__":
            parser = argparse.ArgumentParser()
            parser.add_argument("--input", ...)
    which the add_parser() subcommand detector misses entirely.
    """
    # Must have a __main__ guard AND an ArgumentParser call.
    if not MAIN_GUARD_PATTERN.search(content):
        return []
    if not ARGPARSE_MAIN_PATTERN.search(content):
        return []
    # Already handled by the subcommand extractor — don't double-count.
    if ARGPARSE_SUBPARSER_PATTERN.search(content):
        return []

    flags = ADD_ARGUMENT_FLAG_PATTERN.findall(content)
    flags_str = " ".join(flags[:4])

    script_name = path.rsplit("/", 1)[-1].replace(".py", "")
    label = f"python {script_name}.py"
    if flags_str:
        label += f"  {flags_str}"

    return [
        Intent(
            id=f"intent:{path}:__main__:0",
            canonical_id=f"cli.script.{_slug(script_name)}",
            label=label,
            icon="⌨",
            trigger=f"cli:{script_name}",
            handler_fn_id=f"{path}:__main__:0",
            source_file=path,
            group="Scripts",
            status="candidate",
            confidence=0.62,
            evidence=[
                IntentEvidence(
                    kind=EvidenceKind.CLI_COMMAND,
                    source_file=path,
                    line=1,
                    symbol=script_name,
                    excerpt=f"python {path} {flags_str}".strip(),
                    weight=0.62,
                )
            ],
            aliases=[script_name],
        )
    ]


def _extract_class_api_intents(
    path: str, content: str, fns: list[ParsedFunction]
) -> list[Intent]:
    """Generate intent candidates for public methods of named classes.

    This surfaces the public API of library-style repos that have no HTTP routes
    or CLI commands — e.g. a RAG library with a MyRAG class.

    Confidence is deliberately low (0.55) so these rank below real routes/CLI
    intents when both exist.  For a pure library repo they'll be the primary intents.

    Async/sync pairs (insert/ainsert, query/aquery) are deduplicated: the sync
    version is kept as the canonical intent; the label notes async availability.
    """
    class_matches = list(CLASS_DEF_PATTERN.finditer(content))
    if not class_matches:
        return []

    total_lines = content.count("\n") + 1
    intents: list[Intent] = []

    for i, cm in enumerate(class_matches):
        class_start = content[: cm.start()].count("\n") + 1
        class_end = (
            content[: class_matches[i + 1].start()].count("\n")
            if i + 1 < len(class_matches)
            else total_lines
        )
        class_name = cm.group(1)

        # Skip infrastructure / abstract classes that aren't user-facing entry points.
        # Base* → abstract interfaces; *Error/*Exception/*Warning → exception hierarchy;
        # *Format/*Schema → data models; *Encoder/*Decoder → serialization utilities.
        _cn = class_name.lower()
        if (
            class_name.startswith("Base")
            or _cn.endswith(("error", "exception", "warning"))
            or _cn.endswith(("format", "schema", "encoder", "decoder"))
        ):
            continue

        # Public methods whose definition line falls inside this class's line range.
        methods = [
            fn
            for fn in fns
            if fn.file == path
            and class_start < fn.line <= class_end
            and not fn.name.startswith("_")
        ]

        if len(methods) < 3:
            # Tiny class — not a meaningful API surface worth surfacing as intents.
            continue

        method_names = {fn.name for fn in methods}

        # Deduplicate async variants: keep sync; label it "/ async" if async exists.
        deduped: list[ParsedFunction] = []
        for fn in methods:
            # e.g. ainsert -> check if "insert" exists; aquery -> "query", etc.
            if fn.name.startswith("a") and fn.name[1:] in method_names:
                continue  # async variant; the sync form is the canonical entry
            deduped.append(fn)

        for fn in deduped[:10]:
            async_variant = f"a{fn.name}"
            has_async = async_variant in method_names
            label = f"{class_name}.{fn.name}()"
            if has_async:
                label += " / async"

            intents.append(
                Intent(
                    id=f"intent:{fn.file}:{fn.name}:{fn.line}",
                    canonical_id=f"api.{_slug(class_name)}.{_slug(fn.name)}",
                    label=label,
                    icon="◈",
                    trigger=f"api:{class_name}.{fn.name}",
                    handler_fn_id=fn.id,
                    source_file=fn.file,
                    group=class_name,
                    status="candidate",
                    confidence=0.55,
                    evidence=[
                        IntentEvidence(
                            kind=EvidenceKind.SYMBOL_HEURISTIC,
                            source_file=fn.file,
                            line=fn.line,
                            symbol=f"{class_name}.{fn.name}",
                            excerpt=f"class {class_name}: def {fn.name}()",
                            weight=0.55,
                        )
                    ],
                    aliases=[fn.name, f"{class_name}.{fn.name}"],
                )
            )

    return intents
