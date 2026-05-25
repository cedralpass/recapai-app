# Weekly Digest — In-App Entry Points

## Build Status

**Shipped** (May 2026)

---

## Overview

The weekly digest email is live and sending on a scheduled cadence. This feature surfaces the
digest inside the app so users can reach it from anywhere, see when a fresh one is ready, generate
one on demand, and regenerate when they've added meaningful new bookmarks.

**Design source:** [`tech_design/weekly-digest-entry-points-assets/`](weekly-digest-entry-points-assets/)  
The chosen direction is **Option E ("A + Sidebar")** from the design canvas: a nav link with an
unread indicator, a sidebar card on the home page (3 states), and a new `/digest` page that renders
the email digest inside the app shell.

---

## Goals

| Goal | Status |
|---|---|
| Nav link to weekly digest | Shipped |
| `/digest` page — in-app digest viewer | Shipped |
| Sidebar card — fresh state (unread digest) | Shipped |
| Sidebar card — empty state (no digest yet) | Shipped |
| Sidebar card — generating state (on-demand generation in flight) | Shipped |
| On-demand digest generation from sidebar | Shipped |
| Regenerate banner (≥3 new bookmarks since generation) | Shipped |
| Mobile treatment (card below article list) | Shipped |

---

## What Already Exists

The synthesis agent, scheduler, and management UI are fully built
([`weekly-synthesis-agent.md`](weekly-synthesis-agent.md)). This feature adds the **user-facing
surface** on top of that infrastructure.

| Already exists | Notes |
|---|---|
| `DigestRun` model | In `recap/models.py`; missing `opened_at` and `cluster_count` columns |
| `weekly_digest_task` | In `recap/tasks.py`; populates `DigestRun.digest_html` |
| Email template | `recap/templates/email/weekly_digest.html` |
| Management UI | `/settings/digest-runs` — for debugging, will stay separate |
| Job polling endpoint | `GET /job/<job_id>/show` — reusable for the new generate flow |

---

## Schema Changes Required

Two new columns on `DigestRun`:

```python
# recap/models.py — DigestRun additions
opened_at: so.Mapped[Optional[datetime]] = so.mapped_column(
    sa.DateTime(timezone=True), nullable=True
)
cluster_count: so.Mapped[Optional[int]] = so.mapped_column(sa.Integer(), nullable=True)
```

- **`opened_at`** — set to `now()` the first time the user opens `/digest`. Drives the unread
  dot in the nav and the "fresh" vs "seen" sidebar state.
- **`cluster_count`** — stored when the digest job completes so the sidebar card can display
  "N articles, M topics" without parsing the HTML. Update `weekly_digest_task` in `tasks.py`
  to populate it from `len(final_state["clusters"])`.

**Migration:** new Alembic revision under `migrations/versions/`.

---

## Config Addition

```python
# recap/config.py
DIGEST_REGENERATE_THRESHOLD = 3
```

The regenerate banner on `/digest` appears when this many or more bookmarks have been saved
since `DigestRun.generated_at`. Externalised so it can be tuned without a code change.

---

## New Routes

All new routes go in `recap/routes.py` (existing `routes` blueprint). The design references
`url_for('main.digest')` — translate to `url_for('routes.digest')` in templates.

| Method | Path | Handler | Notes |
|---|---|---|---|
| `GET` | `/digest` | `digest()` | Render latest digest; set `opened_at` on first view |
| `POST` | `/digest/generate` | `digest_generate()` | Kick off on-demand job; return `{"job_id": "..."}` JSON |
| `POST` | `/digest/<int:digest_id>/regenerate` | `digest_regenerate()` | Same, tied to existing run |
| `GET` | `/digest/job/<job_id>` | `digest_job_status()` | Poll status; return `{"status": "...", "view_url": "..."}` |

### `GET /digest`

1. Query latest `DigestRun` for `current_user` where `status == "completed"`, ordered by
   `created_at DESC`.
2. If none found, redirect to home with a flash message prompting the user to generate one.
3. On first view (`opened_at is None`): set `opened_at = now()` and commit.
4. Compute `bookmarks_since_digest` = count of `Article` where
   `created_at > digest_run.completed_at` (use `completed_at` as the cutoff, not `created_at`,
   since the job runs for ~30s after creation).
5. Pass `show_regenerate_banner = bookmarks_since_digest >= config.DIGEST_REGENERATE_THRESHOLD`.
6. Render `digest.html`.

