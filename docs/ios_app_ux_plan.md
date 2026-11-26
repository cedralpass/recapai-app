# Feature Plan: iOS App — Articles, Article Detail, Digest

**Status:** Steps 1–6 built (API + iOS screens, verified in the Simulator); step 7 device install pending · **Designs:** `design_handoff/Recap iOS.html` + `design_handoff/ios-README.md`
**Builds on:** the shipped iOS share extension (`ios/`, see `docs/ios_share_extension.md`)

## Goal

Make the Recap iOS app useful on its own, not just a settings screen behind the share sheet:

1. **Articles** — browse, filter and (semantically) search saved articles.
2. **Article detail** — read the AI summary and key topics, then open the original.
3. **Digest** — read the latest weekly digest and generate/regenerate it.

Keep it simple: no offline storage, no login screen (reuse the existing API token), no editing
beyond read/unread and delete.

## Non-goals (for this iteration)

- Offline cache / Core Data / SwiftData
- Username/password login or OAuth (token paste stays)
- Taxonomy organize/split, profile editing, digest email settings
- iPad-specific layouts, widgets, push notifications

---

## User stories

- As a reader, I open the app and see my most recent saves, with unread ones marked.
- I tap a category pill to narrow the list, or search "agents" and get relevant articles even if
  the word isn't in the title.
- I tap an article, skim the summary and topics, and tap **Read article** to open it — it's marked read.
- On Sunday I open the Digest tab (it has a dot), read my weekly recap, and regenerate it if I've
  saved more since.

---

## Backend: read API (`recap/api_v1.py`)

All endpoints use the existing `Authorization: Bearer <api_token>` auth (`_get_user_from_bearer_token`)
and return JSON. Reuse existing model/query helpers so web and app behave the same.

