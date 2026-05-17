# Reclassify Articles — Tech Design

## Goal

Give users a way to select stale or poorly-classified articles and re-run AI classification on them. This surfaces the benefit of prompt improvements (e.g. the dynamic category selection introduced in May 2026) and model upgrades without silent background changes.

---

## User Flow

1. User navigates to **Profile → Reclassify Articles**
2. Sees a paginated table of their articles sorted by `classified` date (oldest first by default — these are most likely to benefit from reclassification)
3. Unclassified articles (no `classified` date) appear at the top regardless of sort
4. User checks articles they want to re-run, optionally uses "Select all on page"
5. Clicks **Reclassify Selected** — each selected article is queued as an RQ job
6. Flash message: _"12 articles queued for reclassification. Results will appear in your article list shortly."_
7. User stays on the page (no result page needed — worker updates articles in the background)

---

## Routes

Both routes live in `recap/profile/__init__.py` under the `profile` blueprint.

### `GET /settings/reclassify`

Displays the paginated article table.

**Query params:**
| Param | Default | Description |
|---|---|---|
| `page` | `1` | Pagination page |
| `sort` | `oldest` | `oldest` (classified ASC, nulls first) or `newest` (classified DESC) |

**Logic:**
```python
@bp.route("/settings/reclassify", methods=["GET"])
@login_required
def reclassify_articles():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "oldest")

    stmt = (
        sa.select(Article)
        .where(Article.user_id == current_user.id)
        .order_by(
            Article.classified.asc().nulls_first()   # unclassified always first
            if sort == "oldest"
            else Article.classified.desc().nulls_first()
        )
    )
    pagination = db.paginate(stmt, page=page, per_page=20, error_out=False)
    return render_template(
        "profile/reclassify_articles.html",
        pagination=pagination,
        sort=sort,
    )
```

### `POST /settings/reclassify`

Receives the list of checked article IDs, validates ownership, and queues one RQ job per article.

**Logic:**
```python
@bp.route("/settings/reclassify", methods=["POST"])
@login_required
def reclassify_articles_post():
    article_ids = request.form.getlist("article_ids")
    if not article_ids:
        flash("No articles selected.", "error")
        return redirect(url_for("profile.reclassify_articles"))

    queued = 0
    for raw_id in article_ids:
        try:
            article_id = int(raw_id)
        except ValueError:
            continue
        article = db.session.get(Article, article_id)
        if not article or article.user_id != current_user.id:
            continue  # ownership check
        current_app.task_queue.enqueue(
            "recap.tasks.classify_url",
            article.url_path,
            current_user.id,
            job_timeout=120,
        )
        queued += 1

    flash(
        f"{queued} article{'s' if queued != 1 else ''} queued for reclassification. "
        "Results will appear in your article list shortly."
    )
    return redirect(url_for("profile.reclassify_articles"))
```

**Security:** Article ownership is verified before queuing. Non-integer IDs are silently skipped.

---

## Template: `reclassify_articles.html`

Extends `base.html`. Layout follows the same card/section style as other profile pages.

### Structure

```
Page header
  Title: "Reclassify Articles"
  Subtitle: "Select articles to re-run AI classification on. Useful after prompt or model updates."

Sort toggle  (right-aligned)
  [ Oldest classified first ]  [ Newest first ]

<form method="POST">
  <table>
    <thead>
      [ ] (select-all checkbox)  |  Title  |  Category  |  Classified
    </thead>
    <tbody>
      for article in pagination.items:
        [ ] checkbox  |  title (truncated, links to article)  |  category badge  |  classified date (or "Never")
    </tbody>
  </table>

  Pagination controls  (reuse pattern from index.html)

  Footer bar (sticky or below table)
    <span id="selected-count">0 selected</span>
    <button type="submit">Reclassify Selected</button>
</form>
```

### Key template details

**Checkboxes:**
```html
<input
  type="checkbox"
  name="article_ids"
  value="{{ article.id }}"
  class="article-checkbox"
>
```
Multiple `article_ids` values are collected by `request.form.getlist("article_ids")`.

