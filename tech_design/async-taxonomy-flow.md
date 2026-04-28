# Async Taxonomy Flow — Option B Implementation Brief

## Problem

Both `/organize_taxonomy` and `/user/<username>/suggest_splits` call the AI API
**synchronously**, blocking the HTTP request for up to 180 seconds with no user
feedback. If the request times out or the user navigates away, the work is lost.

## Goal

Mirror the existing article-save pattern (RQ job → polling → result) for the
taxonomy pages, so the user sees immediate feedback and the AI work happens in
the background.

---

## Architecture

```
Browser                     Flask (recap)               RQ Worker
  |                              |                           |
  | GET /organize_taxonomy       |                           |
  |----------------------------->|                           |
  |                              | enqueue task              |
  |                              |-------------------------->|
  | 200 "processing" page        |                           |
  |<-----------------------------|                           |
  |                              |                           | call AI API
  | poll GET /job/<id>/show      |                           | (up to 180s)
  |----------------------------->|                           |
  | {"status": "queued"}         |                           |
  |<-----------------------------|                           |
  |   ... (every 3s) ...         |                           |
  |                              |                           | store result
  |                              |                           | in Redis
  | {"status": "finished"}       |                           |
  |<-----------------------------|                           |
  | JS redirects to result route |                           |
  |----------------------------->|                           |
  |                              | read from Redis           |
  |                              | render template           |
  | 200 results page             |                           |
  |<-----------------------------|                           |
```

---

## Files to Change

### 1. `recap/tasks.py` — two new RQ task functions

**`organize_taxonomy_task(user_id)`**
- Calls `build_rich_organize_context(user_id)` (import from `profile`)
- Calls `AiApiHelper.PerformTask(...)` with the existing organize prompt/format
- Serialises the full result dict as JSON
- Stores in Redis: `taxonomy:organize:<job_id>` with a **1-hour TTL**
- Key data to store: `description`, `mappings` (the raw AI response)

**`suggest_splits_task(user_id, threshold=12)`**
- Queries large categories (≥ threshold articles) from DB
- For each large category, calls `build_split_context(...)` + `AiApiHelper.PerformTask(...)`
- After each category completes, writes incremental progress to `job.meta`:
  ```python
  job.meta['progress'] = f"{done} of {total} categories processed"
  job.save_meta()
  ```
- Stores final result dict as JSON in Redis: `taxonomy:splits:<job_id>` with **1-hour TTL**
- Key data to store: the `suggestions` dict keyed by category name

Both tasks must push an app context (`app.app_context().push()`) — see existing
`classify_url` task for the pattern.

> **Helper functions to import:** `build_rich_organize_context`, `build_split_context`
> live in `recap/profile/__init__.py`. To avoid a circular import, move them into a
> new `recap/taxonomy_helpers.py` module and import from there in both
> `profile/__init__.py` and `tasks.py`.

---

### 2. `recap/profile/__init__.py` — convert both routes + add result routes

#### `organize_taxonomy` — before/after

**Before:** calls AI synchronously, renders template.

**After:**
```python
@bp.route('/organize_taxonomy', methods=['GET'])
@login_required
def organize_taxonomy():
    job = current_app.task_queue.enqueue(
        'recap.tasks.organize_taxonomy_task',
        current_user.id,
        job_timeout=300,
    )
    return render_template('profile/taxonomy_processing.html',
                           job_id=job.id,
                           result_url=url_for('profile.organize_taxonomy_result', job_id=job.id),
                           title='Organising Taxonomy…')
```

New result route:
```python
@bp.route('/organize_taxonomy/result/<job_id>')
@login_required
def organize_taxonomy_result(job_id):
    redis = current_app.redis
    data = redis.get(f'taxonomy:organize:{job_id}')
    if not data:
        flash('Result expired or not found. Please try again.')
        return redirect(url_for('profile.user', username=current_user.username))

    json_response = json.loads(data)
    # ... existing logic that builds suggestions, current_annotated, proposed_annotated ...
    # Store category_mapping + suggestion_mappings in session (same as today)
    session['category_mapping'] = category_mapping
    session['suggestion_mappings'] = suggestion_mappings
    return render_template('profile/organize_taxonomy.html', ...)
```

