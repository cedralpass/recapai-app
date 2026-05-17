#!/usr/bin/env python3
"""
Taxonomy model evaluation script.

Compares OpenAI models on the consolidate and split taxonomy tasks using
seed data from tests/seed_data.py — no database or running server required.

Usage:
    .venv/bin/python scripts/eval_taxonomy_models.py
    .venv/bin/python scripts/eval_taxonomy_models.py --models gpt-5-mini gpt-5.4-nano
    .venv/bin/python scripts/eval_taxonomy_models.py --no-judge
    .venv/bin/python scripts/eval_taxonomy_models.py --task consolidate
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Resolve project root so imports work regardless of CWD
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / "aiapi" / ".env")
load_dotenv(PROJECT_ROOT / "recap" / ".env", override=False)

from openai import OpenAI  # noqa: E402

from tests.seed_data import SEED_ARTICLES  # noqa: E402

# ── Config ────────────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.environ.get("AI_API_OPENAI") or os.environ.get("OPENAI_API_KEY")

MODELS = [
    "gpt-4o",
    "gpt-4.1-mini",
    "gpt-5-mini",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
]

JUDGE_MODEL = "gpt-4o"

# ── Context builders (mirror recap/taxonomy_helpers.py, no DB needed) ─────────


def build_organize_context() -> str:
    data: dict = {}
    for article in SEED_ARTICLES:
        cat = article["category"]
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
        article_word = "article" if count == 1 else "articles"
        if subcats:
            lines.append(f"- {cat} ({count} {article_word}): {', '.join(subcats[:4])}")
        else:
            lines.append(f"- {cat} ({count} {article_word})")
    return "\n".join(lines)


def build_split_context(category_name: str) -> tuple[str, list[int]]:
    """Returns (context_str, list_of_article_ids) using sequential IDs 1..N."""
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

JUDGE_PROMPT_TEMPLATE = """\
You are evaluating AI-generated taxonomy suggestions for a personal reading list app.
Score the following groupings on two dimensions (1–5 each):
- Coherence: are items in each group genuinely similar in topic?
- Usefulness: would a human reader find these group names clear and helpful?

Return JSON only: {{"coherence": N, "usefulness": N, "rationale": "one sentence"}}

