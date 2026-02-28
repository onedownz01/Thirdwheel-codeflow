"""JS/TS/TSX parser with multi-signal recall-first intent extraction."""
from __future__ import annotations

import re

import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser

from ..models.schema import (
    EvidenceKind,
    FunctionType,
    Intent,
    IntentEvidence,
    Param,
    ParsedFunction,
)

JS_LANGUAGE = Language(tsjs.language())
TS_LANGUAGE = Language(tsts.language_typescript())
TSX_LANGUAGE = Language(tsts.language_tsx())

INTENT_ATTRS = {
    "onClick",
    "onSubmit",
    "onChange",
    "onPress",
    "onKeyDown",
    "onKeyPress",
    "onDoubleClick",
}



def parse_js_file(path: str, content: str) -> tuple[list[ParsedFunction], list[Intent]]:
    lang = _select_language(path)
    parser = Parser(lang)
    tree = parser.parse(content.encode("utf-8"))

    functions: list[ParsedFunction] = []
    intents: list[Intent] = []

    _walk(tree.root_node, path, content, functions, intents)
    intents.extend(_extract_content_level_intents(path, content))

    for intent in intents:
        intent.confidence = max(0.2, min(0.99, sum(ev.weight for ev in intent.evidence) / 2.0))
    deduped = _dedupe_intents(intents)
    return functions, deduped



def _select_language(path: str) -> Language:
    ext = path.rsplit(".", 1)[-1].lower()
    if ext == "ts":
        return TS_LANGUAGE
    if ext == "tsx":
        return TSX_LANGUAGE
    return JS_LANGUAGE



def _walk(node, path: str, content: str, functions: list[ParsedFunction], intents: list[Intent]) -> None:
    if node.type in ("function_declaration", "method_definition"):
        fn = _extract_named_function(node, path)
        if fn:
            functions.append(fn)
    elif node.type == "variable_declarator":
        fn = _extract_arrow_function(node, path)
        if fn:
            functions.append(fn)
    elif node.type == "jsx_attribute":
        intent = _extract_jsx_intent(node, path, content)
        if intent:
            intents.append(intent)
    elif node.type == "call_expression":
        route_fn, route_intent = _extract_route_signal(node, path)
        if route_fn:
            functions.append(route_fn)
        if route_intent:
            intents.append(route_intent)
        net_intent = _extract_network_signal(node, path)
        if net_intent:
            intents.append(net_intent)

    for child in node.children:
        _walk(child, path, content, functions, intents)


