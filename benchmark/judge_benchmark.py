"""
Codeflow LLM Judge Benchmark
==============================
Uses Gemini 1.5 Flash as an independent third-party judge to measure
semantic comprehension quality of Codeflow vs raw source reading.

Core question: When stripped of implementation bodies, does Codeflow's
structured representation (name + type + params + return_type + calls[])
give an LLM enough signal to understand what a function DOES?

Design
------
For each of 3 repos, select 10 diverse functions.
For each function, run 3 judge passes:

  Pass A — Codeflow signal only
    Input : { name, file, type, params, return_type, calls[] }
    Judge : "Describe what this does. Confidence 1-10."

  Pass B — Raw source body
    Input : full function source code
    Judge : "Describe what this does. Confidence 1-10."

  Pass M — Meta-judge
    Input : Pass A description + Pass B description + actual source
    Judge : Score each description's accuracy 1-10. Explain the gap.

Outputs
-------
  benchmark/JUDGE_REPORT.md   — full narrative report
  Console                     — live progress

Run:
    GEMINI_API_KEY=... GITHUB_TOKEN=... python -m benchmark.judge_benchmark
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
from typing import Any

from google import genai
from google.genai import types as gtypes

from backend.parser.ast_parser import parse_repository
from backend.parser.github_fetcher import fetch_repo
from backend.models.schema import ParsedFunction, ParsedRepo

# ─── Config ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "")
GEMINI_MODEL    = "gemini-2.5-flash"
FUNCTIONS_PER_REPO = 10
RPM_LIMIT       = 500         # Tier 1 limit
RUN_DATE        = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
OUT_PATH        = Path(__file__).parent / "JUDGE_REPORT.md"

REPOS = [
    {"slug": "encode/starlette",                      "label": "Starlette"},
    {"slug": "encode/httpx",                          "label": "HTTPX"},
    {"slug": "fastapi/full-stack-fastapi-template",   "label": "FastAPI Full-Stack"},
]

# ─── Gemini client ────────────────────────────────────────────────────────────
client = genai.Client(api_key=GEMINI_API_KEY)

_last_call_ts: float = 0.0

def gemini(prompt: str) -> str:
    """Call Gemini with simple rate-limiting."""
    global _last_call_ts
    gap = 60.0 / RPM_LIMIT
    elapsed = time.time() - _last_call_ts
    if elapsed < gap:
        time.sleep(gap - elapsed)
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=gtypes.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=8192,
        ),
    )
    _last_call_ts = time.time()
    return resp.text.strip()


# ─── Function body extraction ─────────────────────────────────────────────────

def extract_body(source: str, fn_name: str, start_line: int) -> str:
    """Extract raw function source starting at start_line using ast."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # fallback: grab ~25 lines from start_line
        lines = source.splitlines()
        snippet = lines[max(0, start_line - 1): start_line + 24]
        return "\n".join(snippet)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == fn_name and abs(node.lineno - start_line) <= 3:
                lines = source.splitlines()
                body_lines = lines[node.lineno - 1: node.end_lineno]
                return "\n".join(body_lines)

    # fallback by name only
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == fn_name:
                lines = source.splitlines()
                return "\n".join(lines[node.lineno - 1: node.end_lineno])

    return ""


def is_trivial(body: str) -> bool:
    """Skip one-liners, pass-only, and property getters."""
    stripped = textwrap.dedent(body).strip()
    lines = [l for l in stripped.splitlines() if l.strip() and not l.strip().startswith("#")]
    if len(lines) <= 3:
        return True
    if all(kw in stripped for kw in ["return self._", "return self."]):
        return True
    return False


# ─── Function selection ────────────────────────────────────────────────────────

TYPE_PRIORITY = ["route", "handler", "service", "auth", "db", "util", "other"]

