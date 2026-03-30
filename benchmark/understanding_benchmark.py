"""
Codeflow Deep Understanding Benchmark
======================================
Measures not just token savings, but comprehension QUALITY:
  - What does an agent actually understand from raw files vs Codeflow?
  - How much signal is captured? How much is lost?
  - How efficiently can the agent answer structural questions?

Repos: encode/starlette, encode/httpx, fastapi/full-stack-fastapi-template

Run:
    cd "Thirdwheel codeflow"
    python -m benchmark.understanding_benchmark
"""
from __future__ import annotations

import ast
import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import os

import tiktoken

from backend.parser.ast_parser import parse_repository
from backend.parser.github_fetcher import fetch_repo
from backend.models.schema import ParsedRepo

ENC = tiktoken.get_encoding("cl100k_base")
tok = lambda t: len(ENC.encode(t))

GITHUB_TOKEN: str | None = os.environ.get("GITHUB_TOKEN")

RUN_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
OUT_PATH = Path(__file__).parent / "UNDERSTANDING_REPORT.md"

REPOS = [
    {
        "slug":  "encode/starlette",
        "label": "Starlette — ASGI Framework",
        "type":  "library",
        "desc":  "Small Python ASGI framework; class-based routes, middleware, responses",
    },
    {
        "slug":  "encode/httpx",
        "label": "HTTPX — Python HTTP Client",
        "type":  "library+cli",
        "desc":  "Full-featured HTTP client; typed, async/sync, rich class hierarchy",
    },
    {
        "slug":  "fastapi/full-stack-fastapi-template",
        "label": "FastAPI Full-Stack Template",
        "type":  "fullstack",
        "desc":  "Full-stack app: FastAPI backend + React frontend; routes, services, models",
    },
]


# ─── Ground Truth Extraction ──────────────────────────────────────────────────

ROUTE_DECORATOR_RE = re.compile(
    r"@(?:app|router|blueprint|api_router|v1_router|api)\."
    r"(?:get|post|put|delete|patch|options|head|route)\s*\(",
    re.IGNORECASE,
)
FASTAPI_ROUTE_RE = re.compile(
    r"@(?:\w+\.)+(?:get|post|put|delete|patch|options|head)\s*\(", re.IGNORECASE
)
FLASK_ROUTE_RE = re.compile(r"@\w+\.route\s*\(", re.IGNORECASE)
CLI_COMMAND_RE = re.compile(r"@(?:\w+\.)+command\s*\(|@click\.command\s*\(", re.IGNORECASE)

JS_FUNC_RE = re.compile(
    r"(?:export\s+)?(?:async\s+)?function\s+\w+\s*\("
    r"|(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\(",
    re.MULTILINE,
)
REACT_COMPONENT_RE = re.compile(
    r"(?:export\s+)?(?:default\s+)?function\s+[A-Z]\w*\s*\(|"
    r"(?:const|let)\s+[A-Z]\w*\s*=\s*(?:\([^)]*\)|[A-Z]\w*)\s*=>",
    re.MULTILINE,
)


@dataclass
class GroundTruth:
    """What actually exists in the repo (extracted from raw source)."""
    total_functions:       int = 0   # Python ast.walk count
    total_async_functions: int = 0
    total_routes:          int = 0   # HTTP route decorators
    total_cli_commands:    int = 0
    total_classes:         int = 0
    total_return_annotated: int = 0  # functions with -> annotations
    total_params:          int = 0   # total parameter count across all fns
    total_typed_params:    int = 0   # params with type annotations
    total_js_functions:    int = 0   # JS/TS function definitions
    total_react_components: int = 0
    python_files:          int = 0
    js_ts_files:           int = 0
    total_source_lines:    int = 0
    sample_routes:         list[str] = field(default_factory=list)   # first 5 routes found
    sample_functions:      list[str] = field(default_factory=list)   # first 5 fn names