Groupings to evaluate:
{suggestions}"""


# ── OpenAI helpers ────────────────────────────────────────────────────────────


def call_model(
    client: OpenAI, model: str, context: str, prompt: str, format_instructions: str
) -> tuple[dict | None, float]:
    messages = []
    if context:
        messages.append({"role": "system", "content": context})
    messages.append({"role": "user", "content": f"{prompt}\n\n{format_instructions}"})

    start = time.time()
    # gpt-5-mini only accepts default params — no temperature, frequency_penalty, presence_penalty
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "max_completion_tokens": 4096,
    }
    if model != "gpt-5-mini":
        kwargs["temperature"] = 0.3
        kwargs["frequency_penalty"] = 0.15
        kwargs["presence_penalty"] = 0
    response = client.chat.completions.create(**kwargs)
    elapsed = time.time() - start

    content = response.choices[0].message.content
    try:
        return json.loads(content), elapsed
    except json.JSONDecodeError:
        return None, elapsed


def judge_score(client: OpenAI, suggestions_str: str) -> tuple[float | None, float | None, str]:
    prompt = JUDGE_PROMPT_TEMPLATE.format(suggestions=suggestions_str)
    try:
        response = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=256,
        )
        data = json.loads(response.choices[0].message.content)
        return data.get("coherence"), data.get("usefulness"), data.get("rationale", "")
    except Exception as e:
        return None, None, str(e)


# ── Eval runners ──────────────────────────────────────────────────────────────


def check(val: bool) -> str:
    return "✓" if val else "✗"


def eval_consolidate(client: OpenAI, models: list[str], use_judge: bool) -> None:
    print("\n## Consolidate Task\n")
    context = build_organize_context()
    seed_categories = {a["category"] for a in SEED_ARTICLES if a.get("category")}

    print(f"Input context:\n```\n{context}\n```\n")
    print(f"Seed categories to cover: {sorted(seed_categories)}\n")

    results = []
    for model in models:
        print(f"  → {model} ... ", end="", flush=True)
        try:
            data, elapsed = call_model(client, model, context, ORGANIZE_PROMPT, ORGANIZE_FORMAT)
        except Exception as e:
            print(f"ERROR: {e}")
            results.append(
                {
                    "model": model,
                    "elapsed": None,
                    "valid": False,
                    "complete": False,
                    "judge_str": "—",
                    "raw": str(e),
                    "rationale": "",
                }
            )
            continue

        valid = data is not None and "mappings" in data
        complete = False
        if valid:
            mapped_old = {m.get("old_category") for m in data["mappings"]}
            complete = seed_categories.issubset(mapped_old)

        coherence = usefulness = rationale = None
        if use_judge and valid:
            desc = data.get("description", "")
            mappings_str = json.dumps(data.get("mappings", []), indent=2)
            coherence, usefulness, rationale = judge_score(client, f"{desc}\n{mappings_str}")

        if coherence is not None and usefulness is not None:
            judge_str = f"{(coherence + usefulness) / 2:.1f} / 5"
        else:
            judge_str = "—"

        print(f"{elapsed:.1f}s  valid={check(valid)}  complete={check(complete)}  judge={judge_str}")
        results.append(
            {
                "model": model,
                "elapsed": elapsed,
                "valid": valid,
                "complete": complete,
                "judge_str": judge_str,
                "raw": data,
                "rationale": rationale or "",
            }
        )

    _print_table(results)
    _print_raw(results)


def eval_split(client: OpenAI, models: list[str], use_judge: bool) -> None:
    category = "Artificial Intelligence"
    print(f"\n## Split Task ({category})\n")
    context, article_ids = build_split_context(category)
    article_id_set = set(article_ids)

    print(f"Articles in category: {len(article_ids)}\n")
    print(f"Context preview:\n```\n{context[:600]}{'...' if len(context) > 600 else ''}\n```\n")

    results = []
    for model in models:
        print(f"  → {model} ... ", end="", flush=True)
        try:
            data, elapsed = call_model(client, model, context, SPLIT_PROMPT, SPLIT_FORMAT)
        except Exception as e:
            print(f"ERROR: {e}")
            results.append(
                {
                    "model": model,
                    "elapsed": None,
                    "valid": False,
                    "complete": False,
                    "judge_str": "—",
                    "raw": str(e),
                    "rationale": "",
                }
            )
            continue

        valid = data is not None and "assignments" in data
        complete = False
        if valid:
            assigned_ids = {a.get("article_id") for a in data["assignments"]}
            complete = article_id_set.issubset(assigned_ids)

        coherence = usefulness = rationale = None
        if use_judge and valid:
            groups: dict = {}
            for a in data.get("assignments", []):
                g = a.get("new_category", "Unknown")
                groups[g] = groups.get(g, 0) + 1
            desc = data.get("description", "")
            groups_str = json.dumps(groups, indent=2)
            coherence, usefulness, rationale = judge_score(client, f"{desc}\n\nGroup sizes:\n{groups_str}")

        if coherence is not None and usefulness is not None:
            judge_str = f"{(coherence + usefulness) / 2:.1f} / 5"
        else:
            judge_str = "—"

        print(f"{elapsed:.1f}s  valid={check(valid)}  complete={check(complete)}  judge={judge_str}")
        results.append(
            {
                "model": model,
                "elapsed": elapsed,
                "valid": valid,
                "complete": complete,
                "judge_str": judge_str,
                "raw": data,
                "rationale": rationale or "",
            }
        )

    _print_table(results)
    _print_raw(results)


def _print_table(results: list[dict]) -> None:
    print("\n| Model          | Time (s) | Valid JSON | Complete | Judge score |")
    print("|----------------|----------|------------|----------|-------------|")
    for r in results:
        t = f"{r['elapsed']:.1f}" if r["elapsed"] is not None else "err"
        print(
            f"| {r['model']:<14} | {t:>8} | {check(r['valid']):^10} | "
            f"{check(r['complete']):^8} | {r['judge_str']:^11} |"
        )


def _print_raw(results: list[dict]) -> None:
    print("\n### Raw outputs\n")
    for r in results:
        print(f"#### {r['model']}")
        if r.get("rationale"):
            print(f"> Judge rationale: {r['rationale']}\n")
        raw = r["raw"]
        if isinstance(raw, dict):
            print(f"```json\n{json.dumps(raw, indent=2)}\n```\n")
        else:
            print(f"```\n{raw}\n```\n")


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate OpenAI models on taxonomy tasks")
    parser.add_argument("--models", nargs="+", default=MODELS, metavar="MODEL", help="Models to test (default: all 5)")
    parser.add_argument("--no-judge", action="store_true", help="Skip LLM-as-judge scoring (faster)")
    parser.add_argument(
        "--task",
        choices=["consolidate", "split", "both"],
        default="both",
        help="Which task to evaluate (default: both)",
    )
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        sys.exit("ERROR: No OpenAI API key found. Set AI_API_OPENAI in aiapi/.env")

    client = OpenAI(api_key=OPENAI_API_KEY)
    use_judge = not args.no_judge

    print(f"# Taxonomy Model Eval — {time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Models : {', '.join(args.models)}")
    print(f"Judge  : {JUDGE_MODEL if use_judge else 'disabled'}")
    print(f"Task   : {args.task}")

    if args.task in ("consolidate", "both"):
        eval_consolidate(client, args.models, use_judge)

    if args.task in ("split", "both"):
        eval_split(client, args.models, use_judge)


if __name__ == "__main__":
    main()
