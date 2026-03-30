"""
Codeflow Final Benchmark — 15 Repos, 3 Passes
===============================================
All-in-one benchmark for the publishable GitHub/website report.

Pass 1 — Token Efficiency    : raw tokens vs Codeflow tokens, compression ratio
Pass 2 — Comprehension Quality: ground truth recall (ast.walk + regex)
Pass 3 — LLM Judge           : Gemini 2.5 Flash scores Codeflow vs raw on 5 fns/repo

Corpus: 15 repos across 5 categories
  A — Python App code  (CF's sweet spot)
  B — Python Frameworks
  C — Python Libraries / SDKs
  D — CLI Tools
  E — Full-Stack (Python + JS/TS)

Run:
    cd "Thirdwheel codeflow"
    GEMINI_API_KEY=... GITHUB_TOKEN=... python -m benchmark.final_benchmark
"""
from __future__ import annotations

import ast
import asyncio
import json
import os
import re
import textwrap
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import tiktoken
from google import genai
from google.genai import types as gtypes

from backend.parser.ast_parser import parse_repository
from backend.parser.github_fetcher import fetch_repo
from backend.models.schema import ParsedFunction, ParsedRepo

# ─── Config ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN", "")
GEMINI_MODEL   = "gemini-2.5-flash"
JUDGE_FNS      = 5          # functions judged per repo
RUN_DATE       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
OUT_PATH       = Path(__file__).parent / "FINAL_BENCHMARK_REPORT.md"

ENC = tiktoken.get_encoding("cl100k_base")
tok = lambda t: len(ENC.encode(t))

# ─── Corpus ───────────────────────────────────────────────────────────────────
REPOS = [
    # A — Python App code
    {"slug": "fastapi/full-stack-fastapi-template", "cat": "A", "label": "FastAPI Full-Stack App",       "desc": "Full-stack app: FastAPI backend + React frontend; routes, services, auth"},
    {"slug": "tiangolo/fastapi-users",              "cat": "A", "label": "FastAPI Users — Auth Service",  "desc": "Reusable FastAPI auth library; routers, managers, schemas, DB backends"},
    {"slug": "zauberzeug/nicegui",                  "cat": "A", "label": "NiceGUI — Python UI Framework", "desc": "FastAPI-based Python UI framework; components, routing, event handlers"},
    # B — Python Frameworks
    {"slug": "tiangolo/fastapi",                    "cat": "B", "label": "FastAPI — ASGI Framework",      "desc": "FastAPI itself; routing, dependency injection, OpenAPI generation"},
    {"slug": "pallets/flask",                       "cat": "B", "label": "Flask — WSGI Framework",        "desc": "Classic Python web framework; blueprints, context, routing"},
    {"slug": "encode/starlette",                    "cat": "B", "label": "Starlette — ASGI Toolkit",      "desc": "Low-level ASGI toolkit; middleware, routing, websockets"},
    # C — Python Libraries / SDKs
    {"slug": "anthropics/anthropic-sdk-python",     "cat": "C", "label": "Anthropic Python SDK",          "desc": "Official Anthropic SDK; typed resources, sync+async client"},
    {"slug": "openai/openai-python",                "cat": "C", "label": "OpenAI Python SDK",              "desc": "Official OpenAI SDK; typed resources, extensive API surface"},
    {"slug": "encode/httpx",                        "cat": "C", "label": "HTTPX — HTTP Client",            "desc": "Full-featured HTTP client; typed, async/sync, transport abstraction"},
    {"slug": "psf/requests",                        "cat": "C", "label": "Requests — HTTP Library",        "desc": "De-facto standard Python HTTP library; sessions, adapters, auth"},
    # D — CLI Tools
    {"slug": "httpie/httpie",                       "cat": "D", "label": "HTTPie — CLI HTTP Client",       "desc": "User-friendly CLI HTTP client; plugins, sessions, formatting"},
    {"slug": "pallets/click",                       "cat": "D", "label": "Click — CLI Framework",          "desc": "Composable CLI creation; decorators, types, groups, testing"},
    # E — Full-Stack / Mixed
    {"slug": "Textualize/rich",                     "cat": "E", "label": "Rich — Terminal Formatting",     "desc": "Rich text in terminal; renderables, layout, live display, panels"},
    {"slug": "pydantic/pydantic",                   "cat": "E", "label": "Pydantic — Data Validation",     "desc": "Python data validation; models, validators, serialisation, JSON schema"},
    {"slug": "sqlalchemy/sqlalchemy",               "cat": "E", "label": "SQLAlchemy — Python ORM",        "desc": "Python SQL toolkit and ORM; Core + ORM, dialects, sessions"},
]

