# Handoff: Weekly Digest — In-App Entry Points

## Overview

The Recap AI email digest is well-received, but email is a passive channel. This work
introduces in-app surfaces so users can reach the Weekly Digest from anywhere in the
product, see when a fresh one is ready, generate one on demand if no digest exists yet,
and regenerate a stale digest when they've added meaningful new bookmarks since it was
created.

The chosen direction (Option E / "★ A + Sidebar" in the design canvas) is intentionally
restrained: it adds the digest to the top nav and surfaces freshness via a single
sidebar card. The home page's primary jobs — saving a URL and reviewing bookmarks —
are unchanged.

## About the Design Files

The files in this bundle are **design references created in HTML** — prototypes showing
intended look and behavior, not production code to copy directly. The task is to
**recreate these designs in the existing RecapAI codebase** (Flask + Jinja2 + Tailwind
CSS, per `design-system.md`) using its established patterns:

- Server-rendered Jinja2 templates
- Utility-first Tailwind (no custom theme extension)
- Vanilla JS for any client-side behavior (no framework)
- Inline SVGs in Heroicons outline style

Do **not** import the React/JSX prototype directly. Use it as a visual + interaction
reference.

## Fidelity

**High-fidelity.** Colors, spacing, typography, copy, and interactions are final.
Match the prototype pixel-perfectly using existing Tailwind utility classes from the
RecapAI design system. Where a value falls outside Tailwind defaults, the spec calls it
out explicitly.

---

## Screens / Views

### 1. Top nav — new "Weekly Digest" link

**Location:** Inserted into the global nav (`base.html`) between "Home" and "Profile",
for authenticated users only.

**Markup pattern (matches existing nav links):**
```html
<a class="relative inline-flex items-center gap-1.5 font-medium text-slate-200 underline hover:no-underline"
   href="{{ url_for('main.digest') }}">
  Weekly Digest
  {% if has_unread_digest %}
  <span class="w-1.5 h-1.5 rounded-full bg-amber-400 ring-2 ring-black" aria-label="New digest"></span>
  {% endif %}
</a>
```