**Select-all:**
```html
<input type="checkbox" id="select-all">
```
```javascript
document.getElementById('select-all').addEventListener('change', function () {
  document.querySelectorAll('.article-checkbox').forEach(cb => cb.checked = this.checked);
  updateCount();
});
```

**Live selection count + button state:**
```javascript
function updateCount() {
  const n = document.querySelectorAll('.article-checkbox:checked').length;
  document.getElementById('selected-count').textContent = n + ' selected';
  document.getElementById('submit-btn').disabled = n === 0;
}
document.querySelectorAll('.article-checkbox').forEach(cb =>
  cb.addEventListener('change', updateCount)
);
```

**Classified date display:**
```html
{% if article.classified %}
  {{ article.classified.strftime('%d %b %Y') }}
{% else %}
  <span class="text-gray-400 italic">Never</span>
{% endif %}
```

**Category badge:**
```html
{% if article.category %}
  <span class="inline-flex items-center bg-indigo-50 border border-indigo-200 rounded-full px-2 py-0.5 text-xs text-indigo-700">
    {{ article.category }}
  </span>
{% else %}
  <span class="text-gray-400 italic text-xs">Uncategorised</span>
{% endif %}
```

**Sort toggle:**
```html
<a href="{{ url_for('profile.reclassify_articles', sort='oldest', page=1) }}"
   class="{{ 'font-semibold text-indigo-600' if sort == 'oldest' else 'text-gray-500' }}">
  Oldest first
</a>
|
<a href="{{ url_for('profile.reclassify_articles', sort='newest', page=1) }}"
   class="{{ 'font-semibold text-indigo-600' if sort == 'newest' else 'text-gray-500' }}">
  Newest first
</a>
```

---

## Navigation Entry

Add a link to the profile sidebar/menu. In `recap/templates/profile/` base or the profile nav section:

```html
<a href="{{ url_for('profile.reclassify_articles') }}">Reclassify Articles</a>
```

Placement: after the existing **Organise Taxonomy** link.

---

## Files to Create / Modify

| File | Change |
|---|---|
| `recap/profile/__init__.py` | Add `reclassify_articles()` (GET) and `reclassify_articles_post()` (POST) routes |
| `recap/templates/profile/reclassify_articles.html` | New template |
| `recap/templates/profile/edit_profile.html` or nav partial | Add navigation link |

No new tasks, migrations, or models needed. The existing `recap.tasks.classify_url` handles reclassification.

---

## Pagination

Reuse SQLAlchemy `db.paginate()` — same pattern as `User.get_articles()` in `models.py`.

Pass `sort` through pagination links so sort order is preserved across pages:
```html
{{ url_for('profile.reclassify_articles', page=pagination.next_num, sort=sort) }}
```

---

## Edge Cases

| Case | Handling |
|---|---|
| No articles selected | Flash error, redirect back |
| Invalid / non-integer article ID in form | Skipped silently |
| Article belongs to another user | Skipped silently (ownership check) |
| Article already in RQ queue | Harmless duplicate — worker will re-classify and overwrite with same result |
| User has 0 articles | Show empty state: _"No articles yet. Add some from the home page."_ |

---

## Testing

### Unit tests (`tests/recap/unit/`)
- `test_reclassify_articles_get` — returns 200, renders correct template, pagination works
- `test_reclassify_articles_post_queues_jobs` — mocks `task_queue.enqueue`, verifies called once per selected article
- `test_reclassify_articles_post_ownership` — article belonging to another user is not queued
- `test_reclassify_articles_post_no_selection` — flash error when no IDs submitted

### Manual smoke test
1. Open `/settings/reclassify`
2. Verify articles appear sorted oldest-classified first, with "Never" for unclassified
3. Check a few articles, submit
4. Verify flash message shows correct count
5. Watch rq-worker logs — confirm jobs are enqueued and complete
6. Reload article list — verify categories updated

---

## Out of Scope

- Real-time progress bar per article (RQ jobs are fast, flash message is sufficient)
- Filtering by category (can be added later if needed)
- Showing a diff of old vs new category after reclassification (can be added later)
- Auto-scheduled reclassification (user-triggered only — avoids overwriting manual curation)