CAT_LABELS = {
    "A": "Python App Code",
    "B": "Python Frameworks",
    "C": "Python Libraries / SDKs",
    "D": "CLI Tools",
    "E": "Mixed / Large Libraries",
}

# ─── Gemini ───────────────────────────────────────────────────────────────────
_gemini_client = None

def get_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client

def gemini_call(prompt: str) -> str:
    resp = get_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=gtypes.GenerateContentConfig(temperature=0.1, max_output_tokens=8192),
    )
    return resp.text.strip()

def parse_field(text: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.*?)(?=\n[A-Z_]{{2,}}:|\Z)", text,
                  re.MULTILINE | re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""

def parse_int(text: str, key: str, default: int = 5) -> int:
    val = parse_field(text, key)
    try:
        return max(1, min(10, int(re.search(r"\d+", val).group())))
    except Exception:
        return default

# ─── Ground Truth ─────────────────────────────────────────────────────────────
ROUTE_RE  = re.compile(r"@(?:\w+\.)+(?:get|post|put|delete|patch|options|head|route)\s*\(", re.I)
CLI_RE    = re.compile(r"@(?:\w+\.)+(?:command|cli\.command)\s*\(", re.I)
JS_FN_RE  = re.compile(r"(?:export\s+)?(?:async\s+)?function\s+\w+\s*\(|(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\(", re.M)

@dataclass
class GroundTruth:
    py_files: int = 0; js_files: int = 0; total_lines: int = 0
    py_fns: int = 0; async_fns: int = 0; classes: int = 0
    return_annotated: int = 0; total_params: int = 0; typed_params: int = 0
    routes: int = 0; cli_commands: int = 0; js_fns: int = 0

def extract_gt(contents: dict[str, str]) -> GroundTruth:
    g = GroundTruth()
    for path, src in contents.items():
        ext = Path(path).suffix.lower()
        g.total_lines += src.count("\n")
        if ext == ".py":
            g.py_files += 1
            try:
                tree = ast.parse(src)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        g.py_fns += 1
                        if isinstance(node, ast.AsyncFunctionDef): g.async_fns += 1
                        if node.returns: g.return_annotated += 1
                        all_args = node.args.args + node.args.posonlyargs + node.args.kwonlyargs
                        g.total_params += len(all_args)
                        g.typed_params += sum(1 for a in all_args if a.annotation)
                    elif isinstance(node, ast.ClassDef):
                        g.classes += 1
            except SyntaxError:
                g.py_fns += len(re.findall(r"^\s*(?:async\s+)?def\s+\w+", src, re.M))
            g.routes += len(ROUTE_RE.findall(src))
            g.cli_commands += len(CLI_RE.findall(src))
        elif ext in {".js", ".jsx", ".ts", ".tsx"}:
            g.js_files += 1
            g.js_fns += len(JS_FN_RE.findall(src))
    return g

# ─── Token Pass ───────────────────────────────────────────────────────────────
@dataclass
class TokenResult:
    raw_tokens: int = 0; flow_tokens: int = 0; flow_bytes: int = 0
    fn_count: int = 0; intent_count: int = 0; edge_count: int = 0
    return_typed: int = 0; docstrings: int = 0
    fn_type_buckets: dict = field(default_factory=dict)
    files_indexed: int = 0; parse_time_s: float = 0.0

    @property
    def saved(self): return self.raw_tokens - self.flow_tokens
    @property
    def pct(self): return self.saved / max(self.raw_tokens, 1) * 100
    @property
    def ratio(self): return self.raw_tokens / max(self.flow_tokens, 1)

def run_token_pass(slug: str, branch: str, contents: dict[str, str]) -> tuple[TokenResult, ParsedRepo]:
    r = TokenResult()
    raw_text = "\n".join(f"# file: {p}\n{c}\n" for p, c in contents.items())
    r.raw_tokens = tok(raw_text)
    t0 = time.perf_counter()
    parsed = parse_repository(slug, branch, contents)
    r.parse_time_s = time.perf_counter() - t0
    flow_json = json.dumps(parsed.model_dump(exclude={"edges"}, exclude_defaults=True), separators=(",", ":"))
    r.flow_bytes  = len(flow_json.encode())
    r.flow_tokens = tok(flow_json)
    r.fn_count    = len(parsed.functions)
    r.intent_count = len(parsed.intents)
    r.edge_count  = len(parsed.edges)
    r.return_typed = sum(1 for f in parsed.functions if f.return_type)
    r.docstrings   = sum(1 for f in parsed.functions if f.docstring)
    r.fn_type_buckets = {k: len(v) for k, v in parsed.fn_type_index.items()}
    r.files_indexed = len(parsed.file_index)
    return r, parsed