### `POST /digest/generate`

Enqueue `weekly_digest_task(current_user.id, send_email_flag=False)` — same as the existing
"Test Run" button on the management page. Return JSON so the sidebar card can start polling:

```python
return jsonify({"status": "queued", "job_id": job.id})
```

AJAX-only route (no redirect). The sidebar JS handles state transitions.

### `POST /digest/<int:digest_id>/regenerate`

Same as `/digest/generate` but attach the `DigestRun.id` to the new job so the result
overwrites the existing run record (or creates a new one, simpler). Return JSON with `job_id`.

### `GET /digest/job/<job_id>`

Thin wrapper around RQ job status. Mirrors the existing `/job/<job_id>/show` pattern in
`routes.py`. Returns:

```json
{"status": "queued|started|finished|failed", "view_url": "/digest"}
```

On `finished`, the JS navigates to `/digest`. On `failed`, surface an error in the card.

---

## Template Changes

### 1. `recap/templates/base.html` — Nav link

Insert between "Home" and "Profile", authenticated users only:

```html
{% if current_user.is_authenticated %}
<a class="relative inline-flex items-center gap-1.5 font-medium text-slate-200 underline hover:no-underline"
   href="{{ url_for('routes.digest') }}">
  Weekly Digest
  {% if has_unread_digest %}
  <span class="w-1.5 h-1.5 rounded-full bg-amber-400 ring-2 ring-black" aria-label="New digest"></span>
  {% endif %}
</a>
{% endif %}
```

`has_unread_digest` must be injected into every authenticated template. Use Flask's
`@app.context_processor` (add to `recap/__init__.py`) to compute it once and expose it globally:

```python
@app.context_processor
def inject_digest_state():
    if current_user.is_authenticated:
        latest = db.session.scalar(
            sa.select(DigestRun)
            .where(DigestRun.user_id == current_user.id, DigestRun.status == "completed")
            .order_by(DigestRun.created_at.desc())
        )
        return {
            "has_unread_digest": latest is not None and latest.opened_at is None,
            "latest_digest": latest,
        }
    return {"has_unread_digest": False, "latest_digest": None}
```

### 2. `recap/templates/index.html` — Sidebar card

Insert a new `<div>` **above** the "Filter Articles" heading inside the `<aside>` block.
The card has three mutually exclusive states, selected in the route handler and passed via
a `digest_card_state` template variable (`"fresh"`, `"empty"`, `"generating"`).

Tailwind note: `font-serif` is Tailwind's default Georgia stack — use it directly; it works
with the existing Tailwind config without any extension.

**Fresh state** (digest exists, `opened_at` is null):
```html
<div class="bg-slate-900 rounded-lg p-4 mb-5 text-white">
  <div class="text-[10px] font-bold tracking-[0.16em] uppercase text-amber-400 mb-2">
    This Week · Recap
  </div>
  <div class="font-serif text-lg font-bold leading-tight mb-1.5">
    {{ latest_digest.article_count }} articles, {{ latest_digest.cluster_count }} topics
  </div>
  <div class="font-serif italic text-[13px] text-slate-300 leading-relaxed mb-3">
    Your Monday digest is ready.
  </div>
  <a href="{{ url_for('routes.digest') }}"
     class="inline-block text-[13px] font-bold text-white no-underline border-b-2 border-amber-400 pb-0.5">
    Read digest →
  </a>
</div>
```

**Empty state** (no completed digest, or digest already opened):
```html
<div class="bg-white rounded-lg p-4 mb-5 border border-dashed border-slate-300">
  <div class="text-[10px] font-bold tracking-[0.16em] uppercase text-slate-500 mb-2">
    This Week · Recap
  </div>
  <div class="font-serif text-lg font-bold text-slate-900 leading-snug mb-1.5">
    No digest yet
  </div>
  <div class="font-serif italic text-[13px] text-slate-600 leading-relaxed mb-3.5">
    Mondays at 8am — or generate one now from your {{ recent_bookmark_count }} recent bookmarks.
  </div>
  <button type="button" id="digest-generate-btn"
          class="w-full bg-slate-900 text-white border-none rounded-md py-2.5 px-3 text-[13px] font-bold cursor-pointer flex items-center justify-center gap-1.5">
    <!-- sparkle/sun SVG icon -->
    Generate recap now
  </button>
  <div class="text-[11px] text-slate-400 mt-2 text-center">Takes ~30 seconds</div>
</div>
```

