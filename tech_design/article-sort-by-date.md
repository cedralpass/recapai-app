# Article List Sort by Date

## Problem

Articles are currently sorted unread-first, then by descending id within each group. This means read articles sink to the end of the paginated list — a user who has marked several articles as read has to page through to the last page to find them again.

## Goal

Let users switch between two sort modes:

| Mode | Order | Use case |
|------|-------|----------|
| **Status** (default) | Unread first, then read; newest-first within each group | Day-to-day reading queue |
| **Date** | All articles newest-first regardless of read state | Browsing the full archive, finding a recently-read article |

The sort selection persists across pagination and composes with the existing `category` filter and `hide_read` flag.

---

## Design

### Query parameter

`?sort=date` — absent or any other value falls back to the default status sort.

Chosen over a boolean (`sort_by_date=true`) so the param is extensible (e.g. `sort=oldest` later) without a breaking change.

### URL composition

All three params are independent and stack:

```
/?sort=date&category=Technology&hide_read=true
```

Pagination links must forward all active params.

---

## Backend changes

### `recap/models.py` — `User.get_articles()`

Add a `sort` parameter (default `"status"`):

```python
def get_articles(self, page=1, per_page=10, category=None, include_read=True, sort="status"):
    if sort == "date":
        order = Article.id.desc()
    else:
        order = (Article.is_read.asc(), Article.id.desc())

    stmt = sa.select(Article).where(Article.user_id == self.id).order_by(*order)
    ...
```

`Article.id` is used as a proxy for `created` because it is always monotonically increasing and avoids a potential null on the `created` column for very old rows. If we later need true timestamp ordering, swap to `Article.created.desc()`.

### `recap/routes.py` — `index()`

Read the new param and thread it through:

```python
sort = request.args.get("sort", "status")
articles_paginator = current_user.get_articles(
    page=page,
    per_page=Config.ARTICLES_PER_PAGE,
    category=category,
    include_read=not hide_read,
    sort=sort,
)

pagination_kwargs = {"category": category, "sort": sort if sort != "status" else None}
if hide_read:
    pagination_kwargs["hide_read"] = "true"
```

Pass `sort` to the template context.

---

## Frontend changes

### `recap/templates/index.html`

Add a small sort toggle near the "Hide read articles" checkbox. A link-based toggle is preferable to a `<select>` — no JS, no form submit, and it renders inline with the filter controls:

```html
<div class="flex items-center gap-4 mb-3">
    <form method="get">
        {% if active_category %}<input type="hidden" name="category" value="{{ active_category }}">{% endif %}
        {% if sort != 'status' %}<input type="hidden" name="sort" value="{{ sort }}">{% endif %}
        <label class="flex items-center gap-2 text-sm text-gray-500 cursor-pointer">
            <input type="checkbox" name="hide_read" value="true"
                   {% if hide_read %}checked{% endif %}
                   onchange="this.form.submit()">
            Hide read articles
        </label>
    </form>

    <div class="flex items-center gap-1 text-sm text-gray-500">
        <span class="text-xs text-gray-400">Sort:</span>
        <a href="{{ url_for('routes.index', category=active_category, hide_read='true' if hide_read else None, sort=None) }}"
           class="text-xs {% if sort != 'date' %}font-semibold text-blue-600{% else %}text-gray-500 hover:text-gray-700{% endif %}">
            Unread first
        </a>
        <span class="text-gray-300">/</span>
        <a href="{{ url_for('routes.index', category=active_category, hide_read='true' if hide_read else None, sort='date') }}"
           class="text-xs {% if sort == 'date' %}font-semibold text-blue-600{% else %}text-gray-500 hover:text-gray-700{% endif %}">
            Newest first
        </a>
    </div>
</div>
```

---

## Test plan

### Unit — `tests/recap/unit/test_models.py`

| Test | What it checks |
|------|---------------|
| `test_get_articles_default_sort_unread_first` | With one read + one unread article, default sort returns unread first |
| `test_get_articles_date_sort_ignores_read_state` | With one read + one unread article, `sort="date"` returns newest-id first regardless of read state |

### Integration — `tests/recap/integration/test_read_viewed_state.py`

| Test | What it checks |
|------|---------------|
| `test_index_default_sort_shows_unread_before_read` | `GET /` — unread article title appears before read article title in response |
| `test_index_date_sort_shows_all_in_date_order` | `GET /?sort=date` — both articles present, newer id listed first |
| `test_sort_param_preserved_in_pagination_links` | `GET /?sort=date` — next/prev links contain `sort=date` |
| `test_sort_and_hide_read_compose` | `GET /?sort=date&hide_read=true` — read article absent, remaining articles in date order |

---

## Out of scope

- Oldest-first sort (`sort=oldest`) — can be added later with a one-line ORDER BY change
- Persisting the sort preference across sessions (cookie or user profile field)
- Sorting within the category filter sidebar counts
