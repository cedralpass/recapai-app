# Taxonomy Organization: How It Works

RecapAI has two AI-assisted methods for managing the article taxonomy. They are complementary — Consolidate runs first to clean up a messy taxonomy, Split runs later when individual categories have grown too large.

---

## Overview

| | Consolidate | Split |
|---|---|---|
| **Route** | `GET /organize_taxonomy` | `GET /user/<username>/suggest_splits` |
| **UI entry** | Profile page → "Consolidate" button | Profile page → "Split" button |
| **What it does** | Merges similar/overlapping categories | Breaks one large category into sub-groups |
| **Unit of work** | Category-level (renames categories) | Article-level (reassigns each article) |
| **AI sees** | All categories + counts + sub-category themes | All articles in one large category + their themes |
| **AI returns** | `mappings[]` — old→new category name pairs | `assignments[]` — article_id→new_category pairs |
| **Apply route** | `POST /apply_taxonomy` | `POST /apply_splits` |
| **Selective apply** | Yes — accept/reject per suggestion | Yes — accept/reject per category split |

---

## Method 1: Consolidate

### When to use

Use this when the taxonomy has grown fragmented — many small categories (1–5 articles) with overlapping names, or near-duplicates like "Cooking" and "Culinary Arts" that should be one category.

### Route flow (`recap/profile/__init__.py`)

1. `GET /organize_taxonomy` triggers `build_rich_organize_context(user_id)` — queries all classified articles and builds a category list enriched with article counts and aggregated sub-categories (capped at 4 per category to control token length).
2. Calls `AiApiHelper.PerformTask(context, PROMPT, FORMAT, user_id)` which POSTs to the `aiapi` service at `/process_task`.
3. The aiapi service calls `build_prompt(context, PROMPT, FORMAT)` to assemble the OpenAI messages array, then calls `openai.chat.completions.create(...)`.
4. Response is parsed into per-suggestion groups. Each suggestion covers one or more old categories merging into one new category.
5. `session['category_mapping']` and `session['suggestion_mappings']` are set for the apply step.
6. Renders `organize_taxonomy.html` with a two-column diff (Current | Proposed) and per-suggestion Accept/Reject.

### Example prompt sent to OpenAI

**System message** (built by `build_rich_organize_context`):
```
I am using this taxonomy to categorize content:
- Artificial Intelligence (27 articles): Deep Learning, Fine-tuning, LLM, RAG
- Software Development (18 articles): APIs, Architecture, CI/CD, Python
- Health & Wellness (6 articles): Fitness, Mental Health, Nutrition, Sleep
- Leadership (4 articles): Management, Remote Work, Teams
- Cooking (2 articles): Recipes, Techniques
- Culinary Arts (1 article): Plating, Techniques
- Fitness & Health (1 article): Running
```

**User message** (PROMPT + `\n\n` + FORMAT, assembled in `task_processor.build_prompt`):
```
Can you recommend a consolidated category list? Merge similar or related categories,
especially small ones with 1-3 articles. Keep category names concise and understandable
to a human reader.

Respond with JSON in this exact structure:
{
  "description": "A concise summary of the changes made.",
  "mappings": [
    {"new_category": "New Name", "old_category": "Old Name"},
    {"new_category": "New Name", "old_category": "Old Name"}
  ]
}
```

### Example AI response

```json
{
  "description": "Merged Cooking and Culinary Arts into one category. Combined Health & Wellness and Fitness & Health. All other categories unchanged.",
  "mappings": [
    {"new_category": "Artificial Intelligence", "old_category": "Artificial Intelligence"},
    {"new_category": "Software Development",    "old_category": "Software Development"},
    {"new_category": "Health & Wellness",        "old_category": "Health & Wellness"},
    {"new_category": "Health & Wellness",        "old_category": "Fitness & Health"},
    {"new_category": "Leadership",               "old_category": "Leadership"},
    {"new_category": "Cooking",                  "old_category": "Cooking"},
    {"new_category": "Cooking",                  "old_category": "Culinary Arts"}
  ]
}
```

