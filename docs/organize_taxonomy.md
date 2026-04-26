# Organize Taxonomy Flow

The organize taxonomy feature lets a user consolidate their article categories with one AI-assisted step. It reads the user's existing categories, asks OpenAI to suggest a cleaner grouping, shows a before/after preview, and batch-rewrites every article's category field on confirmation.

---

## Data Model

Categories are **denormalized strings** on the `Article` model — there is no separate Category table.

**`recap/models.py` — Article**

| Field | Type | Notes |
|---|---|---|
| `category` | `str` (max 140) | Single category string, e.g. `"Technology"` |
| `key_topics` | `str` | JSON-encoded list of topic strings |
| `sub_categories` | `str` | JSON-encoded list of sub-category strings |

Helper methods `get_key_topics_json()` and `get_sub_categories_json()` parse the JSON text fields into Python lists.

**`recap/models.py` — User.get_categories()**

Aggregates categories live from the articles table — no materialized category list. Returns `[(category, count), ...]` sorted by count descending.

> There is also a `Topic` model (a reference table with name + definition) that is not currently wired into the taxonomy flow.

---

## Routes

All routes are in `recap/profile/__init__.py`.

### `GET /organize_taxonomy`

Entry point. Called when the user clicks **Reclassify** on their profile page.

1. Fetches `current_user.get_categories()` → list of `(category, count)` tuples.
2. Formats the category names as a comma-separated string and sends to `AiApiHelper.PerformTask()` with:
   - **context**: the user's current categories
   - **prompt**: asks OpenAI to consolidate similar categories while preserving "Artificial Intelligence" and "Software Architecture"
   - **format**: JSON schema specifying a `mappings` array of `{old_category, new_category}` objects plus a `description` string
3. Parses the response into:
   - `category_mapping` — dict of `{old: new}` (stored in `session['category_mapping']`)
   - `suggested` — deduplicated list of new category names (for display)
   - `description` — human-readable summary of proposed changes (for display)
4. Renders `profile/organize_taxonomy.html` with `categories`, `suggested`, and `description`.

### `POST /apply_taxonomy`

Commit step. No user-editable inputs — applies whatever mapping was stored in the session.

1. Reads `session['category_mapping']`.
2. For each `old → new` pair, queries all of the user's articles where `category == old` and sets `category = new`.
3. Commits all updates in a single transaction.
4. Clears `session['category_mapping']`.
5. Flashes a success message and redirects to the user profile.

---

## Template

`recap/templates/profile/organize_taxonomy.html` — a single white card, four sections.

### Current Organization

Gray pill buttons for each existing category, labelled with name and count (e.g. `Tech(5)`). Each pill links to `routes.index?category=<name>`, so clicking one filters the reading list to that category.

### Suggested Organization

The AI's `description` text, then a second row of gray pills showing the proposed category names after consolidation. These pills also link to `routes.index?category=<name>` (using the new name), so the user can preview what that filtered view would look like — though the articles won't have been renamed yet.

### Apply Button

A single blue **Apply Category Changes** button that POSTs to `/apply_taxonomy`. There is no confirmation dialog and no undo. Clicking it immediately batch-rewrites all article category fields.

> **Note:** The `category_mapping` dict is passed to the template context but is not rendered anywhere in the HTML — only `suggested` and `description` are displayed.

---

## Article Filtering

Category filtering is used throughout the app, not just in this flow.

- `routes.index()` accepts a `?category=` query param.
- `User.get_articles(category=...)` adds a `.where(Article.category == category)` clause.
- `recap/templates/profile/_article.html` renders the category as a small gray pill badge on each article card.

---

## AI Integration

The route calls `AiApiHelper.PerformTask()` (`recap/aiapi_helper.py`), which POSTs to the external `aiapi` service at `RECAP_AI_API_URL/process_task`. Passing a JSON schema as the `format` argument enforces structured output from OpenAI — the response is guaranteed to be a list of `{old_category, new_category}` pairs rather than freeform text.

---

## Known Limitations

- **All-or-nothing apply:** The user cannot edit individual mappings. They either accept all AI suggestions or cancel entirely.
- **No undo:** Applying the taxonomy permanently overwrites `category` on every affected article. The only way back is to re-run the flow.
- **Session trust:** `apply_taxonomy` reads directly from the Flask session with no re-validation. Stale or tampered session data runs as-is.
- **Unmapped categories are untouched:** Articles with a category that does not appear in the AI's mappings keep their original value.

---

## Files at a Glance

| File | Role |
|---|---|
| `recap/profile/__init__.py` | Routes: `organize_taxonomy`, `apply_taxonomy` |
| `recap/templates/profile/organize_taxonomy.html` | Before/after preview UI |
| `recap/templates/profile/user.html` | Profile page — "Reclassify" entry point |
| `recap/templates/profile/_article.html` | Article card — renders category badge |
| `recap/models.py` | `Article.category`, `User.get_categories()` |
| `recap/aiapi_helper.py` | `AiApiHelper.PerformTask()` — wraps the AI API call |
| `tests/recap/integration/test_profile.py` | Integration tests for the taxonomy routes |
