#!/usr/bin/env python3
"""
Eval for the classify prompt's category selection behaviour.

Tests how well the model reuses existing categories vs. creates new ones,
using a fixed set of user categories (mirroring a real account) and a
set of probe articles covering clear-match, borderline, and no-match cases.

Usage:
    .venv/bin/python scripts/eval_classify_categories.py

    # Show the full prompt sent to OpenAI for each case
    .venv/bin/python scripts/eval_classify_categories.py --show-prompt

    # Run N times per case to check consistency
    .venv/bin/python scripts/eval_classify_categories.py --runs 3
"""

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402

load_dotenv(PROJECT_ROOT / "aiapi" / ".env")
load_dotenv(PROJECT_ROOT / "recap" / ".env", override=False)

# ── Config ─────────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.environ.get("AI_API_OPENAI") or os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("AI_OPEN_AI_MODEL", "gpt-4.1-mini")

# Real user taxonomy (18 categories from a live account)
USER_CATEGORIES = [
    "Language Models & NLP",
    "AI Infrastructure & Deployment",
    "Web Development & Architecture",
    "Career Development",
    "AI in Enterprise Solutions",
    "Organizational Behavior & Communication",
    "AI Data & Security",
    "Product Management & Strategy",
    "Outdoor Activities & Sports Science",
    "Data & System Architecture",
    "Startup & Growth Strategies",
    "Customer Experience & Engagement",
    "Emerging Trends and Research",
    "Team Dynamics & Management",
    "Engineering & Productivity",
    "Cooking & Consumer Products",
    "AI in Creative Applications",
    "Neuroscience",
]

# ── Probe articles ──────────────────────────────────────────────────────────
# Each case has:
#   url      - the article URL
#   content  - short representative excerpt (or None to test URL-only path)
#   note     - what we expect / what we're watching for
#   bad      - categories the model should NOT pick (the bad-fit case)

PROBE_CASES = [
    {
        "label": "Camera review (the bad case)",
        "url": "https://www.rtings.com/camera/reviews/best/by-type/mirrorless-beginners",
        "content": (
            "We tested dozens of mirrorless cameras to find the best options for beginners. "
            "The Sony ZV-E10 II topped our list for its autofocus performance, compact body, "
            "and beginner-friendly controls. We evaluated sensor size, image stabilisation, "
            "battery life, and value for money. Canon, Fujifilm, and Nikon also featured "
            "strongly. This guide helps first-time buyers choose the right camera body and kit lens."
        ),
        "note": "Should create a new category (e.g. Consumer Electronics, Photography) — none of the 18 categories cover consumer hardware reviews",
        "bad": [
            "Customer Experience & Engagement",
            "Cooking & Consumer Products",
            "Product Management & Strategy",
            "Emerging Trends and Research",
            "Organizational Behavior & Communication",
        ],
    },
    {
        "label": "LLM fine-tuning post (clear match)",
        "url": "https://huggingface.co/blog/rlhf",
        "content": (
            "Reinforcement Learning from Human Feedback (RLHF) is a technique used to train "
            "large language models to follow instructions. We describe how to fine-tune a "
            "pretrained model using a reward model trained on human preference data, then "
            "apply PPO to optimise the policy. Results show significant improvement in "
            "helpfulness and harmlessness scores compared to supervised fine-tuning alone."
        ),
        "note": "Should match Language Models & NLP",
        "bad": [],
    },
    {
        "label": "Trail running nutrition (borderline)",
        "url": "https://www.runnersworld.com/nutrition/a43210876/trail-running-fueling-guide/",
        "content": (
            "Fuelling for trail running differs significantly from road running. Elevation gain, "
            "technical terrain, and longer durations demand a different carbohydrate strategy. "
            "We cover pre-race carb-loading, mid-run gels vs real food, electrolyte balance, "
            "and post-run recovery nutrition. Interviews with elite mountain runners and sports "
            "dietitians inform our recommendations."
        ),
        "note": "Borderline: Outdoor Activities & Sports Science vs new category like Health & Nutrition",
        "bad": [],
    },
    {
        "label": "Sourdough recipe (clear match)",
        "url": "https://www.seriouseats.com/sourdough-bread-recipe",
        "content": (
            "A step-by-step guide to baking sourdough bread at home. We cover starter maintenance, "
            "autolyse, bulk fermentation timing, shaping, and baking in a Dutch oven. "
            "Includes troubleshooting for common problems like dense crumb, gummy interior, "
            "and over-proofing. Recipe yields one 900g loaf."
        ),
        "note": "Should match Cooking & Consumer Products (or create a Cooking subcategory)",
        "bad": [],
    },
    {
        "label": "Quantum computing explainer (no match — new category needed)",
        "url": "https://quantamagazine.org/what-is-quantum-computing-20230101/",
        "content": (
            "Quantum computers exploit superposition and entanglement to perform certain "
            "computations exponentially faster than classical machines. This explainer covers "
            "qubits, quantum gates, decoherence, and current hardware approaches from IBM, "
            "Google, and IonQ. We also discuss which problem classes — optimisation, simulation, "
            "cryptography — will benefit most and realistic timelines to quantum advantage."
        ),
        "note": "Should create a new category (e.g. Quantum Computing, Emerging Technology) — none of the 18 fit well",
        "bad": ["Emerging Trends and Research"],  # too vague — model should be more specific
    },
]