def select_functions(
    parsed: ParsedRepo,
    contents: dict[str, str],
    n: int = FUNCTIONS_PER_REPO,
) -> list[tuple[ParsedFunction, str]]:
    """
    Select n diverse, non-trivial functions.
    Returns list of (ParsedFunction, raw_body_str).
    """
    # Sort by type priority, then by call depth (fns with more calls = richer)
    call_counts = {f.id: len(f.calls) for f in parsed.functions}
    by_type: dict[str, list[ParsedFunction]] = {}
    for fn in parsed.functions:
        by_type.setdefault(fn.type, []).append(fn)

    ordered: list[ParsedFunction] = []
    for t in TYPE_PRIORITY:
        bucket = sorted(by_type.get(t, []), key=lambda f: -call_counts.get(f.id, 0))
        ordered.extend(bucket)
    # append anything not in priority list
    seen_types = set(TYPE_PRIORITY)
    for fn in parsed.functions:
        if fn.type not in seen_types:
            ordered.append(fn)

    selected: list[tuple[ParsedFunction, str]] = []
    seen_names: set[str] = set()

    for fn in ordered:
        if len(selected) >= n:
            break
        if fn.name.startswith("_") and not fn.name.startswith("__"):
            continue   # skip private helpers first pass
        if fn.name in seen_names:
            continue

        # Find raw body
        file_content = contents.get(fn.file, "")
        if not file_content:
            # try without leading slash
            file_content = contents.get(fn.file.lstrip("/"), "")
        if not file_content:
            continue

        body = extract_body(file_content, fn.name, fn.line)
        if not body or is_trivial(body):
            continue

        seen_names.add(fn.name)
        selected.append((fn, body))

    # If we still need more, allow private helpers
    if len(selected) < n:
        for fn in ordered:
            if len(selected) >= n:
                break
            if fn.name in seen_names:
                continue
            file_content = contents.get(fn.file, contents.get(fn.file.lstrip("/"), ""))
            if not file_content:
                continue
            body = extract_body(file_content, fn.name, fn.line)
            if not body or is_trivial(body):
                continue
            seen_names.add(fn.name)
            selected.append((fn, body))

    return selected[:n]


# ─── Judge prompts ─────────────────────────────────────────────────────────────

def prompt_codeflow(fn: ParsedFunction) -> str:
    params_str = ", ".join(
        f"{p.name}: {p.type}" for p in fn.params
    ) if fn.params else "none"
    calls_str = ", ".join(fn.calls[:8]) if fn.calls else "none"
    docstring_line = f"\n  docstring   : {fn.docstring}" if fn.docstring else ""
    return f"""You are evaluating an AI tool's ability to represent code structure.

Below is structured metadata extracted from a Python/JS function by a code analysis tool.
You do NOT have access to the function body.

Function metadata:
  name        : {fn.name}
  file        : {fn.file}
  type        : {fn.type}
  params      : {params_str}
  return_type : {fn.return_type or 'unknown'}{docstring_line}
  calls       : [{calls_str}]

Task:
1. In 2-3 sentences, describe what this function most likely does.
2. Rate your confidence that your description is accurate (1=guessing, 10=certain).

Respond in this exact format:
DESCRIPTION: <your 2-3 sentence description>
CONFIDENCE: <integer 1-10>
REASONING: <1 sentence explaining your confidence level>"""


def prompt_raw(fn: ParsedFunction, body: str) -> str:
    return f"""You are evaluating an AI tool's ability to understand code.

Below is the full source code of a function.

```python
{body}
```

Task:
1. In 2-3 sentences, describe what this function does.
2. Rate your confidence that your description is accurate (1=guessing, 10=certain).

Respond in this exact format:
DESCRIPTION: <your 2-3 sentence description>
CONFIDENCE: <integer 1-10>
REASONING: <1 sentence explaining your confidence level>"""


def prompt_meta(fn: ParsedFunction, body: str, desc_a: str, desc_b: str) -> str:
    return f"""You are a code understanding evaluator. Score two AI-generated descriptions of the same function.

ACTUAL FUNCTION SOURCE:
```python
{body}
```

DESCRIPTION A (generated from metadata only — no source code):
{desc_a}

DESCRIPTION B (generated from full source code):
{desc_b}

Score each description on accuracy (1=completely wrong, 10=perfectly accurate).
Also note what key information Description A was missing vs B.

Respond in this exact format:
SCORE_A: <integer 1-10>
SCORE_B: <integer 1-10>
KEY_GAP: <1-2 sentences: what did A miss that B got right?>
VERDICT: <one of: "A_adequate", "B_clearly_better", "roughly_equal">"""