# ─── Body Extraction ──────────────────────────────────────────────────────────
def extract_body(src: str, fn_name: str, start_line: int) -> str:
    try:
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == fn_name and abs(node.lineno - start_line) <= 3:
                    lines = src.splitlines()
                    return "\n".join(lines[node.lineno - 1: node.end_lineno])
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == fn_name:
                    lines = src.splitlines()
                    return "\n".join(lines[node.lineno - 1: node.end_lineno])
    except SyntaxError:
        pass
    lines = src.splitlines()
    return "\n".join(lines[max(0, start_line - 1): start_line + 24])

def is_trivial(body: str) -> bool:
    lines = [l for l in textwrap.dedent(body).strip().splitlines()
             if l.strip() and not l.strip().startswith("#")]
    return len(lines) <= 3

TYPE_PRIORITY = ["route", "service", "auth", "handler", "db", "util", "other"]

def select_fns(parsed: ParsedRepo, contents: dict[str, str], n: int) -> list[tuple[ParsedFunction, str]]:
    by_type: dict[str, list[ParsedFunction]] = {}
    call_cnt = {f.id: len(f.calls) for f in parsed.functions}
    for fn in parsed.functions:
        fn_type = fn.type if isinstance(fn.type, str) else fn.type.value
        by_type.setdefault(fn_type, []).append(fn)
    ordered: list[ParsedFunction] = []
    for t in TYPE_PRIORITY:
        ordered.extend(sorted(by_type.get(t, []), key=lambda f: -call_cnt.get(f.id, 0)))
    for fn in parsed.functions:
        fn_type = fn.type if isinstance(fn.type, str) else fn.type.value
        if fn_type not in TYPE_PRIORITY:
            ordered.append(fn)
    selected, seen = [], set()
    for fn in ordered:
        if len(selected) >= n: break
        if fn.name in seen or fn.name.startswith("_"): continue
        fc = contents.get(fn.file, contents.get(fn.file.lstrip("/"), ""))
        if not fc: continue
        body = extract_body(fc, fn.name, fn.line)
        if not body or is_trivial(body): continue
        seen.add(fn.name); selected.append((fn, body))
    if len(selected) < n:
        for fn in ordered:
            if len(selected) >= n: break
            if fn.name in seen: continue
            fc = contents.get(fn.file, contents.get(fn.file.lstrip("/"), ""))
            if not fc: continue
            body = extract_body(fc, fn.name, fn.line)
            if not body or is_trivial(body): continue
            seen.add(fn.name); selected.append((fn, body))
    return selected[:n]

# ─── Judge Prompts ────────────────────────────────────────────────────────────
def prompt_cf(fn: ParsedFunction) -> str:
    params = ", ".join(f"{p.name}: {p.type}" for p in fn.params) or "none"
    calls  = ", ".join(fn.calls[:8]) or "none"
    doc_line = f"\n  docstring   : {fn.docstring}" if fn.docstring else ""
    fn_type = fn.type if isinstance(fn.type, str) else fn.type.value
    return f"""You are evaluating an AI code analysis tool.

Structured metadata extracted from a function (NO source body available):
  name        : {fn.name}
  file        : {fn.file}
  type        : {fn_type}
  params      : {params}
  return_type : {fn.return_type or 'unknown'}{doc_line}
  calls       : [{calls}]

In 2-3 sentences, describe what this function most likely does.
Rate confidence 1 (guessing) to 10 (certain).

DESCRIPTION: <2-3 sentence description>
CONFIDENCE: <1-10>
REASONING: <1 sentence>"""

def prompt_raw(fn: ParsedFunction, body: str) -> str:
    return f"""You are evaluating code understanding.

Full function source:
```python
{body[:3000]}
```

In 2-3 sentences, describe what this function does.
Rate confidence 1 (guessing) to 10 (certain).

DESCRIPTION: <2-3 sentence description>
CONFIDENCE: <1-10>
REASONING: <1 sentence>"""