# ── Prompt builder (mirrors aiapi/classify.py) ──────────────────────────────


def _category_instruction(categories):
    if categories:
        cat_str = ", ".join(categories)
        return (
            "First, identify the primary domain of the article (e.g. consumer electronics, nutrition, software engineering). "
            f"Then check whether any of these existing categories genuinely covers that domain: {cat_str}. "
            "Reuse an existing category only if the match is clear and direct. "
            "If no existing category fits without stretching its meaning, invent a concise new one (2–4 words)."
        )
    return "Choose the most appropriate category for this content. Create a specific, descriptive category name."


def build_prompt(url, content=None, categories=None):
    instruction = _category_instruction(categories)
    if content:
        system = (
            "You are given the URL and the full article text below. Classify the article based only on the provided text. "
            f"{instruction} "
            "Base your summary, key_topics, sub_categories, author, and title only on the provided text; do not invent information. "
            "Respond with: category, url of blog, blog title, author, a short summary, "
            "three key topics as bullet points, and three sub categories as bullet points. "
            "Respond in a structured JSON with keys: author, blog_title, category, summary, key_topics, sub_categories, url."
        )
        user = f"Classify the following article. URL: {url}\n\nArticle text:\n\n{content}"
    else:
        system = (
            "You are given ONLY the URL of a blog post; the article text is not provided. "
            f"{instruction} "
            "Do NOT invent or assume acronym meanings, author, title, or details. "
            "If you cannot infer something from the URL alone, use 'Unknown' for fields you cannot determine. "
            "Respond in a structured JSON with keys: author, blog_title, category, summary, key_topics, sub_categories, url."
        )
        user = "please classify this blog post: " + str(url)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ── Runner ──────────────────────────────────────────────────────────────────


def run_case(client, case, categories, show_prompt, runs):
    results = []
    messages = build_prompt(case["url"], content=case.get("content"), categories=categories)

    if show_prompt:
        print("\n  SYSTEM PROMPT:")
        print("  " + messages[0]["content"])

    for i in range(runs):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.25,
            max_tokens=512,
            frequency_penalty=0.15,
            presence_penalty=0,
        )
        raw = resp.choices[0].message.content
        try:
            data = json.loads(raw)
            category = data.get("category", "MISSING")
        except json.JSONDecodeError:
            category = f"JSON ERROR: {raw[:80]}"
        results.append(category)

    return results