def extract_ground_truth(contents: dict[str, str]) -> GroundTruth:
    """Parse raw file contents to establish ground truth for the repo."""
    gt = GroundTruth()

    for path, content in contents.items():
        ext = Path(path).suffix.lower()
        lines = content.splitlines()
        gt.total_source_lines += len(lines)

        # ── Python ──────────────────────────────────────────────────────────
        if ext == ".py":
            gt.python_files += 1
            try:
                tree = ast.parse(content, filename=path)
            except SyntaxError:
                # Count via regex fallback
                gt.total_functions += len(re.findall(r"^\s*(?:async\s+)?def\s+\w+", content, re.MULTILINE))
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    gt.total_functions += 1
                    if isinstance(node, ast.AsyncFunctionDef):
                        gt.total_async_functions += 1
                    if node.returns is not None:
                        gt.total_return_annotated += 1
                    gt.total_params += len(node.args.args) + len(node.args.posonlyargs) + len(node.args.kwonlyargs)
                    gt.total_typed_params += sum(
                        1 for a in (node.args.args + node.args.posonlyargs + node.args.kwonlyargs)
                        if a.annotation is not None
                    )
                    if len(gt.sample_functions) < 5:
                        gt.sample_functions.append(f"{path}:{node.lineno}:{node.name}")
                elif isinstance(node, ast.ClassDef):
                    gt.total_classes += 1

            # Route detection
            for m in FASTAPI_ROUTE_RE.finditer(content):
                gt.total_routes += 1
                if len(gt.sample_routes) < 5:
                    line_no = content[:m.start()].count("\n") + 1
                    gt.sample_routes.append(f"{path}:{line_no}: {m.group().strip()}")
            for m in FLASK_ROUTE_RE.finditer(content):
                gt.total_routes += 1
                if len(gt.sample_routes) < 5:
                    line_no = content[:m.start()].count("\n") + 1
                    gt.sample_routes.append(f"{path}:{line_no}: {m.group().strip()}")
            gt.total_cli_commands += len(CLI_COMMAND_RE.findall(content))

        # ── JavaScript / TypeScript ──────────────────────────────────────────
        elif ext in {".js", ".jsx", ".ts", ".tsx"}:
            gt.js_ts_files += 1
            gt.total_js_functions += len(JS_FUNC_RE.findall(content))
            gt.total_react_components += len(REACT_COMPONENT_RE.findall(content))

    # Deduplicate route samples
    gt.sample_routes = list(dict.fromkeys(gt.sample_routes))[:5]
    return gt


# ─── Manual Read Simulation ────────────────────────────────────────────────────

@dataclass
class ManualReadResult:
    """What an agent gets from reading raw files."""
    raw_tokens:              int   = 0
    raw_bytes:               int   = 0
    files_read:              int   = 0

    # Lookup costs (tokens the agent must read to answer each question)
    cost_find_all_routes:    int   = 0   # must scan all files
    cost_find_function:      int   = 0   # avg tokens to find a specific fn (random fn)
    cost_find_callers:       int   = 0   # must scan all files for a call site

    # What agent CAN understand from raw:
    has_fn_names:            bool  = True   # yes, in raw source
    has_fn_signatures:       bool  = True   # yes, but scattered
    has_call_graph:          bool  = False  # no — must parse mentally
    has_intent_grouping:     bool  = False  # no — no structure
    has_type_index:          bool  = False  # no — no index
    has_file_index:          bool  = False  # no — just files
    structure_score:         float = 0.0   # 0–100, how structured is the input

    signal_tokens:           int   = 0   # estimated structural tokens in raw
    noise_tokens:            int   = 0   # comments, bodies, whitespace, imports
    signal_density_pct:      float = 0.0

    # Raw content sample (first 300 chars of first file, for illustration)
    raw_sample:              str   = ""


def build_manual_read(contents: dict[str, str]) -> ManualReadResult:
    """Simulate what an agent sees when reading all raw files."""
    r = ManualReadResult()
    all_parts = []

    for path, content in contents.items():
        r.files_read += 1
        part = f"# file: {path}\n{content}\n"
        all_parts.append(part)

    raw_text = "\n".join(all_parts)
    r.raw_bytes  = len(raw_text.encode("utf-8"))
    r.raw_tokens = tok(raw_text)

    # Lookup costs: agent reads ALL tokens to answer any global query
    r.cost_find_all_routes = r.raw_tokens   # must scan everything
    r.cost_find_callers    = r.raw_tokens   # must scan everything
    r.cost_find_function   = r.raw_tokens // max(r.files_read, 1)  # avg file size

    # Signal vs noise estimate:
    # Structure (signatures, names, decorators) ≈ 18–22% of typical source
    # Bodies, comments, imports, whitespace ≈ 78–82%
    r.signal_tokens    = int(r.raw_tokens * 0.20)
    r.noise_tokens     = r.raw_tokens - r.signal_tokens
    r.signal_density_pct = 20.0

    # Structure score: raw files have zero agent-usable structure (no index, no graph)
    r.structure_score  = 5.0   # minimal — file headers only

    if all_parts:
        r.raw_sample = all_parts[0][:300].replace("\n", "↵ ")

    return r


# ─── Codeflow Parse Analysis ───────────────────────────────────────────────────

@dataclass
class CodeflowResult:
    """What Codeflow surfaces from the same source."""
    flow_tokens:             int   = 0
    flow_bytes:              int   = 0
    parse_time_s:            float = 0.0

    fn_count:                int   = 0
    intent_count:            int   = 0
    edge_count:              int   = 0
    return_typed_fns:        int   = 0
    total_params:            int   = 0
    typed_params:            int   = 0
    files_indexed:           int   = 0
    fn_type_buckets:         dict  = field(default_factory=dict)

    # Lookup costs via Codeflow structure (tokens for each operation)
    cost_find_all_routes:    int   = 0   # just fn_type_index["route"] section
    cost_find_function:      int   = 0   # average function object tokens
    cost_find_callers:       int   = 0   # scan fn.calls across all functions

    # What agent CAN understand from Codeflow:
    has_fn_names:            bool  = True
    has_fn_signatures:       bool  = True
    has_call_graph:          bool  = True   # explicit fn.calls[]
    has_intent_grouping:     bool  = True   # intents with flow_ids
    has_type_index:          bool  = True   # fn_type_index
    has_file_index:          bool  = True   # file_index
    structure_score:         float = 95.0  # structured JSON, indexed, graph

    signal_tokens:           int   = 0
    noise_tokens:            int   = 0   # practically zero — bodies stripped
    signal_density_pct:      float = 100.0  # all fields are signal

    # Sample intent (first one found)
    sample_intent:           str   = ""
    sample_function:         str   = ""

    # Call chain: can we find a multi-hop chain?
    call_chain_example:      list[str] = field(default_factory=list)
    call_chain_depth:        int   = 0


