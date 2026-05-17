# Taxonomy Model Evaluation — Design Doc

## Goal

Make a data-driven decision on which OpenAI model to use for the two taxonomy
AI tasks (consolidate and split). Current model: `gpt-4.1-mini`. Candidates
under consideration: `gpt-5-mini` ($0.25/1M tokens), `gpt-5.4-mini` ($0.75),
`gpt-5.4-nano` ($0.20).

## Background

Two AI tasks use the model configured in `AI_OPEN_AI_MODEL` (aiapi `.env` and
Render env var):

| Task | Function | Prompt input |
|------|----------|--------------|
| Consolidate | `organize_taxonomy_task` | Category list with article counts + sub-categories |
| Split | `suggest_splits_task` | Per-article: title, sub-category themes, summary (truncated 200 chars) |

The split prompt was recently improved to include article summaries, which
significantly increased semantic richness. The split prompt also caps groups at
2–4 which may be too few for very large categories (e.g. 57-article AI bucket)
— this is a known open issue.

User taxonomy preferences (free-text field saved in `User.taxonomy_preferences`)
are appended to both prompts when set.

## Eval Script

Build `scripts/eval_taxonomy_models.py`. It should be runnable standalone
against a local or remote aiapi instance.

### What to measure

| Metric | How |
|--------|-----|
| **Response time** | Wall-clock time per API call |
| **JSON validity** | Does the response parse and contain the required keys (`mappings` / `assignments`)? |
| **Completeness** | Consolidate: every seed category has a mapping. Split: every article_id has an assignment |
| **Group quality** | LLM-as-judge: pass the suggested groupings to a judge model (gpt-4o or gpt-5), ask it to score coherence and meaningfulness 1–5 |

### Data source

Use the seed data in `tests/seed_data.py` — 53 real classified articles across
10 categories. Import `SEED_ARTICLES` and build context using the same helpers
the tasks use:

```python
from recap.taxonomy_helpers import build_rich_organize_context, build_split_context
```

For the split eval, target the largest seed category: `Artificial Intelligence`
(27 articles in seed data; 57 in prod).

### Models to compare

```python
MODELS = [
    "gpt-4o",        # baseline
    "gpt-4.1-mini",  # current default
    "gpt-5-mini",    # $0.25 — main candidate
    "gpt-5.4-mini",  # $0.75
    "gpt-5.4-nano",  # $0.20 — cheapest
]
```

### Output format

Print a Markdown table per task (consolidate, split):

```
| Model          | Time (s) | Valid JSON | Complete | Judge score |
|----------------|----------|------------|----------|-------------|
| gpt-4o         | 4.2      | ✓          | ✓        | 3.8 / 5     |
| gpt-4.1-mini   | 2.1      | ✓          | ✓        | 4.0 / 5     |
| gpt-5-mini     | 1.8      | ✓          | ✓        | 4.4 / 5     |
| gpt-5.4-nano   | 0.9      | ✓          | ✗        | 2.1 / 5     |
```

Also print the raw AI output for each model so you can eyeball the groupings.

### LLM-as-judge prompt (sketch)

```
You are evaluating AI-generated taxonomy suggestions for a reading list app.
Score the following category groupings on two dimensions (1–5 each):
- Coherence: are articles in each group genuinely similar in topic?
- Usefulness: would a human reader find these group names clear and helpful?

Return JSON: {"coherence": N, "usefulness": N, "rationale": "..."}

Groupings to evaluate:
{suggestions}
```

Use the highest-quality available model as judge (e.g. gpt-4o or gpt-5).

## How to run

```bash
# Requires aiapi to be running locally on port 8082
.venv/bin/python scripts/eval_taxonomy_models.py

# Run against a specific model only
.venv/bin/python scripts/eval_taxonomy_models.py --models gpt-5-mini gpt-5.4-nano

# Skip the judge scoring (faster)
.venv/bin/python scripts/eval_taxonomy_models.py --no-judge
```

## Open questions / follow-on work

- **Split group cap**: The split prompt says "2–4 distinct groups". For a
  57-article category this yields 14–28 articles per group. Consider making
  the cap proportional: `max(2, count // 12)` groups as a minimum target. This
  is separate from the model choice but worth doing in the same session.

- **Per-task model config**: Could split consolidate and split onto different
  models (e.g. nano for classify, mini for taxonomy) by adding
  `AI_OPEN_AI_TAXONOMY_MODEL` env var. Only worth it if eval shows a meaningful
  quality gap between models on the two task types.

- **Classification model**: `classify_url` (per-article, most frequent call)
  also uses `AI_OPEN_AI_MODEL`. Nano may be good enough here since it's a
  simpler extraction task. Eval should include a classify prompt test if
  possible.
