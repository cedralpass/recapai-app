#!/usr/bin/env python3
"""
Hyperparameter tuning eval for gpt-4.1-mini on the two taxonomy tasks.

Runs per-axis sweeps (vary one param, hold others at baseline) and ranks
results by judge quality score, with response time as a secondary metric.

Usage:
    # Per-axis sweeps (default, ~34 configs × 2 tasks)
    .venv/bin/python scripts/eval_tuning.py

    # Single task only
    .venv/bin/python scripts/eval_tuning.py --task consolidate

    # Full combinatorial grid (168 configs × 2 tasks — expensive)
    .venv/bin/python scripts/eval_tuning.py --grid

    # Skip judge scoring (much faster, quality column blank)
    .venv/bin/python scripts/eval_tuning.py --no-judge

    # Run each config N times and average (variance analysis)
    .venv/bin/python scripts/eval_tuning.py --runs 3
"""

import argparse
import itertools
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, stdev

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / "aiapi" / ".env")
load_dotenv(PROJECT_ROOT / "recap" / ".env", override=False)

from openai import OpenAI  # noqa: E402

from tests.seed_data import SEED_ARTICLES  # noqa: E402

# ── Config ────────────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.environ.get("AI_API_OPENAI") or os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-4.1-mini"
JUDGE_MODEL = "gpt-4o"

# Current production baseline
BASELINE = {"temperature": 0.3, "frequency_penalty": 0.15, "presence_penalty": 0.0}

# Sweep ranges for each axis
SWEEP = {
    "temperature": [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0],
    "frequency_penalty": [0.0, 0.1, 0.15, 0.2, 0.3, 0.5],
    "presence_penalty": [0.0, 0.1, 0.3, 0.5],
}


@dataclass
class RunResult:
    temperature: float
    frequency_penalty: float
    presence_penalty: float
    elapsed: float | None
    valid: bool
    complete: bool
    coherence: float | None
    usefulness: float | None
    rationale: str
    error: str = ""

    @property
    def judge_avg(self) -> float | None:
        if self.coherence is not None and self.usefulness is not None:
            return (self.coherence + self.usefulness) / 2
        return None

    @property
    def label(self) -> str:
        return f"t={self.temperature} fp={self.frequency_penalty} pp={self.presence_penalty}"


# ── Context builders (mirror recap/taxonomy_helpers.py) ───────────────────────


def build_organize_context() -> str:
    data: dict = {}
    for article in SEED_ARTICLES:
        cat = article.get("category")
        if not cat:
            continue
        if cat not in data:
            data[cat] = {"count": 0, "subcats": set()}
        data[cat]["count"] += 1
        if article.get("sub_categories"):
            try:
                data[cat]["subcats"].update(json.loads(article["sub_categories"]))
            except (json.JSONDecodeError, TypeError):
                pass
    cats = sorted(data.items(), key=lambda x: x[1]["count"], reverse=True)
    lines = ["I am using this taxonomy to categorize content:"]
    for cat, d in cats:
        count = d["count"]
        subcats = sorted(d["subcats"])
        word = "article" if count == 1 else "articles"
        if subcats:
            lines.append(f"- {cat} ({count} {word}): {', '.join(subcats[:4])}")
        else:
            lines.append(f"- {cat} ({count} {word})")
    return "\n".join(lines)


def build_split_context(category_name: str) -> tuple[str, list[int]]:
    articles = [a for a in SEED_ARTICLES if a["category"] == category_name]
    lines = [
        f'Category "{category_name}" has grown large and needs splitting into smaller groups.',
        "Here are the articles with their content themes and summaries:",
        "",
    ]
    article_ids = []
    for i, article in enumerate(articles, start=1):
        article_ids.append(i)
        subcats = []
        if article.get("sub_categories"):
            try:
                subcats = json.loads(article["sub_categories"])
            except (json.JSONDecodeError, TypeError):
                pass
        subcats_str = ", ".join(subcats) if subcats else "none"
        summary = article.get("summary") or ""
        summary_str = (summary[:200] + "…") if len(summary) > 200 else summary
        lines.append(f"[id:{i}] {article.get('title') or 'Untitled'} | themes: {subcats_str}")
        if summary_str:
            lines.append(f"  summary: {summary_str}")
    return "\n".join(lines), article_ids