def verdict(category, bad_categories, user_categories):
    is_new = category not in user_categories
    is_bad = category in bad_categories
    if is_bad:
        return "FAIL (bad fit)", "✗"
    if is_new:
        return "NEW category", "+"
    return "REUSED", "="


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-prompt", action="store_true", help="Print the full system prompt for each case")
    parser.add_argument("--runs", type=int, default=1, help="Number of times to run each case (for consistency check)")
    parser.add_argument(
        "--no-categories", action="store_true", help="Run without passing categories (baseline comparison)"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="Only send the top N categories by article count (default: all)",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Run multiple top-N values side by side: 0 (none), 6, 8, 10, 12, all",
    )
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        print("Error: AI_API_OPENAI or OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    client = OpenAI(api_key=OPENAI_API_KEY)

    if args.sweep:
        # USER_CATEGORIES is already ordered by article count (desc) per the DB query
        sweep_sizes = [0, 6, 8, 10, 12, len(USER_CATEGORIES)]
        run_sweep(client, sweep_sizes, args.runs)
    else:
        if args.no_categories:
            categories = []
        elif args.top is not None:
            categories = USER_CATEGORIES[: args.top]
        else:
            categories = USER_CATEGORIES
        run_single(client, categories, args.runs, args.show_prompt)


def run_single(client, categories, runs, show_prompt):
    mode = f"{len(categories)} categories" if categories else "NO CATEGORIES (baseline)"
    print(f"\n{'=' * 72}")
    print(f"  Classify eval  |  model: {MODEL}  |  mode: {mode}  |  runs: {runs}")
    print(f"{'=' * 72}")

    failures = 0
    for case in PROBE_CASES:
        print(f"\n  {case['label']}")
        print(f"  note: {case['note']}")
        if show_prompt:
            messages = build_prompt(case["url"], content=case.get("content"), categories=categories)
            print(f"\n  SYSTEM: {messages[0]['content']}\n")
        results = run_case(client, case, categories, show_prompt=False, runs=runs)
        for run_idx, category in enumerate(results):
            label, sym = verdict(category, case["bad"], USER_CATEGORIES)
            run_tag = f" (run {run_idx + 1})" if runs > 1 else ""
            print(f"  {sym}  [{label}]{run_tag}: {category}")
            if sym == "✗":
                failures += 1

    print(f"\n{'=' * 72}")
    if failures:
        print(f"  {failures} FAILURE(s) — bad-fit categories were selected.")
    else:
        print("  All cases passed.")
    print(f"{'=' * 72}\n")


def run_sweep(client, sweep_sizes, runs):
    col = 26  # width per category-count column

    print(f"\n{'=' * 72}")
    print(f"  Sweep: top-N categories  |  model: {MODEL}  |  runs per cell: {runs}")
    print(f"{'=' * 72}")

    # Header row
    header = f"  {'CASE':<32}"
    for n in sweep_sizes:
        tag = "none" if n == 0 else ("all" if n == len(USER_CATEGORIES) else f"top {n}")
        header += f"  {tag:<{col}}"
    print(header)
    print(f"  {'-' * 32}" + (f"  {'-' * col}" * len(sweep_sizes)))

    # Run all cases × all sizes
    all_results = {}  # (case_idx, size) -> list of category strings
    for size in sweep_sizes:
        categories = USER_CATEGORIES[:size] if size > 0 else []
        for ci, case in enumerate(PROBE_CASES):
            results = run_case(client, case, categories, show_prompt=False, runs=runs)
            all_results[(ci, size)] = results

    # Print results
    total_failures = {n: 0 for n in sweep_sizes}
    for ci, case in enumerate(PROBE_CASES):
        # Truncate label for table width
        short_label = case["label"][:32]
        row = f"  {short_label:<32}"
        for n in sweep_sizes:
            results = all_results[(ci, n)]
            cell_parts = []
            for category in results:
                label, sym = verdict(category, case["bad"], USER_CATEGORIES)
                if sym == "✗":
                    total_failures[n] += 1
                cell_parts.append(f"{sym} {category[:col - 3]}")
            row += "  " + " / ".join(cell_parts).ljust(col)
        print(row)

    # Summary row
    print(f"\n  {'FAILURES':<32}", end="")
    for n in sweep_sizes:
        f_str = str(total_failures[n]) if total_failures[n] else "0"
        print(f"  {f_str:<{col}}", end="")
    print(f"\n{'=' * 72}\n")


if __name__ == "__main__":
    main()