**Generating state** (shown after click, via JS swap):
```html
<div class="bg-white rounded-lg p-4 mb-5 border border-dashed border-slate-300">
  <div class="text-[10px] font-bold tracking-[0.16em] uppercase text-slate-500 mb-2">
    This Week · Recap
  </div>
  <div class="font-serif text-lg font-bold text-slate-900 leading-snug mb-1.5">
    Brewing your recap…
  </div>
  <div class="font-serif italic text-[13px] text-slate-600 leading-relaxed mb-3.5">
    Reading your bookmarks, finding the threads.
  </div>
  <div class="h-1.5 bg-slate-200 rounded-full overflow-hidden">
    <div id="digest-progress-bar" class="h-full bg-slate-900" style="width: 20%; transition: width 500ms ease"></div>
  </div>
  <div class="text-[11px] text-slate-400 mt-2 text-center">~30 seconds remaining</div>
</div>
```

The empty → generating swap is done by JS (vanilla, matching the existing classification
polling pattern): POST to `/digest/generate`, swap the card HTML, start polling
`/digest/job/<job_id>` at 500ms intervals, animate the progress bar, navigate to `/digest`
on `finished`.

**Mobile treatment:** On mobile, the `<aside>` is `hidden md:block`, so the same card is
rendered in a separate `<div class="md:hidden">` block below the article list container,
with the same three-state logic. Only the fresh and empty states appear on mobile; if the
digest has been opened and there's nothing new, the mobile block is hidden entirely
(`{% if latest_digest and latest_digest.opened_at is none or not latest_digest %}`).

### 3. New `recap/templates/digest.html`