# ── Prompts (exact copies from recap/tasks.py) ────────────────────────────────

ORGANIZE_PROMPT = (
    "Can you recommend a consolidated category list? "
    "Merge similar or related categories, especially small ones with 1-3 articles. "
    "Keep category names concise and understandable to a human reader."
)
ORGANIZE_FORMAT = (
    "Respond with JSON in this exact structure:\n"
    "{\n"
    '  "description": "A concise summary of the changes made.",\n'
    '  "mappings": [\n'
    '    {"new_category": "New Name", "old_category": "Old Name"},\n'
    '    {"new_category": "New Name", "old_category": "Old Name"}\n'
    "  ]\n"
    "}"
)
SPLIT_PROMPT = (
    "Split these articles into 2-4 distinct, meaningful groups based on their themes. "
    "Name each group clearly (2-4 words). "
    "Assign every article to exactly one group."
)
SPLIT_FORMAT = (
    "Respond with JSON in this exact structure:\n"
    "{\n"
    '  "description": "Brief rationale for the groupings",\n'
    '  "assignments": [\n'
    '    {"article_id": 42, "new_category": "Group Name"},\n'
    '    {"article_id": 43, "new_category": "Group Name"}\n'
    "  ]\n"
    "}"
)

JUDGE_PROMPT = """\
You are evaluating AI-generated taxonomy suggestions for a personal reading list app.
Score the following groupings on two dimensions (1–5 each):
- Coherence: are items in each group genuinely similar in topic?
- Usefulness: would a human reader find these group names clear and helpful?

Return JSON only: {{"coherence": N, "usefulness": N, "rationale": "one sentence"}}

Groupings to evaluate:
{suggestions}"""


# ── OpenAI helpers ────────────────────────────────────────────────────────────


def call_model(
    client: OpenAI,
    context: str,
    prompt: str,
    format_instructions: str,
    temperature: float,
    frequency_penalty: float,
    presence_penalty: float,
) -> tuple[dict | None, float]:
    messages = []
    if context:
        messages.append({"role": "system", "content": context})
    messages.append({"role": "user", "content": f"{prompt}\n\n{format_instructions}"})

    start = time.time()
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        max_completion_tokens=4096,
        temperature=temperature,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
    )
    elapsed = time.time() - start

    try:
        return json.loads(response.choices[0].message.content), elapsed
    except json.JSONDecodeError:
        return None, elapsed


def get_judge_score(client: OpenAI, suggestions_str: str) -> tuple[float | None, float | None, str]:
    prompt = JUDGE_PROMPT.format(suggestions=suggestions_str)
    try:
        response = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
            max_completion_tokens=256,
        )
        data = json.loads(response.choices[0].message.content)
        return data.get("coherence"), data.get("usefulness"), data.get("rationale", "")
    except Exception as e:
        return None, None, str(e)


# ── Single config runner ──────────────────────────────────────────────────────


def run_consolidate(
    client: OpenAI,
    temperature: float,
    frequency_penalty: float,
    presence_penalty: float,
    seed_categories: set[str],
    use_judge: bool,
    context: str,
) -> RunResult:
    try:
        data, elapsed = call_model(
            client,
            context,
            ORGANIZE_PROMPT,
            ORGANIZE_FORMAT,
            temperature,
            frequency_penalty,
            presence_penalty,
        )
    except Exception as e:
        return RunResult(temperature, frequency_penalty, presence_penalty, None, False, False, None, None, "", str(e))

    valid = data is not None and "mappings" in data
    complete = False
    coherence = usefulness = None
    rationale = ""

    if valid:
        mapped_old = {m.get("old_category") for m in data["mappings"]}
        complete = seed_categories.issubset(mapped_old)

    if use_judge and valid:
        desc = data.get("description", "")
        mappings_str = json.dumps(data.get("mappings", []), indent=2)
        coherence, usefulness, rationale = get_judge_score(client, f"{desc}\n{mappings_str}")

    return RunResult(
        temperature, frequency_penalty, presence_penalty, elapsed, valid, complete, coherence, usefulness, rationale
    )