Unchanged categories (old == new) are included in the mappings array but filtered out of the suggestion list in the route — only actual changes are shown to the user.

### Apply logic

`POST /apply_taxonomy` reads `session['suggestion_mappings']` and only applies the suggestions where `accepted_<id>=1` was submitted. For each accepted suggestion, every article in the old category is rewritten to the new category name.

---

## Method 2: Split

### When to use

Use this when a category has grown large (default threshold: 12 articles) and has become a catch-all. The goal is to break it into 2–4 focused sub-categories based on what the articles are actually about.

### Route flow (`recap/profile/__init__.py`)

1. `GET /user/<username>/suggest_splits?threshold=12` finds all categories at or above the threshold.
2. For each large category, `build_split_context(category_name, articles)` queries every article in that category (id, title, sub_categories) and formats them as a numbered list.
3. Calls `AiApiHelper.PerformTask(context, SPLIT_PROMPT, SPLIT_FORMAT, user_id)` — one API call per large category.
4. Response maps each article ID to a new category name. `session['split_assignments']` stores these as `{ 'split_0': {'101': 'AI Applications', '102': 'Model Training', ...}, ... }`.
5. Renders `suggest_splits.html` with a two-column diff and per-split Accept/Reject.

### Example prompt sent to OpenAI

**System message** (built by `build_split_context`):
```
Category "Artificial Intelligence" has grown large and needs splitting into smaller groups.
Here are the articles with their content themes:

[id:101] How GPT-4 Changes Everything | themes: LLM, Transformers, NLP
[id:102] Fine-tuning LLaMA for Production | themes: Fine-tuning, LLaMA, Training
[id:103] Building a RAG Pipeline | themes: RAG, Vector DB, Retrieval
[id:104] Stable Diffusion in Practice | themes: Image Generation, Diffusion Models
[id:105] OpenAI Function Calling Guide | themes: APIs, Tool Use, LLM
[id:106] LangChain for Beginners | themes: Agents, LLM, Orchestration
[id:107] Prompt Engineering Patterns | themes: Prompting, LLM, GPT
[id:108] Running LLMs Locally with Ollama | themes: Local Models, LLaMA, Inference
[id:109] DALL-E 3 vs Midjourney | themes: Image Generation, Generative AI, Comparison
[id:110] Vector Databases Compared | themes: Vector DB, Embeddings, RAG
...
```

**User message** (SPLIT_PROMPT + `\n\n` + SPLIT_FORMAT):
```
Split these articles into 2-4 distinct, meaningful groups based on their themes.
Name each group clearly (2-4 words). Assign every article to exactly one group.

Respond with JSON in this exact structure:
{
  "description": "Brief rationale for the groupings",
  "assignments": [
    {"article_id": 42, "new_category": "Group Name"},
    {"article_id": 43, "new_category": "Group Name"}
  ]
}
```

### Example AI response

```json
{
  "description": "Split into three groups: articles about building with LLMs (APIs, RAG, agents), articles about model training and fine-tuning, and articles about image generation.",
  "assignments": [
    {"article_id": 101, "new_category": "Large Language Models"},
    {"article_id": 102, "new_category": "AI Model Training"},
    {"article_id": 103, "new_category": "Large Language Models"},
    {"article_id": 104, "new_category": "AI Image Generation"},
    {"article_id": 105, "new_category": "Large Language Models"},
    {"article_id": 106, "new_category": "Large Language Models"},
    {"article_id": 107, "new_category": "Large Language Models"},
    {"article_id": 108, "new_category": "AI Model Training"},
    {"article_id": 109, "new_category": "AI Image Generation"},
    {"article_id": 110, "new_category": "Large Language Models"}
  ]
}
```

### Apply logic

`POST /apply_splits` reads `session['split_assignments']` and applies only the accepted splits (`accepted_split_N=1`). For each accepted split, each article ID in the assignments dict is looked up by primary key and its `category` field is updated. Ownership is verified before writing.