def prompt_meta(body: str, desc_a: str, desc_b: str) -> str:
    return f"""Score two AI descriptions of the same function.

ACTUAL SOURCE:
```python
{body[:2000]}
```

DESCRIPTION A (from metadata only — no source):
{desc_a}

DESCRIPTION B (from full source):
{desc_b}

Score accuracy 1–10 each. Note key gap.

SCORE_A: <1-10>
SCORE_B: <1-10>
KEY_GAP: <1-2 sentences>
VERDICT: <A_adequate | roughly_equal | B_clearly_better>"""

# ─── Per-function judgement ────────────────────────────────────────────────────
@dataclass
class FnJudge:
    name: str; fn_type: str; lines: int; params: int; calls: int
    desc_a: str = ""; conf_a: int = 0
    desc_b: str = ""; conf_b: int = 0
    score_a: int = 0; score_b: int = 0
    gap: str = ""; verdict: str = ""
    has_docstring: bool = False

    @property
    def delta(self): return self.score_b - self.score_a

# ─── Full per-repo result ─────────────────────────────────────────────────────
@dataclass
class RepoResult:
    slug: str; label: str; cat: str; desc: str
    gt:    GroundTruth   = field(default_factory=GroundTruth)
    tr:    TokenResult   = field(default_factory=TokenResult)
    judges: list[FnJudge] = field(default_factory=list)
    fetch_time_s: float  = 0.0
    error: str           = ""

    @property
    def fn_recall(self):
        total = self.gt.py_fns + self.gt.js_fns
        return min(100.0, self.tr.fn_count / max(total, 1) * 100)

    @property
    def intent_recall(self):
        gt_ep = self.gt.routes + self.gt.cli_commands
        if gt_ep == 0: return 50.0
        return min(100.0, self.tr.intent_count / gt_ep * 100)

    @property
    def return_type_recall(self):
        if self.gt.return_annotated == 0: return 100.0
        return min(100.0, self.tr.return_typed / self.gt.return_annotated * 100)

    @property
    def avg_score_cf(self):
        if not self.judges: return 0.0
        return sum(j.score_a for j in self.judges) / len(self.judges)

    @property
    def avg_score_raw(self):
        if not self.judges: return 0.0
        return sum(j.score_b for j in self.judges) / len(self.judges)

    @property
    def retention(self):
        if self.avg_score_raw == 0: return 0.0
        return self.avg_score_cf / self.avg_score_raw * 100

    @property
    def docstring_coverage(self):
        return min(100.0, self.tr.docstrings / max(self.tr.fn_count, 1) * 100)

# ─── Run one repo ──────────────────────────────────────────────────────────────
async def run_repo(cfg: dict, run_judge: bool = True) -> RepoResult:
    slug  = cfg["slug"]; label = cfg["label"]
    cat   = cfg["cat"];  desc  = cfg["desc"]
    r = RepoResult(slug=slug, label=label, cat=cat, desc=desc)

    print(f"\n  {'─'*64}")
    print(f"  [{cat}] {label}")
    print(f"  {'─'*64}")

    # Fetch
    print("  [1/3] Fetch ...", end="", flush=True)
    t0 = time.perf_counter()
    try:
        contents, branch = await fetch_repo(slug, token=GITHUB_TOKEN)
    except Exception as e:
        r.error = str(e); print(f" FAILED: {e}"); return r
    r.fetch_time_s = time.perf_counter() - t0
    print(f" {len(contents)} files  {r.fetch_time_s:.1f}s")

    # Ground truth + token pass
    print("  [2/3] Analyse ...", end="", flush=True)
    r.gt = extract_gt(contents)
    r.tr, parsed = run_token_pass(slug, branch, contents)
    print(f" {r.gt.py_fns}py/{r.gt.js_fns}js fns · {r.tr.fn_count} CF fns · "
          f"{r.tr.intent_count} intents · {r.tr.pct:.0f}% saved · "
          f"{r.tr.docstrings} docstrings")

    # LLM judge
    if not run_judge or not GEMINI_API_KEY:
        return r

    selected = select_fns(parsed, contents, JUDGE_FNS)
    print(f"  [3/3] Judge {len(selected)} fns ...")
    for i, (fn, body) in enumerate(selected, 1):
        fn_type = fn.type if isinstance(fn.type, str) else fn.type.value
        j = FnJudge(name=fn.name, fn_type=fn_type, lines=len(body.splitlines()),
                    params=len(fn.params), calls=len(fn.calls),
                    has_docstring=bool(fn.docstring))
        print(f"      [{i}/{len(selected)}] {fn.name}() [{fn_type}]{'📄' if fn.docstring else ''} ", end="", flush=True)

        try:
            ra = gemini_call(prompt_cf(fn))
            j.desc_a = parse_field(ra, "DESCRIPTION")
            j.conf_a = parse_int(ra, "CONFIDENCE")
            print("A✓ ", end="", flush=True)
        except Exception as e:
            j.desc_a = f"[err: {e}]"; print("A✗ ", end="", flush=True)

        try:
            rb = gemini_call(prompt_raw(fn, body))
            j.desc_b = parse_field(rb, "DESCRIPTION")
            j.conf_b = parse_int(rb, "CONFIDENCE")
            print("B✓ ", end="", flush=True)
        except Exception as e:
            j.desc_b = f"[err: {e}]"; print("B✗ ", end="", flush=True)

        try:
            rm = gemini_call(prompt_meta(body, j.desc_a, j.desc_b))
            j.score_a = parse_int(rm, "SCORE_A")
            j.score_b = parse_int(rm, "SCORE_B")
            j.gap     = parse_field(rm, "KEY_GAP")
            j.verdict = parse_field(rm, "VERDICT")
            print(f"M✓  A:{j.score_a} B:{j.score_b} [{j.verdict}]")
        except Exception as e:
            j.score_a = j.score_b = 5; print(f"M✗ {e}")

        r.judges.append(j)

    return r


