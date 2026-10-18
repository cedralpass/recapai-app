# Extension Content Capture — Tech Design

## Build Status

| Phase | Scope | Status |
|---|---|---|
| 0 | Readable titles for blocked articles (URL slug → title) | Built |
| 1 | Store article text; accept HTML via API; save the same URL again → update | Built |
| 2 | Chrome extension captures page HTML | Planned |
| 3 | Promote the extension on blocked articles | Planned |
| — | Extra sources (paste text, Medium RSS, Wayback) | Deferred: later task, see [below](#deferred--other-ways-to-get-the-text) |

---

## Problem

Sites like Medium return **HTTP 403** to our server-side fetch. When that happens,
`fetch_article_content` ([recap/aiapi_helper.py](../recap/aiapi_helper.py)) returns `SITE_BLOCKED`
and `classify_url` ([recap/tasks.py](../recap/tasks.py)) writes placeholder data:

- **title:** `Medium Blocked – https://medium.com/blogflyer/12-claude-code-techniques-that-make-ai-coding-feel-more-like-engineering-3f1ab92cc301`
- **summary:** `Bot Blocked – Classifying by URL Only`
- **author:** `Unknown`

The article is effectively lost. It has no useful summary or topics, and its embedding is weak, so
search and the digest both degrade. Reclassifying doesn't help because it hits the same 403.

Other problems in the same code path:

1. **Two fetches.** When recap gets a 403 it sends no `content`, so aiapi's fallback
   `fetch_article_content` ([aiapi/classify.py](../aiapi/classify.py)) fetches the same URL again
   and gets blocked again.
2. **Duplicate articles.** `POST /api/v1/articles` and the index form always insert a new `Article`,
   so saving the same URL twice creates two rows.
3. **Article text is thrown away.** The extracted text is used once for classification and never
   stored.

## Goal

Get the article text from the **user's own browser**, which can already read the page (including
paywalled articles for logged-in members). Store it with the article and classify that stored text
instead of crawling. When an article is still blocked, show a clear fix: *save it with the
extension*.

---

## Phase 0 — Readable titles for blocked articles (ship on its own)

### Slug → title

New helper in `recap/aiapi_helper.py` (next to `_site_name_from_url`):

```python
_TRAILING_ID = re.compile(r"[-_](?:[0-9a-f]{8,16}|\d{4,})$")   # medium hex ids, numeric post ids
_FILE_EXT = re.compile(r"\.(?:html?|php|aspx?)$", re.IGNORECASE)


def title_from_url(url):
    """Turn a URL slug into a human-readable title, or None if the slug is not descriptive.

    medium.com/blogflyer/12-claude-code-techniques-...-engineering-3f1ab92cc301
      → '12 claude code techniques that make ai coding feel more like engineering'
    """
    path = urlparse(url).path.rstrip("/")
    slug = _FILE_EXT.sub("", path.rsplit("/", 1)[-1])
    slug = _TRAILING_ID.sub("", slug)
    words = [w for w in re.split(r"[-_+]+", slug) if w]
    if len(words) < 3:          # 'p/abc', '/2024/', etc. — not a real title
        return None
    return " ".join(words)
```

### Let the model write the title and summary

The URL-only prompt already returns a `blog_title` and `summary`. Today `classify_url` overwrites
them with placeholder text. Instead:

- Send the slug title to aiapi as a **`title_hint`** form field. The URL-only branch of
  `build_prompt` adds: *"The URL slug suggests the title: '{hint}'. Use it to infer intent and
  fix the capitalization (e.g. 'ai' → 'AI')."* This gives classification a real signal: *"12 Claude
  Code Techniques…"* clearly belongs in *AI Tools / Software Engineering*.
- **Keep the model's `blog_title`.** Fall back to `title_from_url(url).title()` if the model returns
  `Unknown`, and to the current `"{Site} Blocked – {url}"` only if both fail.