---

## OpenAI Call Parameters

Both methods share the same underlying `task_processor.py` call in the `aiapi` service.

```python
client.chat.completions.create(
    model=AIAPIConfig.AI_OPEN_AI_MODEL,   # set via AI_OPEN_AI_MODEL env var (e.g. gpt-4o)
    messages=prompt_array,
    response_format={"type": "json_object"},
    temperature=0.3,          # low — favors deterministic, factual output
    max_tokens=4096,          # raised from 512 to prevent truncation on large responses
    frequency_penalty=0.15,   # mild penalty to reduce repetitive category names
    presence_penalty=0
)
```

The `httpx` timeout on the `recap`→`aiapi` call is **180 seconds** (`recap/aiapi_helper.py`). The aiapi service itself has no request timeout — it blocks until OpenAI responds.

---

## Prompt Assembly (`task_processor.build_prompt`)

The messages array sent to OpenAI is built in this order:

```
1. {"role": "system",    "content": <context string>}
2. {"role": "user",      "content": "<prompt>\n\n<format instructions>"}
   (format instructions are appended to the user turn, not a separate system message)
3. [optional] {"role": "user",      "content": <history prompt>}
   [optional] {"role": "assistant", "content": <history response>}
   (repeated for each prior exchange if prompt_history is passed)
```

The taxonomy routes do not use `prompt_history` — each call is stateless.

---

## Performance Notes

| Scenario | Typical latency | Token budget |
|---|---|---|
| Consolidate, 10–15 categories | 8–15 s | ~300 context tokens, ~200 response tokens |
| Consolidate, 25–35 categories | 30–90 s | ~700 context tokens, ~500 response tokens |
| Split, 30 articles | 10–20 s | ~600 context tokens, ~300 response tokens |
| Split, 60 articles | 30–60 s | ~1 200 context tokens, ~900 response tokens |

Context token count is bounded by:
- **Consolidate:** number of categories × (name + count + up to 4 sub-category names)
- **Split:** number of articles × (title + up to ~5 sub-category themes)

Sub-categories in the Consolidate context are capped at 4 per category (`build_rich_organize_context`, line: `subcats[:4]`).

---

## Tuning Levers

| What to change | Where | Effect |
|---|---|---|
| Split threshold | `?threshold=N` query param (default 12) | Lower = more categories get split |
| Sub-category cap in Consolidate | `subcats[:4]` in `build_rich_organize_context` | Higher = richer context, more tokens, longer latency |
| OpenAI model | `AI_OPEN_AI_MODEL` env var | Better model = better groupings, higher cost |
| Temperature | `task_processor.py` | Lower = more conservative merges; higher = more creative names |
| max_tokens | `task_processor.py` | Must stay ≥ 1024; 4096 is safe for 60-article splits |
| httpx timeout | `aiapi_helper.py` `PerformTask` | Raise if getting timeouts on large taxonomies |

---

## Files at a Glance

| File | Role |
|---|---|
| `recap/profile/__init__.py` | All four routes + context builders + prompt strings |
| `recap/aiapi_helper.py` | `AiApiHelper.PerformTask()` — httpx POST to aiapi |
| `aiapi/task_processor.py` | `build_prompt()`, OpenAI call, JSON parsing, error handling |
| `aiapi/config.py` | `AIAPIConfig` — model name, API key, log level from env |
| `recap/templates/profile/organize_taxonomy.html` | Consolidate review UI (two-column diff + Accept/Reject) |
| `recap/templates/profile/suggest_splits.html` | Split review UI (same pattern as organize_taxonomy) |
| `tests/aiapi/unit/test_task_processor.py` | Unit tests: prompt structure, max_tokens guard, truncation handling |
| `tests/recap/integration/test_profile.py` | Integration tests for all four taxonomy routes |
| `tests/fixtures/organize_taxonomy_large_response.json` | 21-category fixture used in regression test |