def _extract_content_level_intents(path: str, content: str) -> list[Intent]:
    intents: list[Intent] = []
    lines = content.splitlines()

    form_action_re = re.compile(
        r"<form[^>]*action=\{?\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\}?[^>]*>",
        re.IGNORECASE,
    )
    router_re = re.compile(
        r"\b(?:router\.(?:push|replace)|navigate)\s*\(\s*['\"`]([^'\"`]+)['\"`]",
        re.IGNORECASE,
    )
    ui_event_re = re.compile(
        r"\b(onClick|onSubmit|onChange|onPress|onKeyDown|onKeyPress|onDoubleClick)\s*=\s*\{?\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\}?",
        re.IGNORECASE,
    )

    for idx, line in enumerate(lines, start=1):
        form_match = form_action_re.search(line)
        if form_match:
            handler = form_match.group(1)
            label = _humanize(handler)
            intents.append(
                Intent(
                    id=f"intent:{path}:form:{handler}:{idx}",
                    canonical_id=f"{_infer_group(path, label).lower()}.{_slug(label)}",
                    label=f"Form Action: {label}",
                    icon="📝",
                    trigger="form:action",
                    handler_fn_id=f"{path}:{handler}:0",
                    source_file=path,
                    group=_infer_group(path, label),
                    status="candidate",
                    confidence=0.68,
                    evidence=[
                        IntentEvidence(
                            kind=EvidenceKind.FORM_ACTION,
                            source_file=path,
                            line=idx,
                            symbol=handler,
                            excerpt=line.strip()[:140],
                            weight=0.68,
                        )
                    ],
                    aliases=[handler],
                )
            )

        route_match = router_re.search(line)
        if route_match:
            route = route_match.group(1)
            label = f"Navigate {route}"
            intents.append(
                Intent(
                    id=f"intent:{path}:navigate:{idx}",
                    canonical_id=f"navigation.{_slug(route)}",
                    label=label,
                    icon="🧭",
                    trigger="router_transition",
                    handler_fn_id=f"{path}:navigate:{idx}",
                    source_file=path,
                    group="Discovery",
                    status="candidate",
                    confidence=0.62,
                    evidence=[
                        IntentEvidence(
                            kind=EvidenceKind.ROUTER_TRANSITION,
                            source_file=path,
                            line=idx,
                            symbol="router.push|replace|navigate",
                            excerpt=line.strip()[:140],
                            weight=0.62,
                        )
                    ],
                    aliases=["route_transition"],
                )
            )

        ui_match = ui_event_re.search(line)
        if ui_match:
            attr, handler = ui_match.groups()
            label = _humanize(handler)
            intents.append(
                Intent(
                    id=f"intent:{path}:{attr}:{handler}:{idx}",
                    canonical_id=f"{_infer_group(path, label).lower()}.{_slug(label)}",
                    label=label,
                    icon=_guess_icon(label, handler),
                    trigger=attr,
                    handler_fn_id=f"{path}:{handler}:0",
                    source_file=path,
                    group=_infer_group(path, label),
                    status="candidate",
                    confidence=0.72,
                    evidence=[
                        IntentEvidence(
                            kind=EvidenceKind.UI_EVENT,
                            source_file=path,
                            line=idx,
                            symbol=handler,
                            excerpt=line.strip()[:140],
                            weight=0.72,
                        )
                    ],
                    aliases=[handler],
                )
            )

    return intents



def _extract_named_function(node, path: str) -> ParsedFunction | None:
    name_node = node.child_by_field_name("name")
    if not name_node:
        return None

    name = name_node.text.decode("utf-8")
    line = node.start_point[0] + 1
    params = _extract_params(node)

    return ParsedFunction(
        id=f"{path}:{name}:{line}",
        name=name,
        file=path,
        type=_infer_type(name, path),
        params=params,
        line=line,
        calls=_extract_calls(node.text.decode("utf-8")),
        description=f"JS function {name}",
    )



def _extract_arrow_function(node, path: str) -> ParsedFunction | None:
    name_node = node.child_by_field_name("name")
    value_node = node.child_by_field_name("value")
    if not name_node or not value_node:
        return None
    if value_node.type not in ("arrow_function", "function"):
        return None

    name = name_node.text.decode("utf-8")
    line = node.start_point[0] + 1

    return ParsedFunction(
        id=f"{path}:{name}:{line}",
        name=name,
        file=path,
        type=_infer_type(name, path),
        params=_extract_params(value_node),
        line=line,
        calls=_extract_calls(value_node.text.decode("utf-8")),
        description=f"JS function {name}",
    )



def _extract_jsx_intent(node, path: str, content: str) -> Intent | None:
    name_node = node.child_by_field_name("name")
    value_node = node.child_by_field_name("value")
    if not name_node or not value_node:
        return None

    attr = name_node.text.decode("utf-8")
    if attr not in INTENT_ATTRS:
        return None

    value_text = value_node.text.decode("utf-8")
    m = re.search(r"\b([a-zA-Z_$][a-zA-Z0-9_$]*)\b", value_text)
    if not m:
        return None

    handler_name = m.group(1)
    if handler_name in {"true", "false", "null", "undefined"}:
        return None

    label = _infer_label(node, content) or _humanize(handler_name)
    canonical = _canonical_id(path, label, handler_name)

    evidence = IntentEvidence(
        kind=EvidenceKind.UI_EVENT,
        source_file=path,
        line=node.start_point[0] + 1,
        symbol=handler_name,
        excerpt=f"{attr}={value_text}",
        weight=0.75,
    )

    return Intent(
        id=f"intent:{path}:{handler_name}:{node.start_point[0] + 1}",
        canonical_id=canonical,
        label=label,
        icon=_guess_icon(label, handler_name),
        trigger=attr,
        handler_fn_id=f"{path}:{handler_name}:0",
        source_file=path,
        group=_infer_group(path, label),
        status="candidate",
        confidence=0.75,
        evidence=[evidence],
        aliases=[handler_name],
    )