In-app digest viewer. Extends `base.html`. Background is `bg-stone-50` (closest to the
email's `#faf8f3` cream). Inner content adapts the email template structure to the app shell:

```
base.html shell (nav + footer)
  └── main.container
        ├── [regenerate banner — conditional]
        └── digest card (white, max-w-2xl mx-auto, shadow-lg rounded)
              ├── masthead (eyebrow, h1, italic tagline, article/topic count)
              └── cluster sections (label, narrative, article list)
```

Key differences from the email template:
- No `<table>` layout — use `<div>` + Tailwind flexbox/block
- Links are internal (article detail page) rather than original URLs
- No email-client hacks or `!important` style overrides
- Cluster labels use `text-blue-600` (matches existing design system link color)
- Serif font applied via `font-serif` Tailwind class on headings + narratives

#### Regenerate banner

Shown above the digest card when `show_regenerate_banner` is `True`:

```html
{% if show_regenerate_banner %}
<div class="bg-amber-50 border-b border-amber-300 px-7 py-3.5 flex items-center justify-between gap-4 mb-6 rounded-lg">
  <div class="flex items-center gap-2.5 min-w-0">
    <!-- info-circle SVG, text-amber-700 -->
    <div class="text-[13.5px] text-amber-900 leading-snug">
      <b>{{ bookmarks_since_digest }} new bookmarks</b> since this digest was generated.
      Regenerate to include them.
    </div>
  </div>
  <button id="digest-regenerate-btn"
          class="bg-slate-900 text-white rounded-md py-2 px-3.5 font-bold text-[13px] inline-flex items-center gap-1.5 whitespace-nowrap">
    <!-- refresh-cw SVG -->
    Regenerate
  </button>
</div>
{% endif %}
```

Regenerate click: POST to `/digest/<digest_id>/regenerate`, show inline progress (reuse
generating card pattern), reload page on completion.

---

## Interaction & JS

All client-side logic is vanilla JS, matching the existing article-classification polling
pattern in `recap/templates/index.html`.

### Generate flow (sidebar empty card)

```
click "Generate recap now"
  → POST /digest/generate → { job_id }
  → swap card HTML to GENERATING state
  → setInterval 500ms → GET /digest/job/<job_id>
      status = "finished" → navigate to /digest
      status = "failed"   → show error text in card, restore button
```

### Regenerate flow (digest page banner)

```
click "Regenerate"
  → button disabled + spinner shown
  → POST /digest/<id>/regenerate → { job_id }
  → setInterval 500ms → GET /digest/job/<job_id>
      status = "finished" → window.location.reload()
      status = "failed"   → surface error, re-enable button
```

### Progress bar animation

The progress bar in the generating state uses a simple fake-progress approach: start at 20%,
increment by a small random amount every 2s, cap at 90%, jump to 100% on `finished`. This
matches the email that says "~30 seconds" and avoids the need for real server-side progress.

---

## Template Variable Summary

### `index()` route additions

| Variable | Type | Source |
|---|---|---|
| `digest_card_state` | `"fresh" \| "empty" \| "generating"` | Derived from `latest_digest` |
| `recent_bookmark_count` | `int` | Count of user's articles, capped at 25 |
| `latest_digest` | `DigestRun \| None` | Latest completed run |

(`has_unread_digest` and `latest_digest` come from the context processor and are available
globally — no need to pass them explicitly from the route.)

### `digest()` route

| Variable | Type | Source |
|---|---|---|
| `digest_run` | `DigestRun` | Latest completed run |
| `show_regenerate_banner` | `bool` | `bookmarks_since >= threshold` |
| `bookmarks_since_digest` | `int` | Count of articles since `completed_at` |

---

## Testing

Tests are written alongside the code, one step at a time. Each step in the implementation order
below names which tests to write before moving to the next step.

### Test files

| File | What it covers |
|---|---|
| `tests/recap/unit/test_digest_entry_points.py` | Model helpers, context processor logic, threshold config |
| `tests/recap/integration/test_digest_routes.py` | All 4 new HTTP routes end-to-end |
| `tests/recap/integration/test_digest_sidebar.py` | Sidebar card HTML states on the index page |
| `tests/recap/integration/test_digest_nav.py` | Nav link presence, unread dot, opened_at clearing |

All recap integration tests use the existing `recap_app` / `recap_client` / `seeded_user` /
`seeded_authenticated_client` fixtures from `tests/conftest.py`. New fixtures for `DigestRun`
records go in `conftest.py` alongside the existing ones.

### New conftest fixtures

```python
@pytest.fixture
def completed_digest_run(recap_app, seeded_user):
    """A completed DigestRun for seeded_user with digest_html, article_count, cluster_count."""
    from datetime import datetime, timezone, timedelta
    from recap import db
    from recap.models import DigestRun

    with recap_app.app_context():
        now = datetime.now(timezone.utc)
        run = DigestRun(
            user_id=seeded_user.id,
            status="completed",
            week_start=now - timedelta(days=7),
            week_end=now,
            completed_at=now,
            article_count=12,
            cluster_count=3,
            digest_html="<p>Test digest</p>",
            digest_text="Test digest",
            sent=True,
        )
        db.session.add(run)
        db.session.commit()
        yield run


@pytest.fixture
def unread_digest_client(recap_app, seeded_user, completed_digest_run):
    """Authenticated client as seeded_user with an unread completed digest."""
    client = recap_app.test_client()
    client.post("/auth/login", data={"username": "seeduser", "password": "seedpass123"})
    return client


@pytest.fixture
def opened_digest_run(recap_app, seeded_user):
    """A completed DigestRun that has already been opened (opened_at is set)."""
    from datetime import datetime, timezone, timedelta
    from recap import db
    from recap.models import DigestRun

    with recap_app.app_context():
        now = datetime.now(timezone.utc)
        run = DigestRun(
            user_id=seeded_user.id,
            status="completed",
            week_start=now - timedelta(days=7),
            week_end=now,
            completed_at=now,
            opened_at=now,
            article_count=12,
            cluster_count=3,
            digest_html="<p>Test digest</p>",
            digest_text="Test digest",
            sent=True,
        )
        db.session.add(run)
        db.session.commit()
        yield run
```

### Unit tests — `test_digest_entry_points.py`

These test pure logic without HTTP, using `recap_app` for DB access.

| Test | What it verifies |
|---|---|
| `test_opened_at_defaults_to_none` | New `DigestRun` has `opened_at = None` |
| `test_cluster_count_stored` | `cluster_count` column is persisted and read back correctly |
| `test_digest_regenerate_threshold_default` | `Config.DIGEST_REGENERATE_THRESHOLD == 3` |
| `test_has_unread_digest_true_when_opened_at_none` | Context processor returns `True` when `opened_at` is null |
| `test_has_unread_digest_false_when_opened_at_set` | Returns `False` after `opened_at` is set |
| `test_has_unread_digest_false_when_no_digest` | Returns `False` for a user with no completed runs |
| `test_bookmarks_since_digest_count` | Count of articles created after `completed_at` is correct |
| `test_show_regenerate_banner_below_threshold` | `False` when count < 3 |
| `test_show_regenerate_banner_at_threshold` | `True` when count == 3 |
| `test_show_regenerate_banner_above_threshold` | `True` when count > 3 |

### Integration tests — `test_digest_routes.py`

Use `unread_digest_client` and `recap_client` fixtures. RQ job enqueueing is mocked with
`unittest.mock.patch("recap.routes.q.enqueue")` (same pattern as
`test_schedule_weekly_digests_task.py`).

| Test | Route | What it verifies |
|---|---|---|
| `test_digest_page_requires_login` | `GET /digest` | Redirects to login if anonymous |
| `test_digest_page_no_digest_redirects_home` | `GET /digest` | Redirects to `/` + flash when no completed run |
| `test_digest_page_renders_digest_html` | `GET /digest` | `digest_html` content appears in response |
| `test_digest_page_sets_opened_at_on_first_view` | `GET /digest` | `opened_at` is null before, set after |
| `test_digest_page_does_not_overwrite_opened_at` | `GET /digest` | Second visit doesn't change `opened_at` |
| `test_digest_page_no_regenerate_banner_below_threshold` | `GET /digest` | Banner absent when < 3 new bookmarks |
| `test_digest_page_shows_regenerate_banner_at_threshold` | `GET /digest` | Banner present when ≥ 3 new bookmarks |
| `test_digest_generate_requires_login` | `POST /digest/generate` | 401/redirect for anonymous |
| `test_digest_generate_enqueues_job` | `POST /digest/generate` | Returns JSON with `job_id` |
| `test_digest_generate_job_id_in_response` | `POST /digest/generate` | `job_id` key present in JSON response |
| `test_digest_regenerate_requires_login` | `POST /digest/<id>/regenerate` | 401/redirect for anonymous |
| `test_digest_regenerate_enqueues_job` | `POST /digest/<id>/regenerate` | Returns JSON with `job_id` |
| `test_digest_regenerate_404_on_wrong_user` | `POST /digest/<id>/regenerate` | 404 when `digest_id` belongs to another user |
| `test_digest_job_status_queued` | `GET /digest/job/<job_id>` | Returns `{"status": "queued"}` |
| `test_digest_job_status_finished_includes_view_url` | `GET /digest/job/<job_id>` | Returns `view_url: "/digest"` on finished |

### Integration tests — `test_digest_sidebar.py`

Use `unread_digest_client`, `seeded_authenticated_client`, and `recap_client`. Tests assert on
rendered HTML of `GET /`.

| Test | What it verifies |
|---|---|
| `test_fresh_card_shown_when_unread_digest` | Dark `bg-slate-900` card appears in `<aside>` |
| `test_fresh_card_shows_article_and_cluster_count` | "12 articles, 3 topics" copy is present |
| `test_fresh_card_has_read_digest_link` | "Read digest" link points to `/digest` |
| `test_empty_card_shown_when_no_digest` | Dashed `border-dashed` card appears for a user with no completed digest |
| `test_empty_card_shows_generate_button` | "Generate recap now" button present in empty state |
| `test_empty_card_absent_when_digest_opened` | Neither card appears when digest has been opened and nothing new |
| `test_fresh_card_absent_for_anonymous_user` | No digest card in sidebar for logged-out visitors |
| `test_mobile_fresh_card_shown_below_article_list` | `md:hidden` wrapper containing fresh card is present in HTML |
| `test_mobile_empty_card_shown_below_article_list` | `md:hidden` wrapper with empty card present for user with no digest |
| `test_mobile_card_absent_when_digest_opened` | `md:hidden` digest block not rendered when digest already opened |

### Integration tests — `test_digest_nav.py`

Use the same fixtures. Tests assert on rendered HTML of `GET /` and `GET /digest`.

| Test | What it verifies |
|---|---|
| `test_nav_link_present_when_authenticated` | "Weekly Digest" link appears in `<nav>` |
| `test_nav_link_absent_when_anonymous` | "Weekly Digest" not in nav for logged-out users |
| `test_unread_dot_present_when_unread_digest` | Amber dot `bg-amber-400` in nav when `opened_at` is null |
| `test_unread_dot_absent_when_no_digest` | No amber dot for user with no completed digest |
| `test_unread_dot_absent_after_opening_digest` | Amber dot gone from nav after visiting `/digest` |
| `test_nav_link_href_correct` | Link href is `/digest` |

### Run after each step

```bash
.venv/bin/pytest tests/recap/unit/test_digest_entry_points.py tests/recap/integration/test_digest_routes.py tests/recap/integration/test_digest_sidebar.py tests/recap/integration/test_digest_nav.py -v
```

Full suite before committing:

```bash
.venv/bin/pytest tests/ -v
```

---

## Implementation Order

Each step lists the tests to write **before** moving on. The implementation and its tests are
committed together.

1. **DB migration + model update** — add `opened_at` and `cluster_count` to `DigestRun`.
   _Tests:_ `test_opened_at_defaults_to_none`, `test_cluster_count_stored`.

2. **Config** — add `DIGEST_REGENERATE_THRESHOLD = 3` to `recap/config.py`.
   _Tests:_ `test_digest_regenerate_threshold_default`.

3. **`tasks.py` update** — populate `cluster_count` on `DigestRun` from `len(clusters)` in
   `weekly_digest_task`.
   _Tests:_ No new test needed — covered by existing `test_synthesis_nodes.py`; verify
   `cluster_count` is set in `test_digest_entry_points.py` via a DB-level assertion.

4. **Context processor** — `inject_digest_state()` in `recap/__init__.py`.
   _Tests:_ `test_has_unread_digest_*` unit tests; `test_nav_link_present_when_authenticated`,
   `test_nav_link_absent_when_anonymous`.

5. **New routes** — `digest()`, `digest_generate()`, `digest_regenerate()`, `digest_job_status()`
   in `routes.py`.
   _Tests:_ All `test_digest_routes.py` tests.

6. **Nav link** — edit `base.html`.
   _Tests:_ All `test_digest_nav.py` tests.

7. **`/digest` template** — new `recap/templates/digest.html`.
   _Tests:_ `test_digest_page_renders_digest_html`, `test_digest_page_sets_opened_at_on_first_view`,
   `test_digest_page_no_regenerate_banner_below_threshold`,
   `test_digest_page_shows_regenerate_banner_at_threshold`,
   `test_unread_dot_absent_after_opening_digest`.

8. **Sidebar card** — edit `index.html` (desktop `<aside>` + mobile block).
   _Tests:_ All `test_digest_sidebar.py` tests.

9. **Regenerate banner + JS** — wired in `digest.html` with vanilla JS polling.
   _Tests:_ `test_digest_regenerate_enqueues_job`, `test_digest_regenerate_404_on_wrong_user`.

10. **Full suite green** — run `pytest tests/ -v`, fix any regressions before committing.

---

## Files to Create or Modify

```
recap/
  config.py                       ← Add DIGEST_REGENERATE_THRESHOLD
  __init__.py                     ← Add inject_digest_state context processor
  models.py                       ← Add opened_at, cluster_count to DigestRun
  tasks.py                        ← Populate cluster_count on completion
  routes.py                       ← Add 4 new digest routes
  templates/
    base.html                     ← Add "Weekly Digest" nav link
    index.html                    ← Add sidebar digest card (all 3 states + mobile block)
    digest.html                   ← New: in-app digest viewer

migrations/versions/
  <hash>_add_digest_opened_at_cluster_count.py   ← New Alembic migration
```

---

## Design Assets

All design references are in
[`tech_design/weekly-digest-entry-points-assets/`](weekly-digest-entry-points-assets/):

- `README.md` — design spec with pixel-level markup for all states
- `Weekly Digest Entry Points.html` — browser-rendered prototype (open in Chrome to see all
  four design options, chosen direction, mobile treatments)
- `design-canvas.jsx` — React source for the prototype
- `design-system.md` — RecapAI design system reference
- `weekly_digest.html` — email template to adapt for the `/digest` page

---

## Open Questions / Deferred

- **Rate limiting on generate:** none at launch. If cost becomes a concern, add a per-user-per-day
  cap (e.g. 3/day) with a clear error message. Store count in Redis with a TTL.
- **Cluster count on old runs:** existing `DigestRun` records will have `cluster_count = NULL`.
  The sidebar card falls back to omitting the "M topics" phrase if null. No backfill needed.
- **HTMX vs vanilla JS:** the design spec calls for vanilla JS (matches existing patterns).
  HTMX would simplify the card-swap logic but is not in the stack — keep vanilla for now.
- **Admin lockdown of `/settings/digest-runs`:** out of scope for this feature but noted as
  a follow-up — see BUGS.md or a future tech design.