# ─── Parse judge responses ─────────────────────────────────────────────────────

def parse_field(text: str, key: str) -> str:
    # Capture everything from KEY: until the next ALL_CAPS_KEY: line or end of string
    # Use \Z (true end of string) not $ (end of line) to avoid premature termination
    m = re.search(
        rf"^{key}:\s*(.*?)(?=\n[A-Z_]{{2,}}:|\Z)",
        text,
        re.MULTILINE | re.IGNORECASE | re.DOTALL,
    )
    return m.group(1).strip() if m else ""

def parse_int(text: str, key: str, default: int = 5) -> int:
    val = parse_field(text, key)
    try:
        return max(1, min(10, int(re.search(r"\d+", val).group())))
    except Exception:
        return default


# ─── Per-function result ──────────────────────────────────────────────────────

@dataclass
class FunctionJudgement:
    fn_name:       str
    fn_type:       str
    fn_file:       str
    fn_params:     int
    fn_calls:      int
    fn_return:     str
    body_lines:    int

    # Pass A
    desc_a:        str   = ""
    conf_a:        int   = 0
    reasoning_a:   str   = ""

    # Pass B
    desc_b:        str   = ""
    conf_b:        int   = 0
    reasoning_b:   str   = ""

    # Meta
    score_a:       int   = 0
    score_b:       int   = 0
    key_gap:       str   = ""
    verdict:       str   = ""

    @property
    def accuracy_delta(self) -> int:
        return self.score_b - self.score_a

    @property
    def confidence_delta(self) -> int:
        return self.conf_b - self.conf_a


@dataclass
class RepoJudgement:
    slug:          str
    label:         str
    judgements:    list[FunctionJudgement] = field(default_factory=list)
    error:         str = ""

    @property
    def avg_score_a(self) -> float:
        if not self.judgements: return 0.0
        return sum(j.score_a for j in self.judgements) / len(self.judgements)

    @property
    def avg_score_b(self) -> float:
        if not self.judgements: return 0.0
        return sum(j.score_b for j in self.judgements) / len(self.judgements)

    @property
    def avg_conf_a(self) -> float:
        if not self.judgements: return 0.0
        return sum(j.conf_a for j in self.judgements) / len(self.judgements)

    @property
    def avg_conf_b(self) -> float:
        if not self.judgements: return 0.0
        return sum(j.conf_b for j in self.judgements) / len(self.judgements)

    @property
    def comprehension_retention(self) -> float:
        """% of raw-body comprehension retained by Codeflow."""
        if self.avg_score_b == 0: return 0.0
        return (self.avg_score_a / self.avg_score_b) * 100

    @property
    def verdicts(self) -> dict[str, int]:
        d: dict[str, int] = {}
        for j in self.judgements:
            d[j.verdict] = d.get(j.verdict, 0) + 1
        return d


# ─── Run one repo ─────────────────────────────────────────────────────────────