def _extract_route_signal(node, path: str) -> tuple[ParsedFunction | None, Intent | None]:
    text = node.text.decode("utf-8") if node.text else ""
    methods = [
        "app.get",
        "app.post",
        "app.put",
        "app.delete",
        "app.patch",
        "router.get",
        "router.post",
        "router.put",
        "router.delete",
        "router.patch",
    ]

    for method in methods:
        if not text.startswith(method):
            continue
        m = re.search(r"['\"`]([^'\"` ]+)['\"`]", text)
        route_path = m.group(1) if m else "/"
        http_method = method.split(".")[1].upper()
        name = f"{http_method} {route_path}"
        line = node.start_point[0] + 1

        fn = ParsedFunction(
            id=f"{path}:{name}:{line}",
            name=name,
            file=path,
            type=FunctionType.ROUTE,
            params=[
                Param(name="req", type="Request", direction="in"),
                Param(name="res", type="Response", direction="out"),
            ],
            line=line,
            description="Route handler",
        )

        intent = Intent(
            id=f"intent:{path}:{http_method}:{route_path}:{line}",
            canonical_id=f"api.{http_method.lower()}.{_slug(route_path)}",
            label=f"{http_method} {route_path}",
            icon="🧭",
            trigger=f"route:{http_method} {route_path}",
            handler_fn_id=fn.id,
            source_file=path,
            group="Backend",
            status="candidate",
            confidence=0.88,
            evidence=[
                IntentEvidence(
                    kind=EvidenceKind.BACKEND_ROUTE,
                    source_file=path,
                    line=line,
                    symbol=name,
                    excerpt=text[:120],
                    weight=0.88,
                )
            ],
        )
        return fn, intent

    return None, None



def _extract_network_signal(node, path: str) -> Intent | None:
    text = node.text.decode("utf-8") if node.text else ""
    if not any(sig in text for sig in ("fetch(", "axios.", "mutate(", "mutation(")):
        return None

    method = "POST" if any(sig in text.lower() for sig in ("post(", "mutation", "mutate(")) else "GET"
    label = "Network Request"
    route = _first_url_like(text)
    canonical = f"network.{method.lower()}.{_slug(route or 'request')}"

    return Intent(
        id=f"intent:{path}:network:{node.start_point[0] + 1}",
        canonical_id=canonical,
        label=label if not route else f"{label}: {route}",
        icon="🌐",
        trigger=f"network:{method}",
        handler_fn_id=f"{path}:network:{node.start_point[0] + 1}",
        source_file=path,
        group="Actions",
        status="candidate",
        confidence=0.48,
        evidence=[
            IntentEvidence(
                kind=EvidenceKind.NETWORK_MUTATION,
                source_file=path,
                line=node.start_point[0] + 1,
                symbol="fetch/axios",
                excerpt=text[:120],
                weight=0.48,
            )
        ],
        aliases=["network_request"],
    )



def _extract_params(node) -> list[Param]:
    params: list[Param] = []
    params_node = node.child_by_field_name("parameters") or node.child_by_field_name("parameter")
    if not params_node:
        return params

    for child in params_node.children:
        if child.type == "identifier":
            params.append(Param(name=child.text.decode("utf-8"), direction="in"))
        elif child.type in ("required_parameter", "optional_parameter"):
            name_child = child.child_by_field_name("pattern") or (child.children[0] if child.children else None)
            type_child = child.child_by_field_name("type")
            name = name_child.text.decode("utf-8") if name_child else ""
            ptype = type_child.text.decode("utf-8").strip(": ") if type_child else "any"
            if name:
                params.append(Param(name=name, type=ptype, direction="in"))

    return params[:6]



def _extract_calls(text: str) -> list[str]:
    calls = re.findall(r"\b([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(", text)
    skip = {
        "console",
        "setTimeout",
        "setInterval",
        "Promise",
        "Array",
        "Object",
        "Math",
        "JSON",
        "parseInt",
        "parseFloat",
        "Boolean",
        "String",
        "Number",
        "fetch",
        "require",
        "import",
        "super",
        "useState",
        "useEffect",
        "useMemo",
        "useCallback",
        "useRef",
    }
    return [c for c in calls if c not in skip and len(c) > 1][:50]