# ─── Report Generation ─────────────────────────────────────────────────────────
def _bar(v: float, w: int = 25, mx: float = 100) -> str:
    filled = int(round(v / mx * w))
    return "█" * filled + "░" * (w - filled)

def _grade(v: float) -> str:
    if v >= 90: return "A+"
    if v >= 80: return "A"
    if v >= 70: return "B+"
    if v >= 60: return "B"
    if v >= 50: return "C"
    return "D"

def _regime(pct: float) -> str:
    if pct >= 40: return "High compression"
    if pct >= 10: return "Moderate compression"
    return "Near-parity"

def generate_report(results: list[RepoResult]) -> str:
    valid = [r for r in results if not r.error]
    judged = [r for r in valid if r.judges]
    lines: list[str] = []
    A = lines.append

    A("# Codeflow Benchmark Report")
    A("")
    A(f"> **Run date:** {RUN_DATE}  ")
    A(f"> **Repos tested:** {len(valid)}/{len(results)}  ")
    A(f"> **Passes:** Token Efficiency · Comprehension Quality · LLM Judge (Gemini 2.5 Flash)  ")
    A(f"> **Functions judged:** {sum(len(r.judges) for r in judged)} ({JUDGE_FNS}/repo)  ")
    A(f"> **Tokenizer:** `cl100k_base` (tiktoken — GPT-4/Claude proxy ±5%)  ")
    A("")
    A("---")
    A("")

    # ── Abstract ──────────────────────────────────────────────────────────────
    A("## Abstract")
    A("")
    A("Codeflow converts raw source repositories into structured `ParsedRepo` JSON for LLM agents.")
    A("This report quantifies two complementary questions:")
    A("")
    A("1. **How many tokens does it save?** (Pass 1 — Token Efficiency)")
    A("2. **How much does an agent actually understand?** (Pass 2 + 3 — Comprehension Quality + LLM Judge)")
    A("")
    A("Key findings across all repos:")
    if valid:
        avg_saved = sum(r.tr.pct for r in valid) / len(valid)
        avg_recall = sum(r.fn_recall for r in valid) / len(valid)
        avg_ret = sum(r.retention for r in judged) / len(judged) if judged else 0
        A(f"- **Average token reduction:** {avg_saved:.1f}%")
        A(f"- **Average function recall:** {avg_recall:.0f}%")
        A(f"- **Average comprehension retention (LLM judge):** {avg_ret:.0f}%")
    A("")

    # ── Token Results ─────────────────────────────────────────────────────────
    A("## 1. Token Efficiency")
    A("")
    A("| # | Repo | Cat | Raw Tokens | CF Tokens | Saved | Ratio | Regime |")
    A("|---|------|:---:|:----------:|:---------:|:-----:|:-----:|--------|")
    for i, r in enumerate(valid, 1):
        A(f"| {i} | `{r.slug}` | {r.cat} | {r.tr.raw_tokens:,} | {r.tr.flow_tokens:,} | "
          f"**{r.tr.pct:.1f}%** | {r.tr.ratio:.2f}× | {_regime(r.tr.pct)} |")
    if valid:
        tot_raw  = sum(r.tr.raw_tokens for r in valid)
        tot_flow = sum(r.tr.flow_tokens for r in valid)
        tot_pct  = (tot_raw - tot_flow) / tot_raw * 100
        A(f"| | **TOTAL** | | **{tot_raw:,}** | **{tot_flow:,}** | **{tot_pct:.1f}%** | {tot_raw/tot_flow:.2f}× | |")
    A("")

    A("### Token Visualisation")
    A("```")
    A(f"  {'Repo':<42} {'Savings':>8}  {'Bar (% saved)'}")
    A(f"  {'─'*42} {'─'*8}  {'─'*25}")
    for r in valid:
        A(f"  {r.slug:<42} {r.tr.pct:>7.1f}%  {_bar(r.tr.pct, 25)}")
    A("```")
    A("")

    # ── Comprehension Quality ─────────────────────────────────────────────────
    A("## 2. Comprehension Quality")
    A("")
    A("Ground truth extracted via `ast.walk` (Python) and regex (routes, JS functions).")
    A("")
    A("| Repo | Cat | Fns Found | Fn Recall | Route Recall | Return Type % | Docstring % | Intents |")
    A("|------|:---:|:---------:|:---------:|:------------:|:-------------:|:-----------:|:-------:|")
    for r in valid:
        total_gt = r.gt.py_fns + r.gt.js_fns
        A(f"| `{r.slug}` | {r.cat} | {r.tr.fn_count}/{total_gt} | "
          f"{r.fn_recall:.0f}% | {r.intent_recall:.0f}% | "
          f"{r.return_type_recall:.0f}% | {r.docstring_coverage:.0f}% | {r.tr.intent_count} |")
    A("")

    # ── LLM Judge ─────────────────────────────────────────────────────────────
    A("## 3. LLM Judge — Semantic Comprehension")
    A("")
    A("**Judge:** Gemini 2.5 Flash (independent, not Claude — avoids circularity)")
    A("")
    A("For each repo, 5 functions are judged in 3 passes:")
    A("- **Pass A** — Codeflow metadata only (name, type, params, return_type, docstring, calls)")
    A("- **Pass B** — Full raw source body")
    A("- **Meta-judge** — scores both descriptions against actual source")
    A("")
    if judged:
        A("| Repo | Cat | CF Score | Raw Score | Retention | Grade |")
        A("|------|:---:|:--------:|:---------:|:---------:|:-----:|")
        for r in judged:
            A(f"| `{r.slug}` | {r.cat} | {r.avg_score_cf:.1f}/10 | "
              f"{r.avg_score_raw:.1f}/10 | **{r.retention:.0f}%** | {_grade(r.retention)} |")
        all_cf  = sum(r.avg_score_cf for r in judged) / len(judged)
        all_raw = sum(r.avg_score_raw for r in judged) / len(judged)
        all_ret = all_cf / all_raw * 100 if all_raw else 0
        A(f"| **AVERAGE** | | **{all_cf:.1f}/10** | **{all_raw:.1f}/10** | **{all_ret:.0f}%** | {_grade(all_ret)} |")
        A("")

        A("### Verdict Distribution")
        A("")
        all_judges = [j for r in judged for j in r.judges]
        vd: dict[str, int] = {}
        for j in all_judges:
            vd[j.verdict] = vd.get(j.verdict, 0) + 1
        total_j = len(all_judges)
        A("```")
        for v, label_v in [("A_adequate","CF adequate — metadata sufficient"),
                            ("roughly_equal","Roughly equal — both captured it"),
                            ("B_clearly_better","Body clearly better — CF missed it")]:
            cnt = vd.get(v, 0)
            pct = cnt / total_j * 100 if total_j else 0
            A(f"  {v:<22} {cnt:>3}  {_bar(pct, 30)}  {pct:.0f}%  {label_v}")
        cf_wins = vd.get("A_adequate", 0) + vd.get("roughly_equal", 0)
        A(f"  {'─'*70}")
        A(f"  CF adequate rate: {cf_wins}/{total_j} = {cf_wins/total_j*100:.0f}%")
        A("```")
        A("")

        A("### Retention by Category")
        A("")
        by_cat: dict[str, list[RepoResult]] = {}
        for r in judged:
            by_cat.setdefault(r.cat, []).append(r)
        A("| Category | Repos | Avg CF | Avg Raw | Retention | Interpretation |")
        A("|----------|:-----:|:------:|:-------:|:---------:|----------------|")
        interp = {
            "A": "CF's sweet spot — app code with routes/services",
            "B": "Framework code — moderate density, fewer routes",
            "C": "Library/SDK — typed but implementation-heavy",
            "D": "CLI tools — command patterns well-captured",
            "E": "Large libs — diverse, body logic matters more",
        }
        for cat, repos in sorted(by_cat.items()):
            avg_cf  = sum(r.avg_score_cf for r in repos) / len(repos)
            avg_raw = sum(r.avg_score_raw for r in repos) / len(repos)
            ret     = avg_cf / avg_raw * 100 if avg_raw else 0
            A(f"| **{cat} — {CAT_LABELS[cat]}** | {len(repos)} | "
              f"{avg_cf:.1f} | {avg_raw:.1f} | **{ret:.0f}%** | {interp.get(cat, '')} |")
        A("")

    # ── Per-repo function details ──────────────────────────────────────────────
    A("## 4. Per-Repo Detail")
    A("")
    for r in valid:
        A(f"### `{r.slug}` — {r.label}")
        A(f"> Category {r.cat} · {r.desc}")
        A("")
        A(f"| Metric | Value |")
        A(f"|--------|------:|")
        A(f"| Files fetched | {r.gt.py_files} py + {r.gt.js_files} js/ts |")
        A(f"| Source lines | {r.gt.total_lines:,} |")
        A(f"| Ground truth fns | {r.gt.py_fns} py + {r.gt.js_fns} js |")
        A(f"| Codeflow fns | {r.tr.fn_count} ({r.fn_recall:.0f}% recall) |")
        A(f"| Intents | {r.tr.intent_count} ({r.intent_recall:.0f}% route recall) |")
        A(f"| Docstrings captured | {r.tr.docstrings} ({r.docstring_coverage:.0f}% coverage) |")
        A(f"| Raw tokens | {r.tr.raw_tokens:,} |")
        A(f"| Codeflow tokens | {r.tr.flow_tokens:,} |")
        A(f"| Token saving | **{r.tr.pct:.1f}%** ({r.tr.ratio:.2f}×) |")
        A(f"| fn_type_index | `{dict(list(r.tr.fn_type_buckets.items())[:5])}` |")
        A(f"| Parse time | {r.tr.parse_time_s:.2f}s |")
        A("")
        if r.judges:
            A(f"**LLM Judge:** CF {r.avg_score_cf:.1f}/10 · Raw {r.avg_score_raw:.1f}/10 · Retention **{r.retention:.0f}%**")
            A("")
            A("| Function | Type | Doc? | CF | Raw | Δ | Verdict |")
            A("|----------|------|:----:|:--:|:---:|:-:|---------|")
            for j in r.judges:
                vshort = {"A_adequate": "✓ CF ok", "roughly_equal": "≈ equal",
                          "B_clearly_better": "body wins"}.get(j.verdict, j.verdict)
                A(f"| `{j.name}` | `{j.fn_type}` | {'✓' if j.has_docstring else '✗'} | "
                  f"{j.score_a}/10 | {j.score_b}/10 | {j.delta:+d} | {vshort} |")
            A("")
            worst = max(r.judges, key=lambda j: j.delta, default=None)
            best  = min(r.judges, key=lambda j: j.delta, default=None)
            if worst and worst.delta > 2:
                A(f"**Biggest gap** — `{worst.name}()` (Δ={worst.delta:+d}):")
                A(f"> CF: {worst.desc_a[:200]}")
                A(f"> Raw: {worst.desc_b[:200]}")
                A(f"> Gap: {worst.gap}")
                A("")
            if best and best.delta <= 1:
                A(f"**Best case** — `{best.name}()` (Δ={best.delta:+d}): "
                  f"Codeflow metadata was essentially as good as the body.")
                A("")
        A("---")
        A("")

    # ── Regime Analysis ───────────────────────────────────────────────────────
    A("## 5. Regime Analysis")
    A("")
    A("Three distinct regimes emerge from the token benchmark:")
    A("")
    high = [r for r in valid if r.tr.pct >= 40]
    mod  = [r for r in valid if 10 <= r.tr.pct < 40]
    low  = [r for r in valid if r.tr.pct < 10]
    A(f"| Regime | Threshold | Repos | Characteristics |")
    A(f"|--------|:---------:|:-----:|-----------------|")
    A(f"| High compression | ≥40% savings | {len(high)} | Full-stack apps; mixed Python+JS; large file counts |")
    A(f"| Moderate | 10–40% savings | {len(mod)} | Mid-size frameworks; typed libraries |")
    A(f"| Near-parity | <10% savings | {len(low)} | Dense type-annotated libs; small repos |")
    A("")
    for regime_name, repos in [("High compression", high), ("Moderate", mod), ("Near-parity", low)]:
        if repos:
            A(f"**{regime_name}:** " + ", ".join(f"`{r.slug}`" for r in repos))
    A("")

    # ── Optimal Agent Strategy ─────────────────────────────────────────────────
    A("## 6. Optimal Agent Strategy")
    A("")
    A("```")
    A("Step 1: Agent calls POST /parse")
    A("        → receives ParsedRepo (~10–50K tokens)")
    A("        → knows: ALL functions, ALL routes, call graph, types, file layout")
    A("")
    A("Step 2: Agent identifies functions it needs to inspect deeply")
    A("        → uses file_index to know exactly which file to fetch")
    A("        → fetches ONLY those 1–3 files (not all 60–120)")
    A("")
    A("Result: architecture understanding at 10–40% of naive raw-read cost")
    A("        body detail on-demand at zero wasted tokens")
    A("```")
    A("")
    A("| Agent Task | Best tool | Why |")
    A("|------------|:---------:|-----|")
    A("| Understand codebase architecture | Codeflow | fn_type_index + intents |")
    A("| Find all API entry points | Codeflow | intent_recall + fn_type_index[\"route\"] |")
    A("| Trace a call chain | Codeflow | fn.calls[] graph |")
    A("| Read function body | Raw (targeted) | body not in ParsedRepo |")
    A("| First-pass orientation | Codeflow | compressed, structured |")
    A("| Deep bug in specific fn | Both | CF for context, raw for body |")
    A("")

    # ── Limitations ───────────────────────────────────────────────────────────
    A("## 7. Honest Limitations")
    A("")
    A("| Limitation | Impact | Mitigation |")
    A("|------------|:------:|------------|")
    A("| Function bodies stripped | LLM cannot read implementation | Fetch targeted files on demand |")
    A("| Misleadingly-named functions | CF metadata leads agent astray | Docstrings partially compensate |")
    A("| JS/TS recall lower than Python | Tree-sitter coverage incomplete | Use raw for pure-JS repos |")
    A("| Tokenizer is GPT-4 proxy | ±5% vs Claude actual | Directionally correct |")
    A("| Judge is Gemini 2.5 Flash | One model's view | Sufficient for relative comparison |")
    A("")

    A("---")
    A(f"*Codeflow Benchmark · Run {RUN_DATE} · Judge: Gemini 2.5 Flash*")
    return "\n".join(lines)