- Unread dot: 6×6px (`w-1.5 h-1.5`), `bg-amber-400` (#fbbf24), 2px black ring so it
  punches off the black nav.
- "Unread" = a digest exists for the most recent week and `digest.opened_at` is null.

### 2. Home (authenticated) — sidebar slot

The right-hand category sidebar gains a **new card slotted above** the "Filter by category"
list. There are **two states**.

#### 2a · Sidebar card — FRESH state (digest exists, not yet opened)

**Container:** `bg-slate-900 rounded-lg p-4 mb-5 text-white`

```html
<div class="bg-slate-900 rounded-lg p-4 mb-5 text-white">
  <div class="text-[10px] font-bold tracking-[0.16em] uppercase text-amber-400 mb-2">
    This Week · Recap
  </div>
  <div class="font-serif text-lg font-bold leading-tight mb-1.5">
    {{ digest.article_count }} articles, {{ digest.cluster_count }} topics
  </div>
  <div class="font-serif italic text-[13px] text-slate-300 leading-relaxed mb-3">
    Your Monday digest is ready.
  </div>
  <a href="{{ url_for('main.digest') }}"
     class="inline-block text-[13px] font-bold text-white no-underline border-b-2 border-amber-400 pb-0.5">
    Read digest →
  </a>
</div>
```

- `font-serif` here means Georgia stack — matches the email digest typography.
  In Tailwind this is the default `font-serif`. If the existing app doesn't use serif
  anywhere else, add inline `style="font-family: Georgia, 'Times New Roman', serif"`
  on the headline + tagline only.
- Accent color: amber-400 (#fbbf24) for the eyebrow and the underline beneath the link.
- The "Read digest" link is a CTA — keep the underline rendered as a 2px border
  under just the text, not the global `underline` rule.

#### 2b · Sidebar card — EMPTY state (no digest yet)

Shown to users who haven't received their first weekly email (typically week one), or
after they've opened the most recent digest and there's nothing new to surface.

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
  <button type="button"
          class="w-full bg-slate-900 text-white border-none rounded-md py-2.5 px-3 text-[13px] font-bold cursor-pointer flex items-center justify-center gap-1.5"
          hx-post="{{ url_for('main.digest_generate') }}">
    <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4"/>
    </svg>
    Generate recap now
  </button>
  <div class="text-[11px] text-slate-400 mt-2 text-center">Takes ~30 seconds</div>
</div>
```

#### 2c · Sidebar card — GENERATING state (after click)

Shown in place of the empty card while the digest is being built (existing classification
polling pattern applies — poll `/digest/job/<id>` until status is `finished`).

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
    <div class="h-full bg-slate-900" style="width: 64%; transition: width 500ms ease"></div>
  </div>
  <div class="text-[11px] text-slate-400 mt-2 text-center">~12 seconds remaining</div>
</div>
```

### 3. Digest page (`/digest`) — in-app view of the weekly digest

A new route that renders the same content as the email digest. **Reuse the email
template's structure** — masthead, eyebrow, italic tagline, cluster sections — to
preserve the editorial feel. Wrap it in the standard app shell (nav, page background
`bg-stone-50` / #faf8f3 to match the email cream tone, container).

The page header gets one new element: a **regenerate banner**.

#### 3a · Regenerate banner

Shown at the top of the digest page **only when** `bookmarks_since_digest_generated_at >= 3`.

```html
<div class="bg-amber-50 border-b border-amber-300 px-7 py-3.5 flex items-center justify-between gap-4">
  <div class="flex items-center gap-2.5 min-w-0">
    <svg class="h-4.5 w-4.5 text-amber-700 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>
    </svg>
    <div class="text-[13.5px] text-amber-900 leading-snug">
      <b>{{ new_bookmark_count }} new bookmarks</b> since this digest was generated.
      Regenerate to include them.
    </div>
  </div>
  <button class="bg-slate-900 text-white rounded-md py-2 px-3.5 font-bold text-[13px] inline-flex items-center gap-1.5 whitespace-nowrap"
          hx-post="{{ url_for('main.digest_regenerate', digest_id=digest.id) }}">
    <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 12a9 9 0 11-3-6.7L21 8"/><path d="M21 3v5h-5"/>
    </svg>
    Regenerate
  </button>
</div>
```

### 4. Mobile — 390px breakpoint

Sidebar collapses, so the digest card moves to the **bottom of the article list** rather
than competing with the bookmarks for above-the-fold attention. Nav link with the unread
dot remains visible in the compact mobile nav.

The mobile filter UI (existing pattern) is unchanged: an "All ▽" button next to "Your
bookmarks" opens a bottom-sheet category list. This handoff does not modify that.

Conditional rendering rules on mobile:
- **Fresh digest** → show the dark card at the end of the bookmark list.
- **No digest yet** → show the dashed empty card at the end of the bookmark list.
- **Already opened, nothing new** → hide the card entirely; the nav link carries it.

---

## Interactions & Behavior

### Click flows

| User action | Behavior |
|---|---|
| Click "Weekly Digest" in nav | Navigate to `/digest` (server-rendered). |
| Click "Read digest →" on fresh card | Navigate to `/digest`. |
| Click "Generate recap now" on empty card | POST to `/digest/generate`; swap card to GENERATING state; poll job status. |
| Click "Regenerate" on digest page banner | POST to `/digest/<id>/regenerate`; show inline progress; reload page when done. |

### Polling

Reuse the existing article-classification polling pattern (500ms interval, vanilla JS).
On status `finished`, navigate to the digest page (or update the card in place on the
sidebar if we want to keep the user on home).

### Unread state

A digest is "unread" until the user opens `/digest`. Opening should:
1. Set `digest.opened_at = now()` on the latest digest.
2. Remove the amber dot from the nav link on next render.
3. Cause the fresh sidebar card to stop rendering (it's been seen).

### Regenerate threshold

The amber banner on the digest page renders only when **3 or more bookmarks have been
saved since `digest.generated_at`**. Tunable — store as a constant in
`config.py`:

```python
DIGEST_REGENERATE_THRESHOLD = 3
```

### Rate limiting

**None at launch.** Add later if generation cost becomes a problem. When added, prefer
a per-user-per-day cap (e.g. 3/day) with a clear error message returned in the response.

---

## State Management

Server-side, per user:

| Field | Type | Notes |
|---|---|---|
| `digest.id` | int | The latest weekly digest record. |
| `digest.generated_at` | datetime | When it was generated. |
| `digest.opened_at` | datetime or null | First time the user opened `/digest`. |
| `digest.article_count` | int | For the sidebar card teaser. |
| `digest.cluster_count` | int | For the sidebar card teaser. |

Derived for the home template:
- `has_unread_digest` = digest exists AND `opened_at` is null.
- `bookmarks_since_digest` = count of `Article` where `created_at > digest.generated_at`.
- `show_regenerate_banner` = `bookmarks_since_digest >= DIGEST_REGENERATE_THRESHOLD`.
- `recent_bookmark_count` (for empty state) = count of unread bookmarks, capped at, say, 25.

Routes to add:
- `GET /digest` — render latest digest. Mark `opened_at` if first view.
- `POST /digest/generate` — kick off on-demand generation. Returns a job id.
- `POST /digest/<id>/regenerate` — same, but tied to an existing digest record.
- `GET /digest/job/<job_id>` — status poller.

---

## Design Tokens

### Colors

| Role | Hex | Tailwind |
|---|---|---|
| Card fresh BG | #0f172a | `bg-slate-900` |
| Card fresh eyebrow + accent | #fbbf24 | `text-amber-400` / `border-amber-400` |
| Card fresh body text | #cbd5e1 | `text-slate-300` |
| Card empty BG | #ffffff | `bg-white` |
| Card empty border | #cbd5e1 dashed | `border border-dashed border-slate-300` |
| Card empty eyebrow | #64748b | `text-slate-500` |
| Card empty body | #475569 | `text-slate-600` |
| Card empty CTA | #0f172a / white | `bg-slate-900 text-white` |
| Regenerate banner BG | #fffbeb | `bg-amber-50` |
| Regenerate banner border | #fcd34d | `border-amber-300` |
| Regenerate banner text | #78350f | `text-amber-900` |
| Regenerate banner icon | #b45309 | `text-amber-700` |
| Digest page page BG | #faf8f3 (cream, matches email) | `bg-stone-50` (closest) or inline |

### Typography

- Sans body: existing system stack (Tailwind `font-sans` default).
- Serif (used only inside the digest card headlines/taglines and the digest page masthead):
  Georgia, "Times New Roman", serif. Apply inline if Tailwind's `font-serif` differs.
- Eyebrow style: 10–11px, weight 700, `tracking-[0.16em]` uppercase.

### Spacing

Stick to Tailwind's 4px scale already in use across the app. The only arbitrary values
are the eyebrow letter-spacing (`tracking-[0.16em]`) and the small text sizes
(`text-[10px]`, `text-[13px]`).

### Border radius

- Sidebar card: `rounded-lg` (8px) — matches existing detail-page sidebar.
- Regenerate banner button: `rounded-md` (6px).

---

## Assets

No raster assets. All icons are inline SVGs in the Heroicons outline style already used
across the app (sparkle/sun, info circle, refresh-cw). SVG paths are embedded in the
template snippets above.

---

## Files in this handoff

- `Weekly Digest Entry Points.html` — the master design prototype (React/JSX, browser-rendered).
  Open it to see all four options (A/B/C/D), the chosen direction with both sidebar
  states, the mobile treatments, and the in-app digest page with regenerate banner.
- `design-system.md` — the existing RecapAI design system reference. **Read this first.**
  All new components should follow its conventions.
- `weekly_digest.html` — the existing email digest template. The new `/digest` page
  should preserve this editorial feel.
- `README.md` — this document.

## Implementation order (suggested)

1. **Backend first.** Add the four new routes and the `digest.opened_at` migration.
2. **Nav link.** Smallest change, immediately useful.
3. **Digest page** at `/digest`. Adapt the email template to live inside the app shell.
4. **Sidebar card — fresh state.** Wire to `has_unread_digest`.
5. **Sidebar card — empty + generating states.** Wire to on-demand generation.
6. **Regenerate banner** on the digest page. Gate on the 3+ threshold.
7. **Mobile** — verify the card slides to the bottom of the list; QA the nav link.

---

*Generated from the design canvas at `Weekly Digest Entry Points.html`.*