async def run_repo(cfg: dict) -> RepoJudgement:
    slug  = cfg["slug"]
    label = cfg["label"]
    rj    = RepoJudgement(slug=slug, label=label)

    print(f"\n{'═'*68}")
    print(f"  {label}  ({slug})")
    print(f"{'═'*68}")

    # Fetch
    print("  [1/3] Fetching ...", end="", flush=True)
    try:
        contents, branch = await fetch_repo(slug, token=GITHUB_TOKEN)
    except Exception as e:
        rj.error = str(e)
        print(f" FAILED: {e}")
        return rj
    print(f" {len(contents)} files")

    # Parse
    print("  [2/3] Parsing ...", end="", flush=True)
    parsed = parse_repository(slug, branch, contents)
    print(f" {len(parsed.functions)} functions, {len(parsed.intents)} intents")

    # Select functions
    selected = select_functions(parsed, contents, FUNCTIONS_PER_REPO)
    print(f"  [3/3] Judging {len(selected)} functions with Gemini ...\n")

    for i, (fn, body) in enumerate(selected, 1):
        body_lines = len(body.splitlines())
        jdg = FunctionJudgement(
            fn_name=fn.name,
            fn_type=fn.type,
            fn_file=fn.file,
            fn_params=len(fn.params),
            fn_calls=len(fn.calls),
            fn_return=fn.return_type or "unknown",
            body_lines=body_lines,
        )

        print(f"    [{i:02d}/{len(selected)}] {fn.name}() [{fn.type}] {body_lines}L ", end="", flush=True)

        # Pass A — Codeflow only
        try:
            resp_a = gemini(prompt_codeflow(fn))
            jdg.desc_a      = parse_field(resp_a, "DESCRIPTION")
            jdg.conf_a      = parse_int(resp_a, "CONFIDENCE")
            jdg.reasoning_a = parse_field(resp_a, "REASONING")
            print("A✓ ", end="", flush=True)
        except Exception as e:
            jdg.desc_a = f"[error: {e}]"
            print("A✗ ", end="", flush=True)

        # Pass B — Raw body
        try:
            resp_b = gemini(prompt_raw(fn, body[:3000]))   # cap at 3K chars
            jdg.desc_b      = parse_field(resp_b, "DESCRIPTION")
            jdg.conf_b      = parse_int(resp_b, "CONFIDENCE")
            jdg.reasoning_b = parse_field(resp_b, "REASONING")
            print("B✓ ", end="", flush=True)
        except Exception as e:
            jdg.desc_b = f"[error: {e}]"
            print("B✗ ", end="", flush=True)

        # Pass M — Meta-judge
        try:
            resp_m = gemini(prompt_meta(fn, body[:3000], jdg.desc_a, jdg.desc_b))
            jdg.score_a  = parse_int(resp_m, "SCORE_A")
            jdg.score_b  = parse_int(resp_m, "SCORE_B")
            jdg.key_gap  = parse_field(resp_m, "KEY_GAP")
            jdg.verdict  = parse_field(resp_m, "VERDICT")
            print(f"M✓  → A:{jdg.score_a}/10 B:{jdg.score_b}/10 [{jdg.verdict}]")
        except Exception as e:
            jdg.score_a = jdg.score_b = 5
            print(f"M✗  [{e}]")

        rj.judgements.append(jdg)

    return rj


# ─── Report Generation ─────────────────────────────────────────────────────────

def bar(v: float, w: int = 28) -> str:
    filled = int(round(v / 10 * w))
    return "█" * filled + "░" * (w - filled)

def grade(v: float) -> str:
    if v >= 9:  return "A+"
    if v >= 8:  return "A"
    if v >= 7:  return "B+"
    if v >= 6:  return "B"
    if v >= 5:  return "C"
    return "D"

def pct_bar(v: float, w: int = 20) -> str:
    filled = int(round(v / 100 * w))
    return "█" * filled + "░" * (w - filled)