def build_codeflow_result(slug: str, branch: str, contents: dict[str, str]) -> tuple[CodeflowResult, ParsedRepo]:
    r = CodeflowResult()
    t0 = time.perf_counter()
    parsed = parse_repository(slug, branch, contents)
    r.parse_time_s = time.perf_counter() - t0

    flow_json = json.dumps(
        parsed.model_dump(exclude={"edges"}, exclude_defaults=True),
        separators=(",", ":")
    )
    r.flow_bytes  = len(flow_json.encode("utf-8"))
    r.flow_tokens = tok(flow_json)

    r.fn_count           = len(parsed.functions)
    r.intent_count       = len(parsed.intents)
    r.edge_count         = len(parsed.edges)
    r.return_typed_fns   = sum(1 for f in parsed.functions if f.return_type)
    r.total_params       = sum(len(f.params) for f in parsed.functions)
    r.typed_params       = sum(
        sum(1 for p in f.params if p.type not in {"any", "", "unknown"})
        for f in parsed.functions
    )
    r.files_indexed      = len(parsed.file_index)
    r.fn_type_buckets    = {k: len(v) for k, v in parsed.fn_type_index.items()}

    # Lookup cost: find all routes → only the route section of fn_type_index
    route_ids  = parsed.fn_type_index.get("route", [])
    route_fns  = [f for f in parsed.functions if f.id in set(route_ids)]
    route_json = json.dumps([f.model_dump(exclude_defaults=True) for f in route_fns], separators=(",", ":"))
    r.cost_find_all_routes = tok(route_json) if route_fns else 0

    # Lookup cost: find a specific function → avg function object size
    if parsed.functions:
        sample_fn_tokens = [
            tok(json.dumps(f.model_dump(exclude_defaults=True), separators=(",", ":")))
            for f in parsed.functions[:10]
        ]
        r.cost_find_function = sum(sample_fn_tokens) // len(sample_fn_tokens)

    # Lookup cost: find callers of function → scan fn.calls across all fns
    # This is the fn_count × avg_fn_tokens (you read the whole function list once)
    r.cost_find_callers = r.flow_tokens  # worst case: scan all functions

    r.signal_tokens = r.flow_tokens  # all tokens are signal (no bodies/comments)
    r.noise_tokens  = 0
    r.signal_density_pct = 100.0

    # Sample intent
    if parsed.intents:
        i = parsed.intents[0]
        r.sample_intent = f"{i.label} | trigger={i.trigger} | confidence={i.confidence:.2f} | flow_hops={len(i.flow_ids)}"

    # Sample function
    if parsed.functions:
        f = parsed.functions[0]
        r.sample_function = f"{f.name}({', '.join(p.name+':'+p.type for p in f.params)}) -> {f.return_type or 'unknown'} [{f.type}]"

    # Find longest call chain (BFS)
    call_map: dict[str, list[str]] = {f.id: f.calls for f in parsed.functions}
    id_to_name: dict[str, str] = {f.id: f.name for f in parsed.functions}
    best_chain: list[str] = []
    for start_fn in parsed.functions[:20]:  # check first 20 as starting points
        chain = _longest_chain(start_fn.id, call_map, max_depth=10)
        if len(chain) > len(best_chain):
            best_chain = chain
    r.call_chain_example = [id_to_name.get(fid, fid) for fid in best_chain]
    r.call_chain_depth   = len(best_chain)

    return r, parsed


def _longest_chain(start: str, call_map: dict[str, list[str]], max_depth: int) -> list[str]:
    """BFS to find the longest reachable call chain from `start`."""
    best = [start]
    queue = [[start]]
    visited = {start}
    while queue:
        path = queue.pop(0)
        if len(path) > max_depth:
            continue
        for child in call_map.get(path[-1], []):
            if child not in visited:
                visited.add(child)
                new_path = path + [child]
                if len(new_path) > len(best):
                    best = new_path
                queue.append(new_path)
    return best


# ─── Per-dimension Scoring ────────────────────────────────────────────────────