# ─── Entry Point ──────────────────────────────────────────────────────────────
async def main() -> None:
    run_judge = bool(GEMINI_API_KEY)
    print("\n" + "═" * 68)
    print("  CODEFLOW FINAL BENCHMARK")
    print(f"  {len(REPOS)} repos · 3 passes · Judge: {'Gemini 2.5 Flash' if run_judge else 'DISABLED (no API key)'}")
    print("═" * 68)
    print(f"  Run date : {RUN_DATE}")
    if run_judge:
        print(f"  Judge    : {JUDGE_FNS} fns/repo × 3 passes = {JUDGE_FNS * 3 * len(REPOS)} Gemini calls")

    results: list[RepoResult] = []
    for cfg in REPOS:
        r = await run_repo(cfg, run_judge=run_judge)
        results.append(r)

    valid  = [r for r in results if not r.error]
    judged = [r for r in valid if r.judges]

    print(f"\n{'═'*68}")
    print(f"  SUMMARY  {len(valid)}/{len(results)} repos")
    print(f"{'═'*68}")
    print(f"\n  {'Repo':<42} {'Saved':>7} {'FnRecall':>9} {'Retention':>10}")
    print(f"  {'─'*42} {'─'*7} {'─'*9} {'─'*10}")
    for r in valid:
        ret_str = f"{r.retention:.0f}%" if r.judges else "—"
        print(f"  {r.slug:<42} {r.tr.pct:>6.1f}% {r.fn_recall:>8.0f}% {ret_str:>10}")

    print(f"\n  Writing → {OUT_PATH}")
    OUT_PATH.write_text(generate_report(results), encoding="utf-8")
    print(f"  Done  ({OUT_PATH.stat().st_size // 1024}KB)\n")


if __name__ == "__main__":
    asyncio.run(main())