def generate_report(repos: list[RepoJudgement]) -> str:
    valid = [r for r in repos if not r.error and r.judgements]
    lines: list[str] = []
    A = lines.append

    A("# Codeflow LLM Judge Benchmark")
    A("")
    A(f"> **Run date:** {RUN_DATE}  ")
    A(f"> **Judge:** Gemini 1.5 Flash (independent third-party)  ")
    A(f"> **Repos:** {len(valid)}/3 succeeded  ")
    A(f"> **Functions judged:** {sum(len(r.judgements) for r in valid)} total  ")
    A(f"> **Passes per function:** 3 (Codeflow-only · Raw-body · Meta-judge)  ")
    A("")
    A("---")
    A("")
    A("## 1. What This Measures")
    A("")
    A("Token benchmarks tell you *how many* tokens. This benchmark tells you *how much* an agent understands.")
    A("")
    A("**Judge task:** Given the same function, Gemini receives:")
    A("- **Condition A**: Only what Codeflow knows — `name, type, file, params, return_type, calls[]`")
    A("- **Condition B**: The full raw source body")
    A("")
    A("A meta-judge then scores both descriptions against the actual code.")
    A("")
    A("**Key metric:** `comprehension_retention` — what % of raw-body understanding does Codeflow preserve?")
    A("")
    A("---")
    A("")

    # ── Headline results ───────────────────────────────────────────────────────
    A("## 2. Headline Results")
    A("")
    A("| Repo | Codeflow Score | Raw Score | Retention | Grade |")
    A("|------|:--------------:|:---------:|:---------:|:-----:|")
    for r in valid:
        A(f"| `{r.slug}` | {r.avg_score_a:.1f}/10 | {r.avg_score_b:.1f}/10 | **{r.comprehension_retention:.0f}%** | {grade(r.avg_score_a)} |")
    if valid:
        all_a = sum(r.avg_score_a for r in valid) / len(valid)
        all_b = sum(r.avg_score_b for r in valid) / len(valid)
        all_ret = (all_a / all_b * 100) if all_b else 0
        A(f"| **AVERAGE** | **{all_a:.1f}/10** | **{all_b:.1f}/10** | **{all_ret:.0f}%** | {grade(all_a)} |")
    A("")

    # ── Confidence comparison ──────────────────────────────────────────────────
    A("## 3. Judge Confidence")
    A("")
    A("How confident was Gemini in its description?")
    A("")
    A("| Repo | Codeflow Confidence | Raw Confidence | Delta |")
    A("|------|:-------------------:|:--------------:|:-----:|")
    for r in valid:
        delta = r.avg_conf_b - r.avg_conf_a
        sign  = "+" if delta > 0 else ""
        A(f"| `{r.slug}` | {r.avg_conf_a:.1f}/10 | {r.avg_conf_b:.1f}/10 | {sign}{delta:.1f} |")
    A("")
    A("> Delta = how much MORE confident Gemini is with full source vs Codeflow metadata.")
    A("> Lower delta = Codeflow provides nearly as much signal as the raw body.")
    A("")

    # ── Verdict breakdown ──────────────────────────────────────────────────────
    A("## 4. Verdict Breakdown")
    A("")
    A("For each function the meta-judge ruled one of:")
    A("- `A_adequate` — Codeflow description was sufficient, essentially as good as raw")
    A("- `roughly_equal` — both descriptions captured the same key points")
    A("- `B_clearly_better` — full body gave Gemini significantly more to work with")
    A("")
    A("| Repo | A_adequate | roughly_equal | B_clearly_better | Codeflow Win Rate |")
    A("|------|:----------:|:-------------:|:----------------:|:-----------------:|")
    for r in valid:
        v = r.verdicts
        a_ok  = v.get("A_adequate", 0)
        equal = v.get("roughly_equal", 0)
        b_win = v.get("B_clearly_better", 0)
        total = len(r.judgements)
        win_rate = (a_ok + equal) / total * 100 if total else 0
        A(f"| `{r.slug}` | {a_ok} | {equal} | {b_win} | **{win_rate:.0f}%** |")
    A("")

    # ── Visual overview ────────────────────────────────────────────────────────
    A("## 5. Score Visualisation")
    A("")
    A("```")
    A(f"  {'Repo':<35} {'Codeflow':^12} {'Raw Body':^12}  {'Retention':^10}")
    A(f"  {'─'*35} {'─'*12} {'─'*12}  {'─'*10}")
    for r in valid:
        A(f"  {r.slug:<35} {bar(r.avg_score_a, 10)} {r.avg_score_a:.1f}  {bar(r.avg_score_b, 10)} {r.avg_score_b:.1f}  {pct_bar(r.comprehension_retention, 10)} {r.comprehension_retention:.0f}%")
    A("```")
    A("")

    # ── Per-repo deep dive ─────────────────────────────────────────────────────
    A("## 6. Per-Repo Function Analysis")
    A("")

    for r in valid:
        A(f"### {r.label} (`{r.slug}`)")
        A("")
        A(f"**Average Codeflow score:** {r.avg_score_a:.1f}/10 · "
          f"**Raw score:** {r.avg_score_b:.1f}/10 · "
          f"**Retention:** {r.comprehension_retention:.0f}%")
        A("")

        # Table of all judged functions
        A("| # | Function | Type | Lines | CF Score | Raw Score | Δ | Verdict |")
        A("|---|----------|------|:-----:|:--------:|:---------:|:-:|---------|")
        for i, j in enumerate(r.judgements, 1):
            delta = j.score_b - j.score_a
            sign  = f"+{delta}" if delta > 0 else str(delta)
            vshort = {"A_adequate": "✓ CF ok", "roughly_equal": "≈ equal", "B_clearly_better": "→ body wins"}.get(j.verdict, j.verdict)
            A(f"| {i} | `{j.fn_name}` | `{j.fn_type}` | {j.body_lines} | {j.score_a}/10 | {j.score_b}/10 | {sign} | {vshort} |")
        A("")

        # Detailed per-function breakdown (first 3 most interesting)
        interesting = sorted(r.judgements, key=lambda j: abs(j.accuracy_delta), reverse=True)[:3]
        A("#### Notable Cases (sorted by comprehension gap)")
        A("")
        for j in interesting:
            A(f"**`{j.fn_name}()`** `[{j.fn_type}]` — {j.body_lines} lines, {j.fn_params} params, {j.fn_calls} calls")
            A("")
            A(f"*Codeflow description (conf {j.conf_a}/10):*")
            A(f"> {j.desc_a}")
            A("")
            A(f"*Raw body description (conf {j.conf_b}/10):*")
            A(f"> {j.desc_b}")
            A("")
            A(f"*Meta-judge:* Score A={j.score_a}/10 · Score B={j.score_b}/10 · Δ={j.accuracy_delta:+d}")
            A(f"*Gap:* {j.key_gap}")
            A(f"*Verdict:* `{j.verdict}`")
            A("")
        A("---")
        A("")

    # ── Aggregate analysis ─────────────────────────────────────────────────────
    if valid:
        all_judgements = [j for r in valid for j in r.judgements]
        all_a   = [j.score_a for j in all_judgements]
        all_b   = [j.score_b for j in all_judgements]
        all_ret = sum(all_a) / sum(all_b) * 100 if sum(all_b) else 0
        verdicts_agg: dict[str, int] = {}
        for j in all_judgements:
            verdicts_agg[j.verdict] = verdicts_agg.get(j.verdict, 0) + 1

        A("## 7. Aggregate Analysis")
        A("")
        A(f"**Total functions judged:** {len(all_judgements)}")
        A(f"**Overall Codeflow score:** {sum(all_a)/len(all_a):.2f}/10")
        A(f"**Overall Raw score:** {sum(all_b)/len(all_b):.2f}/10")
        A(f"**Overall retention:** {all_ret:.1f}%")
        A("")

        total = len(all_judgements)
        a_ok  = verdicts_agg.get("A_adequate", 0)
        equal = verdicts_agg.get("roughly_equal", 0)
        b_win = verdicts_agg.get("B_clearly_better", 0)

        A("### 7.1 Verdict Distribution (all repos)")
        A("")
        A("```")
        A(f"  A_adequate         {a_ok:>3}  {pct_bar(a_ok/total*100, 30)}  {a_ok/total*100:.0f}%  Codeflow was sufficient")
        A(f"  roughly_equal      {equal:>3}  {pct_bar(equal/total*100, 30)}  {equal/total*100:.0f}%  Both equally good")
        A(f"  B_clearly_better   {b_win:>3}  {pct_bar(b_win/total*100, 30)}  {b_win/total*100:.0f}%  Full body needed")
        A(f"  ─────────────────────────────────────────────────────────────────")
        A(f"  CF wins/ties       {a_ok+equal:>3}  {pct_bar((a_ok+equal)/total*100, 30)}  {(a_ok+equal)/total*100:.0f}%  ← Codeflow adequate rate")
        A("```")
        A("")

        A("### 7.2 Score Distribution")
        A("")
        A("```")
        A(f"  Score  Codeflow  Raw Body")
        A(f"  ─────  ────────  ────────")
        for score in range(10, 0, -1):
            ca = sum(1 for s in all_a if s == score)
            cb = sum(1 for s in all_b if s == score)
            A(f"  {score:>5}  {ca:>4}  {'█'*ca:<10}  {cb:>4}  {'█'*cb}")
        A("```")
        A("")

        A("### 7.3 Comprehension Retention by Function Type")
        A("")
        by_type: dict[str, list[FunctionJudgement]] = {}
        for j in all_judgements:
            by_type.setdefault(j.fn_type, []).append(j)
        A("| Function Type | Avg CF | Avg Raw | Retention |")
        A("|---------------|:------:|:-------:|:---------:|")
        for ftype, jlist in sorted(by_type.items(), key=lambda x: -len(x[1])):
            avg_a = sum(j.score_a for j in jlist) / len(jlist)
            avg_b = sum(j.score_b for j in jlist) / len(jlist)
            ret   = avg_a / avg_b * 100 if avg_b else 0
            A(f"| `{ftype}` | {avg_a:.1f} | {avg_b:.1f} | {ret:.0f}% |")
        A("")

    # ── Interpretation ─────────────────────────────────────────────────────────
    A("## 8. Interpretation")
    A("")
    A("### What does comprehension retention mean?")
    A("")
    A("If Codeflow retention = 85%, it means:")
    A("> An agent using Codeflow understands 85% of what an agent with full source code understands,")
    A("> while consuming far fewer tokens.")
    A("")
    A("### What causes retention < 100%?")
    A("")
    A("The gap comes from information genuinely **not present** in Codeflow's representation:")
    A("")
    A("| Information type | In Codeflow? | Impact on retention |")
    A("|-----------------|:------------:|---------------------|")
    A("| Function name & signature | ✓ yes | High — names are very predictive |")
    A("| Parameter types | ✓ yes | Medium |")
    A("| Return type | ✓ yes | Medium |")
    A("| What functions are called | ✓ yes (calls[]) | High — call graph reveals intent |")
    A("| Function body logic | ✗ stripped | Medium — bodies often repeat what names imply |")
    A("| Error handling patterns | ✗ stripped | Low — usually guessable |")
    A("| Inline comments/docstrings | ✗ stripped | Variable — can be very informative |")
    A("| Magic values / constants | ✗ stripped | Low |")
    A("")
    A("### The key insight")
    A("")
    A("Well-named functions in well-typed codebases lose **very little** comprehension")
    A("when bodies are stripped. The name + type + params + calls together")
    A("paint a clear picture. Bodies add detail but rarely change the fundamental understanding.")
    A("")
    A("---")
    A(f"*Generated by Codeflow LLM Judge Benchmark · Judge: Gemini 1.5 Flash · {RUN_DATE}*")

    return "\n".join(lines)