#### `suggest_splits` — same pattern

**After:** enqueues `suggest_splits_task`, renders `taxonomy_processing.html`
with `result_url` pointing to a new `suggest_splits_result` route.

New result route reads from `taxonomy:splits:<job_id>`, runs the existing
`suggestion_list` / `large_cats` / `split_assignments` assembly logic, and
renders the existing `suggest_splits.html` template.

#### `apply_taxonomy` and `apply_splits` — **no changes needed**

They read from the Flask session, which the result routes populate exactly as
the old synchronous routes did.

---

### 3. New template: `recap/templates/profile/taxonomy_processing.html`

A full-page waiting screen. Reuse `base.html`. Key elements:

- Animated spinner (same SVG used in `_article.html`)
- Heading: "Working on it…"
- Subtext: "AI is reviewing your categories. This usually takes 1–3 minutes."
- **Progress line** (for splits only): `<p id="progress-msg"></p>` — hidden for
  organize, shown for splits
- JavaScript that polls `/job/<job_id>/show` every **3 seconds**:

```javascript
async function poll() {
  const res = await fetch('/job/{{ job_id }}/show');
  const data = await res.json();

  // Show incremental progress if present
  if (data.meta && data.meta.progress) {
    document.getElementById('progress-msg').textContent = data.meta.progress;
  }

  if (data.status === 'finished') {
    window.location.href = '{{ result_url }}';
  } else if (data.status === 'failed') {
    document.getElementById('status-msg').textContent =
      'Something went wrong. Please go back and try again.';
  } else {
    setTimeout(poll, 3000);
  }
}
setTimeout(poll, 3000);  // first check after 3s
```

- A "cancel / go back" link so the user isn't trapped.

---

### 4. `recap/routes.py` — minor enhancement to `/job/<id>/show`

The existing endpoint returns `{"id", "status", "description"}`.
Add `"meta"` to the response so the template can surface progress:

```python
return {
    "id": job.id,
    "status": status,
    "description": job.description,
    "meta": job.meta,          # <-- add this line
}
```

---

## Redis Key Design

| Key | Content | TTL |
|-----|---------|-----|
| `taxonomy:organize:<job_id>` | Raw AI JSON (`description` + `mappings`) | 1 hour |
| `taxonomy:splits:<job_id>` | `suggestions` dict (per-category assignments) | 1 hour |

Use `redis.setex(key, 3600, json.dumps(data))`.

The 1-hour TTL means a result page visited more than an hour after the job
finishes will show a "result expired" flash and redirect. That's acceptable —
users shouldn't be sitting on these pages that long.

---

## Refactor: `recap/taxonomy_helpers.py` (new file)

Move these two pure functions out of `profile/__init__.py` to break the
circular import between `tasks.py` and `profile/__init__.py`:

- `get_categories_with_subcats(user_id)`
- `build_rich_organize_context(user_id)`
- `build_split_context(category_name, articles)`

Update imports in `profile/__init__.py` and `tasks.py` accordingly.

---

## Testing Notes

- Existing tests for `apply_taxonomy` and `apply_splits` POST with session data
  directly — they don't go through the new routes and **will not need changes**.
- Add a test for each new result route: mock `current_app.redis.get` to return
  a fixture JSON blob, assert the template renders correctly.
- The `suggest_splits_task` progress reporting can be verified by inspecting
  `job.meta` after calling the task function directly (no RQ worker needed).

---

## Sequence of Changes (suggested order)

1. Create `recap/taxonomy_helpers.py` — move the three helper functions
2. Update imports in `recap/profile/__init__.py`
3. Add two task functions to `recap/tasks.py`
4. Add the `"meta"` field to the job status endpoint in `recap/routes.py`
5. Create `recap/templates/profile/taxonomy_processing.html`
6. Rewrite `organize_taxonomy` route + add `organize_taxonomy_result` route
7. Rewrite `suggest_splits` route + add `suggest_splits_result` route
8. Smoke test end-to-end with the `recap` and `rq-worker` preview servers running