def run_split(
    client: OpenAI,
    temperature: float,
    frequency_penalty: float,
    presence_penalty: float,
    article_id_set: set[int],
    use_judge: bool,
    context: str,
) -> RunResult:
    try:
        data, elapsed = call_model(
            client,
            context,
            SPLIT_PROMPT,
            SPLIT_FORMAT,
            temperature,
            frequency_penalty,
            presence_penalty,
        )
    except Exception as e:
        return RunResult(temperature, frequency_penalty, presence_penalty, None, False, False, None, None, "", str(e))

    valid = data is not None and "assignments" in data
    complete = False
    coherence = usefulness = None
    rationale = ""

    if valid:
        assigned_ids = {a.get("article_id") for a in data["assignments"]}
        complete = article_id_set.issubset(assigned_ids)

    if use_judge and valid:
        groups: dict = {}
        for a in data.get("assignments", []):
            g = a.get("new_category", "Unknown")
            groups[g] = groups.get(g, 0) + 1
        desc = data.get("description", "")
        coherence, usefulness, rationale = get_judge_score(
            client, f"{desc}\n\nGroup sizes:\n{json.dumps(groups, indent=2)}"
        )

    return RunResult(
        temperature, frequency_penalty, presence_penalty, elapsed, valid, complete, coherence, usefulness, rationale
    )


# ── Config generation ─────────────────────────────────────────────────────────


def per_axis_configs() -> list[dict]:
    """One config per sweep value, varying one axis at a time from baseline."""
    configs = []
    seen = set()

    def add(t, fp, pp):
        key = (t, fp, pp)
        if key not in seen:
            seen.add(key)
            configs.append({"temperature": t, "frequency_penalty": fp, "presence_penalty": pp})

    # Always include baseline
    add(BASELINE["temperature"], BASELINE["frequency_penalty"], BASELINE["presence_penalty"])

    for t in SWEEP["temperature"]:
        add(t, BASELINE["frequency_penalty"], BASELINE["presence_penalty"])
    for fp in SWEEP["frequency_penalty"]:
        add(BASELINE["temperature"], fp, BASELINE["presence_penalty"])
    for pp in SWEEP["presence_penalty"]:
        add(BASELINE["temperature"], BASELINE["frequency_penalty"], pp)

    return configs


def grid_configs() -> list[dict]:
    """Full combinatorial grid."""
    return [
        {"temperature": t, "frequency_penalty": fp, "presence_penalty": pp}
        for t, fp, pp in itertools.product(SWEEP["temperature"], SWEEP["frequency_penalty"], SWEEP["presence_penalty"])
    ]


# ── Reporting ─────────────────────────────────────────────────────────────────


def check(val: bool) -> str:
    return "✓" if val else "✗"


def fmt_score(val: float | None) -> str:
    return f"{val:.2f}" if val is not None else "—"


def fmt_time(val: float | None) -> str:
    return f"{val:.1f}s" if val is not None else "err"