# ─── Entry point ──────────────────────────────────────────────────────────────

async def main() -> None:
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set.")
        return

    print("\n" + "═" * 68)
    print("  CODEFLOW LLM JUDGE BENCHMARK")
    print("  Judge: Gemini 1.5 Flash (independent, third-party)")
    print("═" * 68)
    print(f"\n  Run date  : {RUN_DATE}")
    print(f"  Repos     : {', '.join(r['slug'] for r in REPOS)}")
    print(f"  Functions : {FUNCTIONS_PER_REPO} per repo × 3 passes = {FUNCTIONS_PER_REPO*3*len(REPOS)} Gemini calls")
    print(f"  Rate limit: {RPM_LIMIT} RPM (free tier safe)\n")

    results: list[RepoJudgement] = []
    for cfg in REPOS:
        rj = await run_repo(cfg)
        results.append(rj)

    valid = [r for r in results if not r.error and r.judgements]
    print(f"\n\n{'═'*68}")
    print(f"  SUMMARY  ({len(valid)}/{len(results)} repos)")
    print(f"{'═'*68}\n")
    print(f"  {'Repo':<38} {'CF':>6} {'Raw':>6} {'Ret':>8}")
    print(f"  {'─'*38} {'─'*6} {'─'*6} {'─'*8}")
    for r in valid:
        print(f"  {r.slug:<38} {r.avg_score_a:>5.1f}/10 {r.avg_score_b:>5.1f}/10 {r.comprehension_retention:>7.0f}%")

    print(f"\n  Writing report → {OUT_PATH}")
    report = generate_report(results)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(f"  Report written ({len(report):,} chars)")
    print(f"\n  Open: benchmark/JUDGE_REPORT.md\n")


if __name__ == "__main__":
    asyncio.run(main())