def _infer_type(name: str, path: str) -> FunctionType:
    n = name.lower()
    p = path.lower()

    if re.match(r"^use[A-Z]", name):
        return FunctionType.HOOK
    if name and name[0].isupper() and any(x in p for x in (".jsx", ".tsx", ".vue", ".svelte")):
        return FunctionType.COMPONENT
    if any(x in n for x in ("handle", "onsubmit", "onclick", "submit", "create", "update", "delete")):
        return FunctionType.HANDLER
    if any(x in p for x in ("service", "api", "client")):
        return FunctionType.SERVICE
    if any(x in p for x in ("model", "schema", "db", "database", "prisma")):
        return FunctionType.DB
    if any(x in p for x in ("auth", "guard", "middleware")):
        return FunctionType.AUTH
    if any(x in p for x in ("util", "helper", "lib", "common", "shared")):
        return FunctionType.UTIL
    return FunctionType.OTHER



def _infer_label(node, content: str) -> str | None:
    ctx_start = max(0, node.start_byte - 250)
    ctx_end = min(len(content), node.end_byte + 250)
    ctx = content[ctx_start:ctx_end]
    m = re.search(r">([A-Za-z][A-Za-z0-9\s\-]{1,40})<", ctx)
    return m.group(1).strip() if m else None



def _humanize(name: str) -> str:
    name = re.sub(r"^handle", "", name)
    name = re.sub(r"^on", "", name)
    name = re.sub(r"([A-Z])", r" \1", name)
    name = name.strip()
    return name.title() if name else "Action"



def _guess_icon(label: str, handler: str) -> str:
    s = f"{label} {handler}".lower()
    mapping = {
        "search": "🔍",
        "login": "🔐",
        "signin": "🔐",
        "signup": "👤",
        "register": "👤",
        "logout": "👋",
        "submit": "📤",
        "delete": "🗑️",
        "remove": "🗑️",
        "pay": "💳",
        "checkout": "💳",
        "upload": "📎",
        "send": "💬",
        "save": "💾",
        "edit": "✏️",
        "update": "🔄",
        "share": "🔗",
        "download": "⬇️",
        "add": "➕",
    }
    for key, icon in mapping.items():
        if key in s:
            return icon
    return "▶"



def _infer_group(path: str, label: str) -> str:
    s = f"{path} {label}".lower()
    if any(x in s for x in ("auth", "login", "signup", "register", "logout")):
        return "Auth"
    if any(x in s for x in ("search", "filter", "discover", "explore")):
        return "Discovery"
    if any(x in s for x in ("post", "publish", "create", "write", "content")):
        return "Content"
    if any(x in s for x in ("user", "profile", "account", "setting")):
        return "Profile"
    if any(x in s for x in ("pay", "checkout", "billing", "subscription")):
        return "Payments"
    if any(x in s for x in ("admin", "dashboard", "manage")):
        return "Admin"
    return "Actions"



def _canonical_id(path: str, label: str, handler: str) -> str:
    domain = _infer_group(path, label).lower()
    action = _slug(label or handler)
    return f"{domain}.{action}"



def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", ".", value).strip(".").lower() or "action"



def _first_url_like(text: str) -> str | None:
    m = re.search(r"['\"`](/[^'\"`\s]+)['\"`]", text)
    if m:
        return m.group(1)
    m = re.search(r"['\"`](https?://[^'\"`\s]+)['\"`]", text)
    return m.group(1) if m else None


def _dedupe_intents(intents: list[Intent]) -> list[Intent]:
    by_key: dict[str, Intent] = {}
    for intent in intents:
        key = intent.canonical_id or intent.id
        existing = by_key.get(key)
        if not existing:
            by_key[key] = intent
            continue
        existing.aliases = sorted(set(existing.aliases + intent.aliases + [intent.label]))
        existing.evidence.extend(intent.evidence)
        existing.confidence = max(existing.confidence, intent.confidence)
    return list(by_key.values())