def print_ranked_table(results: list[RunResult], task_name: str, runs: int) -> None:
    print(f"\n### {task_name} — ranked by quality, then speed\n")

    # Sort: completeness first (failures sink to bottom), then judge score desc, then time asc
    def sort_key(r: RunResult):
        score = r.judge_avg if r.judge_avg is not None else -1.0
        time_val = r.elapsed if r.elapsed is not None else 999.0
        return (0 if r.complete else 1, -score, time_val)

    sorted_results = sorted(results, key=sort_key)

    avg_label = "Judge avg" if runs == 1 else f"Judge avg (n={runs})"
    header = f"| {'Params':<36} | {'Time':>6} | {'Valid':^7} | {'Complete':^8} | {'Coherence':^9} | {'Useful':^7} | {avg_label:^13} |"
    sep = f"|{'-'*38}|{'-'*8}|{'-'*9}|{'-'*10}|{'-'*11}|{'-'*9}|{'-'*15}|"
    print(header)
    print(sep)

    baseline_key = (BASELINE["temperature"], BASELINE["frequency_penalty"], BASELINE["presence_penalty"])

    for r in sorted_results:
        is_baseline = (r.temperature, r.frequency_penalty, r.presence_penalty) == baseline_key
        marker = " *" if is_baseline else "  "
        label = f"t={r.temperature} fp={r.frequency_penalty} pp={r.presence_penalty}{marker}"
        print(
            f"| {label:<36} | {fmt_time(r.elapsed):>6} | {check(r.valid):^7} | "
            f"{check(r.complete):^8} | {fmt_score(r.coherence):^9} | {fmt_score(r.usefulness):^7} | "
            f"{fmt_score(r.judge_avg):^13} |"
        )

    print("\n_* = current production baseline_")