| Method & path | Purpose | Reuses |
|---|---|---|
| `GET /api/v1/articles?page=&per_page=&category=` | Paginated list, newest first | Same query as `routes.index` (user's articles, category filter) |
| `GET /api/v1/articles/search?q=&category=` | Semantic search (top 20) | `AiApiHelper.EmbedText` + `User.search_articles` (as `routes.search`) |
| `GET /api/v1/articles/<id>` | One article (404 if not the user's) | `Article` |
| `POST /api/v1/articles/<id>/read` | Set read state `{ "read": true/false }` | Logic behind `toggle-read` |
| `DELETE /api/v1/articles/<id>` | Delete article | Logic behind `routes.delete` |
| `GET /api/v1/categories` | Categories with counts for pills | `User.get_categories()` |
| `GET /api/v1/digest/latest` | Latest completed digest + banner info; marks `opened_at` | Query in `routes.digest` |
| `POST /api/v1/digest/generate` | Enqueue `weekly_digest_task` → `{job_id}` | `routes.digest_generate` |
| `GET /api/v1/digest/job/<job_id>` | Poll job status | `routes.digest_job_status` |

**Article JSON:**
```json
{
  "id": 495, "url": "https://…", "title": "…", "summary": "…",
  "author": "Andrew Ng", "category": "Artificial Intelligence",
  "key_topics": ["…"], "source": "deeplearning.ai",
  "created": "2026-11-24T18:02:11Z", "read": false,
  "summary_available": true
}
```
`summary_available` = `not article.url_only_clause()`-style check (URL-only classification).
`key_topics` is decoded from its stored JSON string.

**List response:** `{ "articles": [...], "page": 1, "has_next": true }`

**Digest response:**
```json
{
  "id": 12, "week_start": "2026-11-17", "article_count": 12, "cluster_count": 4,
  "digest_html": "<…>", "bookmarks_since": 4, "show_regenerate": true
}
```
`404 {"status": "none"}` when the user has no completed digest (app shows the empty state, with
`articles_since_last` from a cheap count so the copy can say "You've saved N articles").

**Refactor note:** shared queries now live in `recap/queries.py`, used by both `routes.py` and
`api_v1.py`. Tests: `tests/recap/integration/test_api_v1_read.py`.

**As built (details beyond the shapes above):**
- List order is `created` desc (plain newest first — unlike the web list, read articles aren't
  moved to the end). `per_page` defaults to `ARTICLES_PER_PAGE`, capped at 50.
- Search response: `{ "articles": [...], "query": "<q>" }`; a blank query or failed embedding
  returns an empty list (no text-match fallback yet).
- `POST …/read` with no `"read"` key toggles; a non-boolean `read` is a 400. Returns the article.
- `DELETE` returns `{ "status": "deleted", "id": … }`.
- Categories: `{ "categories": [{ "name", "count" }] }`, largest first, unclassified left out.
- Digest latest also returns `was_unread` (true when the digest hadn't been opened before this
  fetch) for the tab badge; `?mark_opened=false` peeks without setting `opened_at`.
- Generate returns `202 { "status": "queued", "job_id" }`. Job poll returns `{ "status": "finished" }`
  etc., and 404 `{ "status": "not_found" }` for unknown jobs or another user's job.
- Article JSON never includes `content_text`.

### Tests (`tests/`)

- Auth: every endpoint 401s without/with a bad token; can't read/modify another user's article (404).
- List pagination + category filter using the `seeded_user` / `seeded_articles` fixtures
  (e.g. AI category returns 27).
- Search with `AiApiHelper.EmbedText` mocked.
- Read toggle and delete.
- Digest: none → 404/`none`; completed digest → payload, sets `opened_at`; generate enqueues a job.

---

## iOS app (`ios/`)

### Structure

```
RecapAI/
  RecapAIApp.swift          TabView root (Articles · Digest · Settings)
  Articles/
    ArticlesView.swift      list, .searchable, category pills, infinite scroll, swipe actions
    ArticleRow.swift        card
    ArticleDetailView.swift summary, topics, "Read article" (SFSafariViewController)
  Digest/
    DigestView.swift        latest / empty / generating states, regenerate banner
    DigestWebView.swift     WKWebView wrapper rendering digest_html with injected CSS
  Settings/
    SettingsView.swift      existing settings, restyled into grouped sections
Shared/
  RecapClient.swift         + list/search/get/read/delete/categories/digest calls
  Models.swift              Codable Article, ArticlePage, Category, Digest, JobStatus
```

### Behaviour details

- `@Observable` view models per tab; async/await `URLSession`; errors shown inline with retry.
- Not configured (no token) → Articles/Digest show a "Connect Recap" empty state linking to Settings.
- Search runs on submit (embedding call per query); clearing search restores the list.
- "Read article" → mark read optimistically, then open `SFSafariViewController`.
- Digest generation polls `/digest/job/<id>` every 3 s (max ~3 min), then reloads.
- Digest tab badge: shown when latest digest exists and `opened_at` was null at fetch time.

### Design

Follow `design_handoff/ios-README.md`: native SwiftUI components with Recap tokens
(blue-500 tint, category badges, amber notices, serif digest headings).

---

## Delivery plan

| Step | Scope | Verify |
|---|---|---|
| 1 ✅ | API: articles list/detail/categories/read/delete + tests | pytest |
| 2 ✅ | API: search + digest latest/generate/job + tests | pytest |
| 3 ✅ | iOS: models + client calls, TabView shell, Settings tab | Simulator |
| 4 ✅ | iOS: Articles list, pills, search, swipe actions | Simulator vs local server (seed data via `scripts/load_test_articles.py`) |
| 5 ✅ | iOS: Article detail + Safari view + read state | Simulator |
| 6 ✅ | iOS: Digest tab (latest/empty/generating) | Simulator with a generated digest |
| 7 | Device install + docs (`docs/ios_share_extension.md`, CLAUDE.md, vision.md) | iPhone |

Steps 1–2 can ship independently (they're harmless additions to the API).

## Open questions

- Should search fall back to plain title/summary text match when the embedding call fails or is slow?
- Delete from the app: allow, or keep the app read-only for now?
- Digest regenerate threshold — reuse `DIGEST_REGENERATE_THRESHOLD` (web) as-is?
- Should `X-Recap-Client: ios-app/…` reads also update `extension_last_seen`, or only saves?