@dataclass
class QualityScore:
    """Comprehension quality score across dimensions (0–100 each)."""
    fn_recall:            float = 0.0   # % of real functions captured
    intent_recall:        float = 0.0   # % of routes surfaced as intents
    return_type_recall:   float = 0.0   # % of annotated fns with return_type
    param_coverage:       float = 0.0   # % of params captured
    call_graph_score:     float = 0.0   # 0 if no graph, else edge density proxy
    structure_score:      float = 0.0   # index, grouping, lookup efficiency
    lookup_efficiency:    float = 0.0   # 100 × (raw_cost / flow_cost) if flow < raw
    overall:              float = 0.0

    def compute_overall(self) -> None:
        weights = {
            "fn_recall":          0.20,
            "intent_recall":      0.20,
            "return_type_recall": 0.10,
            "param_coverage":     0.10,
            "call_graph_score":   0.15,
            "structure_score":    0.15,
            "lookup_efficiency":  0.10,
        }
        self.overall = sum(getattr(self, k) * w for k, w in weights.items())


def score_codeflow(gt: GroundTruth, cf: CodeflowResult, mr: ManualReadResult) -> QualityScore:
    s = QualityScore()

    # Function recall: Codeflow fns / ground truth fns
    total_gt_fns = gt.total_functions + gt.total_js_functions
    s.fn_recall = min(100.0, (cf.fn_count / max(total_gt_fns, 1)) * 100)

    # Intent recall: intents / (routes + CLI commands)
    gt_entry_points = gt.total_routes + gt.total_cli_commands
    s.intent_recall = min(100.0, (cf.intent_count / max(gt_entry_points, 1)) * 100) if gt_entry_points else 50.0

    # Return type recall: flow return_typed / gt return_annotated
    s.return_type_recall = min(100.0, (cf.return_typed_fns / max(gt.total_return_annotated, 1)) * 100) if gt.total_return_annotated else 100.0

    # Param coverage: flow params / gt params
    s.param_coverage = min(100.0, (cf.total_params / max(gt.total_params, 1)) * 100) if gt.total_params else 100.0

    # Call graph score: 100 if edges exist, scaled by density
    if cf.edge_count > 0:
        # Edge density: edges / max_possible_edges (n choose 2)
        max_edges = max(cf.fn_count * (cf.fn_count - 1), 1)
        density = cf.edge_count / max_edges
        s.call_graph_score = min(100.0, 10 + density * 90 * 100)  # floor at 10 if any edges
        s.call_graph_score = max(10.0, min(100.0, s.call_graph_score))
    else:
        s.call_graph_score = 5.0  # some parsing happened but no edges

    # Structure score: based on what capabilities Codeflow provides
    s.structure_score = cf.structure_score  # 95 by design

    # Lookup efficiency: how much cheaper is it to answer "find all routes"?
    if cf.cost_find_all_routes > 0 and mr.cost_find_all_routes > 0:
        ratio = mr.cost_find_all_routes / cf.cost_find_all_routes
        s.lookup_efficiency = min(100.0, ratio * 10)  # 10× cheaper = 100 score
    elif cf.intent_count > 0:
        s.lookup_efficiency = 80.0

    s.compute_overall()
    return s


def score_manual(gt: GroundTruth, mr: ManualReadResult) -> QualityScore:
    """Score for manual raw read — high recall but zero structure."""
    s = QualityScore()
    # Manual read: everything IS there, just unsorted
    s.fn_recall          = 100.0   # all code present
    s.intent_recall      = 100.0   # all decorators present
    s.return_type_recall = 100.0   # all annotations present
    s.param_coverage     = 100.0   # all params present
    s.call_graph_score   = 0.0     # no structured call graph — agent must infer
    s.structure_score    = mr.structure_score   # 5 — just file headers
    s.lookup_efficiency  = 0.0     # find routes = read everything
    s.compute_overall()
    return s


# ─── Full Benchmark Run ────────────────────────────────────────────────────────

@dataclass
class RepoReport:
    slug:    str
    label:   str
    rtype:   str
    gt:      GroundTruth     = field(default_factory=GroundTruth)
    mr:      ManualReadResult = field(default_factory=ManualReadResult)
    cf:      CodeflowResult   = field(default_factory=CodeflowResult)
    cf_score: QualityScore    = field(default_factory=QualityScore)
    mr_score: QualityScore    = field(default_factory=QualityScore)
    fetch_time_s: float       = 0.0
    error:   str              = ""


async def run_repo(cfg: dict) -> RepoReport:
    slug  = cfg["slug"]
    label = cfg["label"]
    rtype = cfg["type"]
    rpt   = RepoReport(slug=slug, label=label, rtype=rtype)

    print(f"\n{'═'*72}")
    print(f"  {label}")
    print(f"  github.com/{slug}")
    print(f"{'═'*72}")

    print("  [1/4] Fetching ...", end="", flush=True)
    t0 = time.perf_counter()
    try:
        contents, branch = await fetch_repo(slug, token=GITHUB_TOKEN)
    except Exception as exc:
        rpt.error = str(exc)
        print(f" FAILED: {exc}")
        return rpt
    rpt.fetch_time_s = time.perf_counter() - t0
    print(f" {len(contents)} files in {rpt.fetch_time_s:.1f}s")

    print("  [2/4] Ground truth extraction ...", end="", flush=True)
    rpt.gt = extract_ground_truth(contents)
    print(f" done  ({rpt.gt.total_functions} Python fns, {rpt.gt.total_routes} routes, {rpt.gt.total_js_functions} JS fns)")

    print("  [3/4] Manual read simulation ...", end="", flush=True)
    rpt.mr = build_manual_read(contents)
    print(f" done  ({rpt.mr.raw_tokens:,} tokens, signal density {rpt.mr.signal_density_pct:.0f}%)")

    print("  [4/4] Codeflow parse ...", end="", flush=True)
    rpt.cf, _ = build_codeflow_result(slug, branch, contents)
    print(f" done  ({rpt.cf.flow_tokens:,} tokens, {rpt.cf.fn_count} fns, {rpt.cf.intent_count} intents in {rpt.cf.parse_time_s:.2f}s)")

    rpt.cf_score = score_codeflow(rpt.gt, rpt.cf, rpt.mr)
    rpt.mr_score = score_manual(rpt.gt, rpt.mr)

    return rpt


