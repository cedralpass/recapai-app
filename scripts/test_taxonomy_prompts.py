#!/usr/bin/env python3
"""
test_taxonomy_prompts.py — Experiment harness for taxonomy optimization.

Runs multiple prompt strategies against live user data and prints the proposed
taxonomy for each, without applying any changes to the database.

Usage (from project root):
    # Consolidation variants for testuser2
    .venv/bin/python scripts/test_taxonomy_prompts.py

    # Specific variant only
    .venv/bin/python scripts/test_taxonomy_prompts.py --variant names-subcats

    # Phase 2 split for large categories (threshold 15)
    .venv/bin/python scripts/test_taxonomy_prompts.py --split --threshold 15

    # Different user
    .venv/bin/python scripts/test_taxonomy_prompts.py --username testuser

Consolidation variants:
    names-only     Category names only (matches current organize_taxonomy)
    names-subcats  Category names + aggregated sub-categories per category (recommended)
    names-titles   Category names + article titles per category
"""

import sys
import os
import json
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# --- Prompt constants (mirroring the web routes) ----------------------------

CONSOLIDATION_PROMPT = (
    "Can you recommend a consolidated category list? "
    "Merge similar or related categories, especially small ones with 1-3 articles. "
    "Keep Artificial Intelligence and Software Architecture as separate categories. "
    "Keep category names concise and understandable to a human reader."
)
CONSOLIDATION_FORMAT = (
    'Respond with JSON in this exact structure:\n'
    '{\n'
    '  "description": "A summary of the changes.",\n'
    '  "mappings": [\n'
    '    {"new_category": "new_name", "old_category": "old_name"}\n'
    '  ],\n'
    '  "ref_key": "2"\n'
    '}'
)

SPLIT_PROMPT = (
    "Split these articles into 2-4 distinct, meaningful groups based on their themes. "
    "Name each group clearly (2-4 words). "
    "Assign every article to exactly one group."
)
SPLIT_FORMAT = (
    'Respond with JSON in this exact structure:\n'
    '{\n'
    '  "description": "Brief rationale for the groupings",\n'
    '  "assignments": [\n'
    '    {"article_id": 42, "new_category": "Group Name"},\n'
    '    {"article_id": 43, "new_category": "Group Name"}\n'
    '  ]\n'
    '}'
)


# --- Context builders -------------------------------------------------------

def build_names_only_context(categories):
    """Current organize_taxonomy approach: just category names."""
    names = sorted(cat for cat, _count in categories)
    return f"I am using this taxonomy to categorize content: {', '.join(names)}."


def build_names_subcats_context(cats_with_subcats):
    """Richer context: counts + aggregated sub-categories per category."""
    lines = ["I am using this taxonomy to categorize content:"]
    for cat, count, subcats in cats_with_subcats:
        article_word = "article" if count == 1 else "articles"
        if subcats:
            subcats_str = ", ".join(subcats[:8])
            lines.append(f"- {cat} ({count} {article_word}): {subcats_str}")
        else:
            lines.append(f"- {cat} ({count} {article_word})")
    return "\n".join(lines)


def build_names_titles_context(cats_with_articles):
    """
    Context with actual article titles per category.
    cats_with_articles: [(cat, count, [title, ...]), ...]
    Shows up to 5 titles per category to keep token count manageable.
    """
    lines = ["I am using this taxonomy to categorize content:"]
    for cat, count, titles in cats_with_articles:
        article_word = "article" if count == 1 else "articles"
        if titles:
            sample = titles[:5]
            remaining = count - len(sample)
            lines.append(f"- {cat} ({count} {article_word}):")
            for t in sample:
                lines.append(f"    • {t}")
            if remaining > 0:
                lines.append(f"    ... and {remaining} more")
        else:
            lines.append(f"- {cat} ({count} {article_word})")
    return "\n".join(lines)


def build_split_context(category_name, articles):
    """Context for splitting a single category. articles: [(id, title, sub_categories_json)]"""
    lines = [
        f'Category "{category_name}" has grown large and needs splitting into smaller groups.',
        "Here are the articles with their content themes:",
        "",
    ]
    for article_id, title, subcats_json in articles:
        subcats = []
        if subcats_json:
            try:
                subcats = json.loads(subcats_json)
            except (json.JSONDecodeError, TypeError):
                pass
        subcats_str = ", ".join(subcats) if subcats else "none"
        lines.append(f"[id:{article_id}] {title or 'Untitled'} | themes: {subcats_str}")
    return "\n".join(lines)