- **Keep the model's summary** and mark the article as URL-only with a new `fetch_status` value
  (Phase 1), not by replacing the summary. Until Phase 1 lands, prefix the summary with
  `"[From URL only] "`.

### Remove the second fetch

Add a `skip_fetch=1` form field. `AiApiHelper.ClassifyUrl` sets it when recap's fetch returned
blocked or down, and aiapi's `classify_url` skips its fallback fetch when it's present. An empty
extraction (`None`) doesn't set it, because `None` can also mean readability isn't installed on
the recap side, so aiapi still gets a chance. Once Phase 1 lands, it's also set whenever stored
content exists.

### "Summary not available" notice

`Article.url_only_reason` (`'blocked'` / `'down'` / `None`) reads the summary prefix, including
the old placeholder summaries. When it's set, the index card and search results show
*"Summary not available — Medium is blocking our crawler."* (or *"… couldn't be reached."*)
instead of the summary (`templates/_url_only_notice.html`). The detail page shows the same notice
in a blue info box, with the model's guess underneath labeled *"Guess from the link:"*. Phase 3
adds the extension prompt to this notice instead of adding a second one.

### Repairing existing blocked articles

When a fetch fails, `classify_url` keeps an article's existing classification, unless that
classification is itself a URL-only placeholder (the old `Bot Blocked – …` / `Site Down – …`
summaries, or the new `[URL only – …]` prefix). Running **Settings → Reclassify** on old
`Medium Blocked – <url>` articles therefore replaces them with the better URL-based title.

The Reclassify page has a **Needs attention** filter (`?show=attention`, using
`Article.url_only_clause()`). It lists URL-only articles, each with a "Blocked — summary from URL
only" badge, plus articles that never finished classifying.

Reclassify jobs now pass `article_id`, and `classify_url` looks the article up by ID. Before this,
the job looked the article up by URL, which returns the newest row, so reclassifying one copy of a
URL saved twice updated the other copy. This part of the Phase 1 `classify_url` changes shipped
early. Stopping duplicates from being created is still Phase 1 (upsert).

**Files:** `recap/aiapi_helper.py`, `recap/tasks.py`, `aiapi/classify.py`

---

## Phase 1 — Store article text

### Data model

New `Article` columns (one Alembic migration):

| Column | Type | Notes |
|---|---|---|
| `content_text` | `Text`, nullable | Extracted plain text. Capped at 100k characters; classification still sends only the first 12k |
| `content_source` | `String(20)`, nullable | `crawl` · `extension` · `url_only` (a later `paste` value is possible; see Deferred) |
| `fetch_status` | `String(20)`, nullable | `ok` · `blocked` · `down` · `empty` (result of the last server fetch) |

**Backfill:** set `fetch_status='blocked', content_source='url_only'` where
`summary = 'Bot Blocked – Classifying by URL Only'`. Do the same with `down` for the site-down
placeholder. That lets the Phase 3 prompt appear on existing articles.

`content_text` is **private**. It never appears in shared views, exports to other users, or API
responses (see *Sharing policy* below).

### One shared text extractor

Move the readability steps (HTML → text) out of `fetch_article_content` into:

```python
def extract_article_text(html, max_chars=100_000):
    """Readability-extract main article text from raw HTML. Returns str or None."""
```

`fetch_article_content` calls it after a successful fetch. The API calls it on HTML uploaded by
the extension. Both paths share one implementation and one set of tests.

### URL normalization + upsert

Medium and other sites add tracking parameters (`?source=…`, `utm_*`, `fbclid`, `gi=`). Without
normalization, the same article saved twice looks like two different URLs, and long query strings
can exceed `url_path`'s 255 characters.

```python
def normalize_url(url):
    """Drop fragments and tracking params (utm_*, source, fbclid, gclid, gi, sk)."""
```

New `Article.upsert_for_user(url, user)`. It looks up the article by user and normalized URL and
returns `(article, created)`. Both `POST /api/v1/articles` and the index form use it:

- **New URL:** insert it, as today.
- **Existing URL, new content uploaded:** replace `content_text` and set
  `content_source='extension'`. Reclassify the article, even if it was already classified, because
  the new text is better.
- **Existing URL, no content:** no duplicate row. Flash *"That article is already in your list."*
  (form) or return `200 {"status": "exists"}` (API).

URLs longer than 255 characters after normalization are rejected (`400` from the API, a flash
from the form) instead of failing in the database.

### API changes — `POST /api/v1/articles`

```
Body (JSON): {"url": "https://...", "html": "<!doctype html>..."}   # html optional
Header:      X-Recap-Client: chrome-extension/1.1.0                 # optional
```

- Reject request bodies larger than **5 MB** (check `request.content_length` in the route so the
  rest of the app keeps its limits). Medium pages are usually 0.5–1.5 MB.
- If `html` is present, call `extract_article_text(html)`. On success, store it with
  `content_source='extension'`. If extraction finds no text, fall back to the normal crawl.
- Response gains `"content_captured": true|false`, so the popup can tell the user whether the full
  text was saved. Status codes: `201 queued` (new article), `200 updated` (existing article, new
  text, reclassified), `200 exists` (existing article, nothing new, no job). `content_text` is
  never included in the response.
- The current popup (v1.0) was updated to treat both `200` responses as success, so re-saving an
  existing article doesn't show an error before Phase 2 ships.
- When `X-Recap-Client` is present, set `User.extension_last_seen = now()` (new nullable `DateTime`
  column). Phase 3 uses it to tailor the message.

Extraction runs inside the request: readability on about 1 MB takes ~100 ms. Raw HTML is never
stored.

### `classify_url` changes

- ~~Accept `article_id` and look the article up by ID~~ — done in Phase 0 (all four enqueue sites
  pass it; `url` lookup kept for jobs queued before the change).
- If `article.content_text` exists, send it as `content` (first 12k characters) with `skip_fetch=1`
  and **don't crawl**. `AiApiHelper.ClassifyUrl(..., content=...)` handles this; a successful crawl
  returns its text under `fetched_content`, which `classify_url` stores and removes from the RQ job
  result. If aiapi fails, no text is returned (the result stays `{}`), and a retry crawls again.
- Otherwise crawl as today. On success, store `content_text` with `content_source='crawl'` and
  `fetch_status='ok'`. On a 403 or outage, set `fetch_status` and `content_source='url_only'` and
  apply the Phase 0 behavior.
- Embeddings: `build_article_text` stays the same for now. Adding the first ~2k characters of
  `content_text` is a good follow-up, but it changes vector search results, so it gets its own
  evaluation.

**Files:** `recap/models.py`, new migration, `recap/aiapi_helper.py`, `recap/api_v1.py`,
`recap/routes.py`, `recap/tasks.py`, `recap/profile/__init__.py` (the reclassify enqueue passes
`article_id`)

---

## Phase 2 — Chrome extension captures the page

### `manifest.json`

```json
"version": "1.1.0",
"permissions": ["activeTab", "storage", "scripting"]
```

`host_permissions` already covers `http(s)://*/*`. `scripting` doesn't add an install warning.

### `popup.js` — Save handler

```js
async function capturePageHtml(tabId) {
  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => document.documentElement.outerHTML,
    });
    return result && result.length <= 5_000_000 ? result : null;
  } catch (_) {
    return null;   // chrome://, Web Store, PDF viewer, etc. — fall back to URL-only save
  }
}

// in the save click handler
const html = await capturePageHtml(tabId);
body: JSON.stringify(html ? { url: tabUrl, html } : { url: tabUrl }),
headers: { ..., 'X-Recap-Client': `chrome-extension/${chrome.runtime.getManifest().version}` },
```

Popup states:

- `201` with `content_captured: true`: **"✅ Saved with full text — Recap AI is summarizing it."**
- `201` with `content_captured: false`: **"✅ Saved. Recap AI is classifying it."** (same as today)
- `200` with `status: exists`, content captured: **"✅ Updated with full text — re-summarizing."**

Capturing the HTML the user sees means the extension also gets past Cloudflare challenge pages
(the user has already passed them), sites that require login, and Medium member-only articles.

**Files:** `chrome-extension/manifest.json`, `chrome-extension/popup.js`, `docs/chrome_extension.md`

---

## Phase 3 — Promote the extension on blocked articles

### Article card (`_article.html`) and detail page (`article/show.html`)

When `article.fetch_status == 'blocked'` and `article.content_source != 'extension'`, replace the
plain summary styling with a callout. Use an info/notice pattern from
[docs/design-system.md](../docs/design-system.md), not error red.

| User state | Message |
|---|---|
| `extension_last_seen` is null | **Medium blocks automatic reading.** This summary is a guess based on the URL. *Install the RecapAI Chrome extension* to save the full article. → link to `/settings/api-token` (setup guide) |
| Extension seen | **Medium blocks automatic reading.** Open the article and click the RecapAI button. Your summary will update in place. → link to the article URL |
| `fetch_status == 'down'` | (no extension prompt) *"Site was unreachable — try Reclassify later."* |

Because of the Phase 1 upsert, the second message completes the loop: the user opens the article,
clicks the extension, and the existing card updates in place without creating a duplicate.

### Warn at save time

Keep a Redis set `blocked_domains` and add a domain each time a fetch returns 403. When the index
form saves a URL from a domain in that set, flash: *"Heads up: medium.com blocks automatic reading.
Save from the Chrome extension for a full summary."* The user sees the tip while they still have
the page open.

### Measuring it

Log `content_source` on every classification. Track
`count(fetch_status='blocked' AND content_source='url_only')` per user over time. That number
should go down as users adopt the extension.

**Files:** `recap/templates/_article.html`, `recap/templates/article/show.html`, `recap/routes.py`,
`recap/tasks.py`

---

## Deferred — Other ways to get the text

> **Not part of this project. Saved for a later task.** To keep things simple for users, the
> Chrome extension is the only fix we offer for blocked sites. Users get one clear message
> ("save it with the extension") instead of several choices. Revisit after Phases 0–3 ship and we
> can see how many articles stay blocked.

The extension covers Chrome desktop. The options below would cover everything else, from most to
least recommended:

| Approach | Covers | Recommendation |
|---|---|---|
| **Paste text** on the article page ("Paste article text" textarea → `content_source='paste'`) | Any browser, mobile, PDFs | ✅ Cheap, universal, uses the Phase 1 path |
| **iOS share extension** with a Safari JavaScript preprocessing file (`NSExtensionJavaScriptPreprocessingFile` gives the page DOM) | iPhone/iPad | ✅ Same model as Chrome; already on the vision roadmap |
| **Medium RSS** (`medium.com/feed/@user` / `/feed/<publication>`) — find the post by URL, use `content:encoded` | Recent public Medium posts | ✅ Official feed; good server-side fallback for the most common blocked site. Not available for member-only posts or older posts |
| **Wayback Machine** availability API (`archive.org/wayback/available?url=`) | Older public pages already archived | ⚠️ OK for public pages; often has nothing for new posts. Don't use it to get around paywalls |
| **Third-party reader APIs** (Jina Reader, Diffbot, Firecrawl) | Most public sites | ⚠️ Costs money per call and sends user URLs to a third party; these services get around blocks with proxies and headless browsers, so we take on their ToS risk |
| **Headless browser on our server** (Playwright) | Some JS-heavy sites | ❌ Heavy container; Cloudflare still blocks data-center IPs |
| **Spoofed browser User-Agent, residential proxies, CAPTCHA solvers** | — | ❌ Deliberately getting around a site's access controls; ToS and legal risk, and fragile |