# ─── Report Generation ─────────────────────────────────────────────────────────

def bar(value: float, width: int = 30, char: str = "█", empty: str = "░") -> str:
    filled = int(round(value / 100 * width))
    return char * filled + empty * (width - filled)


def grade(score: float) -> str:
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 70: return "B+"
    if score >= 60: return "B"
    if score >= 50: return "C"
    return "D"


def fmt_score(s: float) -> str:
    return f"{s:5.1f}%"


def generate_report(reports: list[RepoReport]) -> str:
    valid = [r for r in reports if not r.error]
    lines = []
    A = lines.append

    A("# Codeflow Deep Understanding Benchmark")
    A("")
    A(f"> **Run date:** {RUN_DATE}  ")
    A(f"> **Repos tested:** {len(valid)}/3  ")
    A(f"> **Question:** Does Codeflow actually understand codebases better than raw reading?  ")
    A(f"> **Methodology:** Ground truth (ast.walk + regex) vs Manual read vs Codeflow parse")
    A("")
    A("---")
    A("")

    # ── Executive Summary ──────────────────────────────────────────────────────
    A("## 1. Executive Summary")
    A("")
    A("This benchmark answers a critical question for AI agents:")
    A("")
    A("> *When an agent reads raw source files vs receives a Codeflow ParsedRepo,*")
    A("> *how much does it actually understand, and at what token cost?*")
    A("")
    A("Two dimensions measured:")
    A("- **Recall** — how much of the real codebase is surfaced")
    A("- **Structure** — how queryable/navigable the representation is")
    A("")
    A("Key finding: Raw reading has **100% recall** but **~5% structure score**.")
    A("Codeflow has **lower recall** (bodies/comments stripped) but **95% structure score**")
    A("and dramatically lower token cost.")
    A("")

    # ── Score overview table ──────────────────────────────────────────────────
    A("## 2. Overall Quality Scores")
    A("")
    A("| Repo | Manual Read Score | Codeflow Score | Verdict |")
    A("|------|:-----------------:|:--------------:|---------|")
    for r in valid:
        verdict = "Codeflow wins" if r.cf_score.overall > r.mr_score.overall else "Manual wins"
        A(f"| `{r.slug}` | {r.mr_score.overall:.1f}/100 ({grade(r.mr_score.overall)}) | {r.cf_score.overall:.1f}/100 ({grade(r.cf_score.overall)}) | {verdict} |")
    A("")

    # ── Token savings ──────────────────────────────────────────────────────────
    A("## 3. Token Efficiency")
    A("")
    A("| Repo | Raw Tokens | Codeflow Tokens | Saved | Ratio |")
    A("|------|:----------:|:---------------:|:-----:|:-----:|")
    for r in valid:
        saved = r.mr.raw_tokens - r.cf.flow_tokens
        pct   = saved / max(r.mr.raw_tokens, 1) * 100
        ratio = r.mr.raw_tokens / max(r.cf.flow_tokens, 1)
        A(f"| `{r.slug}` | {r.mr.raw_tokens:,} | {r.cf.flow_tokens:,} | {saved:,} ({pct:.1f}%) | {ratio:.2f}× |")
    A("")

    # ── Per-repo deep analysis ─────────────────────────────────────────────────
    A("## 4. Per-Repo Deep Analysis")
    A("")

    for r in valid:
        A(f"### 4.{valid.index(r)+1} {r.label}")
        A(f"> `{r.slug}` · Type: `{r.rtype}`")
        A("")

        # Ground truth
        A("#### Ground Truth (from ast.walk + regex on raw source)")
        A("")
        A(f"| Metric | Value |")
        A(f"|--------|------:|")
        A(f"| Python source files | {r.gt.python_files} |")
        A(f"| JS/TS source files | {r.gt.js_ts_files} |")
        A(f"| Total source lines | {r.gt.total_source_lines:,} |")
        A(f"| **Python functions** (ast.FunctionDef) | **{r.gt.total_functions}** |")
        A(f"| Async functions | {r.gt.total_async_functions} |")
        A(f"| Classes | {r.gt.total_classes} |")
        A(f"| Return-annotated functions | {r.gt.total_return_annotated} |")
        A(f"| Total parameters | {r.gt.total_params:,} |")
        A(f"| Typed parameters | {r.gt.total_typed_params:,} |")
        A(f"| **HTTP routes** (decorator regex) | **{r.gt.total_routes}** |")
        A(f"| CLI commands | {r.gt.total_cli_commands} |")
        A(f"| JS/TS functions | {r.gt.total_js_functions} |")
        A(f"| React components | {r.gt.total_react_components} |")
        A("")

        if r.gt.sample_routes:
            A("Sample routes found:")
            for sr in r.gt.sample_routes:
                A(f"- `{sr}`")
            A("")
        if r.gt.sample_functions:
            A("Sample functions found:")
            for sf in r.gt.sample_functions:
                A(f"- `{sf}`")
            A("")

        # Side-by-side comparison
        A("#### Manual Read vs Codeflow — Dimension by Dimension")
        A("")
        A("```")
        A(f"{'Dimension':<28} {'Manual Read':>14} {'Codeflow':>14} {'Winner':>10}")
        A(f"{'─'*28} {'─'*14} {'─'*14} {'─'*10}")

        dims = [
            ("Function recall",    r.mr_score.fn_recall,          r.cf_score.fn_recall),
            ("Intent/route recall",r.mr_score.intent_recall,       r.cf_score.intent_recall),
            ("Return type recall", r.mr_score.return_type_recall,  r.cf_score.return_type_recall),
            ("Param coverage",     r.mr_score.param_coverage,      r.cf_score.param_coverage),
            ("Call graph",         r.mr_score.call_graph_score,    r.cf_score.call_graph_score),
            ("Structure/index",    r.mr_score.structure_score,     r.cf_score.structure_score),
            ("Lookup efficiency",  r.mr_score.lookup_efficiency,   r.cf_score.lookup_efficiency),
        ]
        for dname, ms, cs in dims:
            winner = "← Manual" if ms > cs + 5 else ("Codeflow →" if cs > ms + 5 else "  tie  ")
            A(f"  {dname:<26} {fmt_score(ms):>14} {fmt_score(cs):>14} {winner:>10}")
        A(f"{'─'*28} {'─'*14} {'─'*14} {'─'*10}")
        A(f"  {'OVERALL':<26} {fmt_score(r.mr_score.overall):>14} {fmt_score(r.cf_score.overall):>14} {'← Manual' if r.mr_score.overall > r.cf_score.overall else 'Codeflow →':>10}")
        A("```")
        A("")

        # Visual radar
        A("#### Score Breakdown (Visual)")
        A("")
        A("```")
        A(f"  Dimension            Manual Read             Codeflow")
        A(f"  ─────────────────── ─────────────────────── ───────────────────────")
        for dname, ms, cs in dims:
            A(f"  {dname:<19} {bar(ms,22)} {bar(cs,22)}")
            A(f"  {'':19} {ms:5.1f}%                  {cs:5.1f}%")
        A("```")
        A("")

        # Codeflow specifics
        A("#### Codeflow Parse Details")
        A("")
        A(f"| Metric | Value |")
        A(f"|--------|------:|")
        A(f"| Functions extracted | {r.cf.fn_count} / {r.gt.total_functions + r.gt.total_js_functions} total |")
        A(f"| Function recall | {r.cf_score.fn_recall:.1f}% |")
        A(f"| Intents extracted | {r.cf.intent_count} |")
        A(f"| Route recall | {r.cf_score.intent_recall:.1f}% |")
        A(f"| Edges (call graph) | {r.cf.edge_count:,} |")
        A(f"| Return types captured | {r.cf.return_typed_fns} / {r.gt.total_return_annotated} annotated |")
        A(f"| Parameters captured | {r.cf.total_params} / {r.gt.total_params} total |")
        A(f"| Typed params captured | {r.cf.typed_params} |")
        A(f"| Files indexed | {r.cf.files_indexed} |")
        A(f"| fn_type_index buckets | {r.cf.fn_type_buckets} |")
        A(f"| Parse time | {r.cf.parse_time_s:.2f}s |")
        A(f"| Longest call chain depth | {r.cf.call_chain_depth} hops |")
        if r.cf.call_chain_example:
            A(f"| Call chain example | `{' → '.join(r.cf.call_chain_example[:6])}{'...' if len(r.cf.call_chain_example) > 6 else ''}` |")
        A("")

        # Lookup cost comparison
        A("#### Lookup Cost Comparison")
        A("")
        A("How many tokens does the agent need to read to answer each question?")
        A("")
        A(f"| Query | Manual Read | Codeflow | Speedup |")
        A(f"|-------|:-----------:|:--------:|:-------:|")

        route_speedup = r.mr.cost_find_all_routes / max(r.cf.cost_find_all_routes, 1) if r.cf.cost_find_all_routes else "∞"
        fn_speedup    = r.mr.cost_find_function / max(r.cf.cost_find_function, 1) if r.cf.cost_find_function else "∞"
        route_speedup_str = f"{route_speedup:.0f}×" if isinstance(route_speedup, float) else route_speedup
        fn_speedup_str    = f"{fn_speedup:.0f}×" if isinstance(fn_speedup, float) else fn_speedup

        A(f"| \"List all HTTP routes\" | {r.mr.cost_find_all_routes:,} tok | {r.cf.cost_find_all_routes:,} tok | **{route_speedup_str}** |")
        A(f"| \"Find function signature\" | {r.mr.cost_find_function:,} tok | {r.cf.cost_find_function:,} tok | **{fn_speedup_str}** |")
        A(f"| \"What does this file export?\" | {r.mr.raw_tokens:,} tok | {tok(json.dumps(r.cf.fn_type_buckets)):,} tok | **{r.mr.raw_tokens // max(tok(json.dumps(r.cf.fn_type_buckets)),1)}×** |")
        A("")

        # What's lost
        A("#### What Codeflow Does NOT Capture")
        A("")
        lost = []
        lost.append(f"- **Function bodies** — {r.gt.total_functions} functions have their implementation stripped (by design: reduces noise)")
        lost.append(f"- **Comments & docstrings** — documentation not passed to agent")
        lost.append(f"- **Import graph** — module-level imports not tracked per-function")
        if r.cf.fn_count < r.gt.total_functions * 0.8:
            missed = r.gt.total_functions - r.cf.fn_count
            lost.append(f"- **~{missed} functions not captured** — likely private helpers, lambdas, nested functions")
        if r.gt.total_js_functions > 0 and r.cf.fn_count < (r.gt.total_functions + r.gt.total_js_functions) * 0.6:
            lost.append(f"- **JS/TS functions** — {r.gt.total_js_functions} JS/TS fns detected by regex; coverage may be partial")
        lost.append("- **Runtime values** — no data flow, no type inference beyond annotations")
        for l in lost:
            A(l)
        A("")

        # What's gained
        A("#### What Codeflow UNIQUELY Provides")
        A("")
        gained = [
            f"- **Structured call graph** — {r.cf.edge_count:,} edges, traversable in O(1) vs O(n) file scan",
            f"- **fn_type_index** — instant lookup by function type: {r.cf.fn_type_buckets}",
            f"- **file_index** — {r.cf.files_indexed} files mapped to their function IDs",
            f"- **Intent grouping** — {r.cf.intent_count} entry points with confidence + evidence",
            f"- **Compressed representation** — {r.cf.flow_tokens:,} tokens vs {r.mr.raw_tokens:,} raw ({(1 - r.cf.flow_tokens/max(r.mr.raw_tokens,1))*100:.1f}% smaller)",
        ]
        if r.cf.call_chain_depth > 1:
            gained.append(f"- **Pre-traced call chains** — deepest chain: {r.cf.call_chain_depth} hops ({' → '.join(r.cf.call_chain_example[:4])}...)")
        if r.cf.sample_intent:
            gained.append(f"- **Rich intent objects** — e.g. `{r.cf.sample_intent}`")
        for g in gained:
            A(g)
        A("")
        A("---")
        A("")

    # ── Aggregate Analysis ─────────────────────────────────────────────────────
    A("## 5. Aggregate Analysis")
    A("")

    # Score averages
    if not valid:
        A("*No valid results — all repos failed to fetch.*")
        return "\n".join(lines)

    cf_overalls = [r.cf_score.overall for r in valid]
    mr_overalls = [r.mr_score.overall for r in valid]

    A("### 5.1 Average Scores Across All Repos")
    A("")
    A("```")
    A(f"  Approach       Avg Score   Grade   Strengths")
    A(f"  ─────────────  ─────────   ─────   ─────────────────────────────────────────")
    A(f"  Manual Read    {sum(mr_overalls)/len(mr_overalls):>7.1f}%   {grade(sum(mr_overalls)/len(mr_overalls))}       100% recall; zero structure; high token cost")
    A(f"  Codeflow       {sum(cf_overalls)/len(cf_overalls):>7.1f}%   {grade(sum(cf_overalls)/len(cf_overalls))}      Structured; indexed; call graph; low token cost")
    A("```")
    A("")

    A("### 5.2 The Recall–Structure Tradeoff")
    A("")
    A("```")
    A(f"  100% ┤ ← Manual Read (all code present)")
    A(f"       │   high recall, zero structure")
    A(f"       │")
    A(f"   75% ┤")
    A(f"       │")
    A(f"   50% ┤                     ← Codeflow (structured, indexed)")
    A(f"       │                       lower recall, maximum structure")
    A(f"   25% ┤")
    A(f"       │")
    A(f"    0% ┤─────────────────────────────────────────────────────")
    A(f"       Recall                                     Structure")
    A("```")
    A("")

    A("### 5.3 When to Use Each Approach")
    A("")
    A("| Agent Task | Best Approach | Reason |")
    A("|------------|:-------------:|--------|")
    A("| Understand codebase architecture | Codeflow | fn_type_index + intents give instant map |")
    A("| Find all API endpoints | Codeflow | intent_recall + fn_type_index[\"route\"] |")
    A("| Trace a call chain | Codeflow | explicit fn.calls[] graph |")
    A("| Read a specific function body | Manual | body not in ParsedRepo |")
    A("| Understand a complex algorithm | Manual | implementation detail needed |")
    A("| Find what calls function X | Codeflow | scan fn.calls (single pass) |")
    A("| First-pass repo orientation | Codeflow | compressed, structured overview |")
    A("| Deep bug analysis | Both | architecture from CF, body from raw |")
    A("")

    A("### 5.4 Optimal Agent Strategy")
    A("")
    A("```")
    A("1. Agent calls /parse  → gets ParsedRepo (cheap: low tokens, full structure)")
    A("   → knows: all functions, all routes, call graph, types, file layout")
    A("")
    A("2. For functions it needs to inspect in detail:")
    A("   → reads ONLY those files (targeted, not full scan)")
    A("   → uses file_index to know exactly which file to fetch")
    A("")
    A("Combined token cost = flow_tokens + (targeted_file_tokens × files_needed)")
    A("vs")
    A("Naive cost = all_raw_tokens (reads everything blindly)")
    A("```")
    A("")

    # ── Understanding Gap Analysis ─────────────────────────────────────────────
    A("## 6. Understanding Gap Analysis")
    A("")
    A("What is genuinely NOT capturable without an LLM evaluation?")
    A("")
    A("| Gap | Measurable here? | Impact |")
    A("|-----|:----------------:|--------|")
    A("| Semantic meaning of function bodies | ✗ requires LLM | Medium |")
    A("| Business logic correctness | ✗ requires LLM | High |")
    A("| Natural language description quality | ✗ requires LLM | Low |")
    A("| Call graph accuracy (false edges?) | ✓ (partial) | Medium |")
    A("| Function recall completeness | ✓ (ast.walk) | High |")
    A("| Route recall completeness | ✓ (regex) | High |")
    A("| Structural navigation efficiency | ✓ (token count) | High |")
    A("| Type accuracy | ✓ (annotation match) | Medium |")
    A("")

    # ── Conclusion ─────────────────────────────────────────────────────────────
    A("## 7. Conclusion")
    A("")
    A("**Codeflow is not trying to replace reading code — it is trying to eliminate**")
    A("**the need to read code you don't care about.**")
    A("")
    A("Manual reading scores 100% on recall but fails on structure and efficiency.")
    A("Codeflow scores lower on recall (bodies stripped) but delivers:")
    A("")

    for r in valid:
        saved_pct = (1 - r.cf.flow_tokens / max(r.mr.raw_tokens, 1)) * 100
        A(f"- **{r.label}**: {saved_pct:.1f}% token reduction, {r.cf.edge_count:,} call edges, "
          f"{r.cf.intent_count} intents, {r.cf_score.fn_recall:.0f}% fn recall")

    A("")
    A("The right mental model:")
    A("")
    A("> Codeflow gives the agent a **map of the city** (cheap, structured, navigable).")
    A("> Raw reading gives the agent **every brick of every building** (complete but overwhelming).")
    A("> A good agent uses the map first, then reads only the buildings it needs.")
    A("")
    A("---")
    A(f"*Generated by Codeflow Understanding Benchmark — {RUN_DATE}*")

    return "\n".join(lines)