# --- Result display helpers -------------------------------------------------

def print_distribution(categories, label="Current"):
    total = sum(c for _, c in categories)
    print(f"\n{'─'*60}")
    print(f"  {label} distribution ({len(categories)} categories, {total} articles)")
    print(f"{'─'*60}")
    small = sum(1 for _, c in categories if c <= 3)
    medium = sum(1 for _, c in categories if 3 < c < 15)
    large = sum(1 for _, c in categories if c >= 15)
    print(f"  Small (1-3):  {small} categories")
    print(f"  Medium (4-14): {medium} categories")
    print(f"  Large (15+):  {large} categories")
    print()
    for cat, count in categories:
        bar = "█" * min(count, 40)
        print(f"  {cat:<42} {count:>4}  {bar}")


def print_consolidation_result(variant_name, context, result, original_categories):
    if not result or 'mappings' not in result:
        print(f"\n[{variant_name}] AI returned no usable result: {result}")
        return

    mappings = result['mappings']
    description = result.get('description', '')

    # Build new category counts from mappings
    original_counts = {cat: count for cat, count in original_categories}
    new_counts = {}
    for m in mappings:
        old = m.get('old_category', '')
        new = m.get('new_category', '')
        new_counts[new] = new_counts.get(new, 0) + original_counts.get(old, 0)

    # Detect merges (many→one) and renames (one→one)
    new_sources = {}
    for m in mappings:
        old, new = m.get('old_category', ''), m.get('new_category', '')
        new_sources.setdefault(new, []).append(old)
    merges = {new: olds for new, olds in new_sources.items() if len(olds) > 1}
    renames = {new: olds[0] for new, olds in new_sources.items()
               if len(olds) == 1 and olds[0] != new}

    print(f"\n{'='*60}")
    print(f"  VARIANT: {variant_name}")
    print(f"{'='*60}")
    print(f"  AI description: {description}")
    print()
    print(f"  Result: {len(original_categories)} → {len(new_counts)} categories")
    if merges:
        print(f"\n  Merges:")
        for new, olds in sorted(merges.items()):
            olds_str = " + ".join(f"{o}({original_counts.get(o,0)})" for o in olds)
            print(f"    {olds_str} → {new}({new_counts[new]})")
    if renames:
        print(f"\n  Renames:")
        for new, old in sorted(renames.items()):
            print(f"    {old} → {new}")

    print(f"\n  Proposed taxonomy:")
    for cat, count in sorted(new_counts.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * min(count, 30)
        print(f"    {cat:<40} {count:>4}  {bar}")

    # Show unmapped original categories (AI missed them)
    mapped_olds = {m.get('old_category') for m in mappings}
    unmapped = set(original_counts.keys()) - mapped_olds
    if unmapped:
        print(f"\n  ⚠  Not covered by mappings (AI omitted): {', '.join(sorted(unmapped))}")


def print_split_result(category_name, original_count, result):
    if not result or 'assignments' not in result:
        print(f"\n  [{category_name}] AI returned no usable result: {result}")
        return

    description = result.get('description', '')
    assignments = result['assignments']

    # Count articles per new sub-category
    sub_counts = {}
    for a in assignments:
        new_cat = a.get('new_category', 'Unknown')
        sub_counts[new_cat] = sub_counts.get(new_cat, 0) + 1

    unassigned = original_count - len(assignments)

    print(f"\n  Category: {category_name} ({original_count} articles)")
    print(f"  Rationale: {description}")
    print(f"  Split into {len(sub_counts)} groups:")
    for sub_cat, count in sorted(sub_counts.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * min(count, 30)
        print(f"    {sub_cat:<40} {count:>4}  {bar}")
    if unassigned > 0:
        print(f"  ⚠  {unassigned} articles not assigned by AI")


# --- Main -------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--username", default="testuser2",
                   help="User to analyze (default: testuser2)")
    p.add_argument("--variant", choices=["names-only", "names-subcats", "names-titles"],
                   default=None,
                   help="Run a single consolidation variant (default: all three)")
    p.add_argument("--split", action="store_true",
                   help="Run Phase 2 split prompts for large categories")
    p.add_argument("--threshold", type=int, default=15,
                   help="Min articles to consider for splitting (default: 15)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print contexts without calling the AI API")
    return p.parse_args()


def main():
    args = parse_args()

    from recap import create_app, db
    import sqlalchemy as sa
    from recap.models import User, Article
    from recap.aiapi_helper import AiApiHelper

    app = create_app()

    with app.app_context():
        user = db.session.scalar(sa.select(User).where(User.username == args.username))
        if user is None:
            print(f"Error: user '{args.username}' not found.")
            sys.exit(1)

        # ── Current distribution ──────────────────────────────────────────
        categories = db.session.execute(
            sa.select(Article.category, sa.func.count(Article.id).label('count'))
            .where(Article.user_id == user.id)
            .where(Article.classified.isnot(None))
            .group_by(Article.category)
            .order_by(sa.desc('count'))
        ).all()

        print_distribution(categories, label=f"Current ({args.username})")

        # ── Aggregated sub-categories per category (for variants 2 & 3) ──
        article_rows = db.session.execute(
            sa.select(Article.category, Article.sub_categories, Article.title)
            .where(Article.user_id == user.id)
            .where(Article.classified.isnot(None))
        ).all()

        cats_data = {}
        for cat, subcats_json, title in article_rows:
            if cat is None:
                continue
            if cat not in cats_data:
                cats_data[cat] = {'count': 0, 'subcats': set(), 'titles': []}
            cats_data[cat]['count'] += 1
            if subcats_json:
                try:
                    cats_data[cat]['subcats'].update(json.loads(subcats_json))
                except (json.JSONDecodeError, TypeError):
                    pass
            if title:
                cats_data[cat]['titles'].append(title)

        cats_with_subcats = [
            (cat, d['count'], sorted(d['subcats']))
            for cat, d in sorted(cats_data.items(), key=lambda x: x[1]['count'], reverse=True)
        ]
        cats_with_titles = [
            (cat, d['count'], d['titles'])
            for cat, d in sorted(cats_data.items(), key=lambda x: x[1]['count'], reverse=True)
        ]

        # ── Consolidation variants ────────────────────────────────────────
        run_variants = (
            [args.variant] if args.variant
            else ["names-only", "names-subcats", "names-titles"]
        )

        variant_contexts = {
            "names-only": build_names_only_context(categories),
            "names-subcats": build_names_subcats_context(cats_with_subcats),
            "names-titles": build_names_titles_context(cats_with_titles),
        }

        for variant in run_variants:
            context = variant_contexts[variant]
            if args.dry_run:
                print(f"\n{'='*60}")
                print(f"  VARIANT: {variant} (dry run — context only)")
                print(f"{'='*60}")
                print(context)
            else:
                print(f"\nCalling AI for variant '{variant}'...", flush=True)
                result = AiApiHelper.PerformTask(context, CONSOLIDATION_PROMPT, CONSOLIDATION_FORMAT, user.id)
                print_consolidation_result(variant, context, result, categories)

        # ── Phase 2: split large categories ──────────────────────────────
        if args.split:
            large = [(cat, count) for cat, count in categories if count >= args.threshold]
            if not large:
                print(f"\nNo categories exceed {args.threshold} articles — nothing to split.")
            else:
                print(f"\n{'='*60}")
                print(f"  PHASE 2: Split categories with {args.threshold}+ articles")
                print(f"{'='*60}")
                for category_name, count in large:
                    article_split_rows = db.session.execute(
                        sa.select(Article.id, Article.title, Article.sub_categories)
                        .where(Article.user_id == user.id)
                        .where(Article.category == category_name)
                        .order_by(Article.id)
                    ).all()

                    context = build_split_context(category_name, article_split_rows)
                    if args.dry_run:
                        print(f"\n  [{category_name}] context ({len(article_split_rows)} articles):")
                        print(context[:500] + ("..." if len(context) > 500 else ""))
                    else:
                        print(f"\n  Splitting '{category_name}' ({count} articles)...", flush=True)
                        result = AiApiHelper.PerformTask(context, SPLIT_PROMPT, SPLIT_FORMAT, user.id)
                        print_split_result(category_name, count, result)

        print()


if __name__ == "__main__":
    main()