**When this is picked up:** start with the paste box and the Medium RSS fallback. The iOS share
extension is already its own roadmap item. Skip the evasion techniques.

Also: our User-Agent `Recap/1.0 (article bookmarking service)` is honest. Adding a contact URL
(`Recap/1.0 (+https://<app-domain>/bot)`) is good practice and lets site owners allowlist us.

---

## Sharing policy (for the future Social & Sharing feature)

**Sharing title + AI summary + link is allowed. Sharing `content_text` is not.**

A shared item looks like a link-aggregator post: it promotes the original article and sends
readers to it. To keep it that way:

1. **What gets shared:** `title`, `author_name`, `category`, `key_topics`, AI `summary`, and
   `url_path`, with UTM parameters as in the digest (`utm_source=recap&utm_medium=share`).
2. **What never gets shared:** `content_text`. Enforce this in the serializer/view layer with an
   allowlist of fields, not a blocklist, and add a test that asserts it's missing from every shared
   surface.
3. **Keep summaries short and useful as a preview,** not a replacement for the article. The
   classify prompt already asks for "a short summary" with `max_tokens=512`. Add an explicit limit
   (≤ 60 words, no verbatim passages longer than one sentence). This matters most for paywalled
   content, where a detailed summary could stand in for paying.
4. **Label it** "AI-generated summary," and make the source link the most prominent element.
5. **Start with private sharing** (friends/family who are logged in). Hold off on public, indexable
   share pages. Publicly indexed summaries of paywalled articles carry the most risk.
6. **Takedown path:** a way for a rights holder to request removal, and the ability to exclude a
   domain from sharing.

This isn't legal advice. Get a quick legal review before public sharing launches.

---

## Testing

| Area | Tests |
|---|---|
| `title_from_url` | Medium slug + hex ID, numeric IDs, `.html` suffix, short/opaque slugs → `None` |
| `normalize_url` | Strips `utm_*`/`source`/`fbclid`/fragment; keeps meaningful query params |
| `extract_article_text` | `tests/fixtures/flask_tutorial_part1.html` → expected text; empty/garbage HTML → `None` |
| API | `html` present → `content_captured: true`, `content_source='extension'`; body > 5 MB → 413; same URL again → updated, not duplicated; `X-Recap-Client` sets `extension_last_seen` |
| `classify_url` | Stored content → **no outbound fetch** (respx asserts zero calls) and `skip_fetch=1` sent; 403 → `fetch_status='blocked'`, model title kept, slug fallback used when model says `Unknown` |
| aiapi | `skip_fetch=1` → `fetch_article_content` not called; `title_hint` appears in the URL-only prompt |
| Templates | Blocked + no extension → install message; blocked + extension seen → "click the button" message; extension-sourced → no message |
| Sharing (later) | `content_text` missing from every shared response |

Record a real Medium fixture by saving the page from Chrome ("Save page as → HTML only") into
`tests/fixtures/medium_claude_code_techniques.html`. Our server can't fetch it, which is the whole
problem.

---

## Out of scope

- Paste-text box, Medium RSS fallback, Wayback Machine lookups (deferred; see above)
- Saving raw HTML, images, or a reader-mode view of the article
- Firefox/Safari desktop extensions
- Using `content_text` for embeddings or digest synthesis (follow-ups; both need evaluation)
- Detecting Cloudflare challenge pages that return HTTP 200 server-side (the extension avoids the
  problem)
- Public share pages

## Open questions

1. **Retention:** should `content_text` be deleted after N days, or kept for future re-summarizing
   and search? Proposal: keep it. It's private, and it powers reclassification.
2. **Extension distribution:** the extension is currently loaded unpacked. The prompt in Phase 3
  is much more effective with a Chrome Web Store link. Should it be published to the store?
3. **Storage cost:** ~100k characters × articles per user. Fine on Postgres at current scale; check
   again if users reach thousands of articles.