def print_recommendation(consolidate_results: list[RunResult], split_results: list[RunResult]) -> None:
    print("\n---\n\n## Recommendation\n")

    def best(results: list[RunResult]) -> RunResult | None:
        valid = [r for r in results if r.complete and r.judge_avg is not None]
        if not valid:
            return None
        return min(valid, key=lambda r: (-r.judge_avg, r.elapsed or 999))

    best_c = best(consolidate_results)
    best_s = best(split_results)

    for task, best_r in [("Consolidate", best_c), ("Split", best_s)]:
        if best_r:
            print(
                f"**{task}:** `temperature={best_r.temperature}  frequency_penalty={best_r.frequency_penalty}  presence_penalty={best_r.presence_penalty}`"
            )
            print(f"  — judge avg {fmt_score(best_r.judge_avg)}/5, response time {fmt_time(best_r.elapsed)}\n")
        else:
            print(f"**{task}:** no valid results to recommend\n")

    # Suggest a single unified config if best params overlap
    if best_c and best_s:
        same = (
            best_c.temperature == best_s.temperature
            and best_c.frequency_penalty == best_s.frequency_penalty
            and best_c.presence_penalty == best_s.presence_penalty
        )
        if same:
            print("Both tasks agree on the same config — safe to apply universally.")
        else:
            print(
                "Tasks prefer different configs. Consider separate env vars "
                "(`AI_OPEN_AI_TAXONOMY_MODEL` + tuning params) if the quality delta justifies it."
            )


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Hyperparameter tuning eval for gpt-4.1-mini")
    parser.add_argument("--grid", action="store_true", help="Full combinatorial grid instead of per-axis sweeps")
    parser.add_argument("--no-judge", action="store_true", help="Skip LLM-as-judge scoring (much faster)")
    parser.add_argument("--task", choices=["consolidate", "split", "both"], default="both")
    parser.add_argument(
        "--runs", type=int, default=1, metavar="N", help="Run each config N times and average (default: 1)"
    )
    parser.add_argument(
        "--configs", nargs="+", metavar="t,fp,pp", help="Explicit configs to test, e.g. '0.3,0.15,0.0' '0.3,0.0,0.0'"
    )
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        sys.exit("ERROR: No OpenAI API key found. Set AI_API_OPENAI in aiapi/.env")

    if args.configs:
        configs = []
        for raw in args.configs:
            parts = [float(x) for x in raw.split(",")]
            if len(parts) != 3:
                sys.exit(f"ERROR: --configs values must be 't,fp,pp' — got '{raw}'")
            configs.append({"temperature": parts[0], "frequency_penalty": parts[1], "presence_penalty": parts[2]})
    else:
        configs = grid_configs() if args.grid else per_axis_configs()
    use_judge = not args.no_judge

    total_calls = len(configs) * (2 if args.task == "both" else 1) * args.runs
    judge_calls = total_calls if use_judge else 0

    print(f"# Taxonomy Tuning Eval — {time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Model  : {MODEL}")
    print(f"Mode   : {'full grid' if args.grid else 'per-axis sweeps'}")
    print(f"Task   : {args.task}")
    print(f"Runs   : {args.runs} per config")
    print(f"Configs: {len(configs)}")
    print(f"Calls  : ~{total_calls} model + ~{judge_calls} judge\n")

    if args.grid and len(configs) > 50:
        print(f"WARNING: {len(configs)} configs × {args.runs} run(s) = {total_calls} calls. This may take a while.\n")

    client = OpenAI(api_key=OPENAI_API_KEY)

    org_context = build_organize_context()
    split_context, split_ids = build_split_context("Artificial Intelligence")
    seed_categories = {a["category"] for a in SEED_ARTICLES if a.get("category")}
    split_id_set = set(split_ids)

    consolidate_results: list[RunResult] = []
    split_results: list[RunResult] = []

    total = len(configs)
    for i, cfg in enumerate(configs, start=1):
        t, fp, pp = cfg["temperature"], cfg["frequency_penalty"], cfg["presence_penalty"]
        label = f"t={t} fp={fp} pp={pp}"
        print(f"[{i}/{total}] {label}")

        if args.task in ("consolidate", "both"):
            run_times: list[float] = []
            run_coherence: list[float] = []
            run_usefulness: list[float] = []
            last_r = None

            for _ in range(args.runs):
                r = run_consolidate(client, t, fp, pp, seed_categories, use_judge, org_context)
                last_r = r
                if r.elapsed:
                    run_times.append(r.elapsed)
                if r.coherence is not None:
                    run_coherence.append(r.coherence)
                if r.usefulness is not None:
                    run_usefulness.append(r.usefulness)

            if args.runs > 1 and last_r:
                last_r.elapsed = mean(run_times) if run_times else None
                last_r.coherence = mean(run_coherence) if run_coherence else None
                last_r.usefulness = mean(run_usefulness) if run_usefulness else None

            status = f"  consolidate: {fmt_time(last_r.elapsed if last_r else None)}  complete={check(last_r.complete if last_r else False)}  judge={fmt_score(last_r.judge_avg if last_r else None)}"
            print(status)
            if last_r:
                consolidate_results.append(last_r)

        if args.task in ("split", "both"):
            run_times = []
            run_coherence = []
            run_usefulness = []
            last_r = None

            for _ in range(args.runs):
                r = run_split(client, t, fp, pp, split_id_set, use_judge, split_context)
                last_r = r
                if r.elapsed:
                    run_times.append(r.elapsed)
                if r.coherence is not None:
                    run_coherence.append(r.coherence)
                if r.usefulness is not None:
                    run_usefulness.append(r.usefulness)

            if args.runs > 1 and last_r:
                last_r.elapsed = mean(run_times) if run_times else None
                last_r.coherence = mean(run_coherence) if run_coherence else None
                last_r.usefulness = mean(run_usefulness) if run_usefulness else None

            status = f"  split:       {fmt_time(last_r.elapsed if last_r else None)}  complete={check(last_r.complete if last_r else False)}  judge={fmt_score(last_r.judge_avg if last_r else None)}"
            print(status)
            if last_r:
                split_results.append(last_r)

    print("\n---\n")
    print("## Results\n")

    if consolidate_results:
        print_ranked_table(consolidate_results, "Consolidate", args.runs)
    if split_results:
        print_ranked_table(split_results, "Split", args.runs)

    if consolidate_results or split_results:
        print_recommendation(consolidate_results, split_results)


if __name__ == "__main__":
    main()