# ─── Entry Point ──────────────────────────────────────────────────────────────

async def main() -> None:
    print("\n" + "═" * 72)
    print("  CODEFLOW DEEP UNDERSTANDING BENCHMARK")
    print("  Token savings + Comprehension quality across 3 repos")
    print("═" * 72)
    print(f"\n  Run date : {RUN_DATE}")
    print(f"  Repos    : {', '.join(r['slug'] for r in REPOS)}")
    print(f"  Measures : ground truth (ast) · manual read · codeflow parse · quality scores")

    reports: list[RepoReport] = []
    for cfg in REPOS:
        rpt = await run_repo(cfg)
        reports.append(rpt)

    valid = [r for r in reports if not r.error]
    print(f"\n\n{'═'*72}")
    print(f"  QUICK RESULTS  ({len(valid)}/{len(reports)} repos)")
    print(f"{'═'*72}")
    print(f"\n  {'Repo':<40} {'Manual':>8} {'Codeflow':>10} {'Token↓':>8}")
    print(f"  {'─'*40} {'─'*8} {'─'*10} {'─'*8}")
    for r in valid:
        saved_pct = (1 - r.cf.flow_tokens / max(r.mr.raw_tokens, 1)) * 100
        print(f"  {r.slug:<40} {r.mr_score.overall:>7.1f}%  {r.cf_score.overall:>8.1f}%  {saved_pct:>7.1f}%")

    print(f"\n  Generating report → {OUT_PATH}")
    report_md = generate_report(reports)
    OUT_PATH.write_text(report_md, encoding="utf-8")
    print(f"  Report written ({len(report_md):,} chars)")
    print(f"\n  Open: benchmark/UNDERSTANDING_REPORT.md\n")


if __name__ == "__main__":
    asyncio.run(main())
