## Add google Chrome Plugin

Right now, the user has to copy and paste a URL to the form ArticleForm. It would be good to remove this friction point. I would like to build a lightweight (not too many heavy libraries) Google Chrome Extension to enable quick bookmarking. 

Here are instructions on building a Google Chrome Extension: https://developer.chrome.com/docs/extensions/get-started

would  you review and develop a plan?  can you append this file with the plan?

## Place Plan Below Here

---

## Implementation Plan

### Overview

The extension will let a logged-in RecapAI user save the current tab's URL to their reading list with one click. To keep the extension lightweight and stateless, the backend will expose a simple token-authenticated REST endpoint. The extension only needs `fetch()`, `chrome.storage`, and `chrome.tabs` — no build tools or external libraries required.

---

### Part 1 — Backend Changes (Flask / `recap/`)

#### 1.1 Add `api_token` to the User model

**File:** `recap/models.py`

Add a `api_token` column (random URL-safe string, 32 chars) to the `User` model. Generate it automatically on first use via a helper method.

```python
# in User model
api_token = db.Column(db.String(64), nullable=True, unique=True, index=True)

def get_or_create_api_token(self):
    if not self.api_token:
        import secrets
        self.api_token = secrets.token_urlsafe(32)
        db.session.commit()
    return self.api_token
```

Run a new Flask-Migrate migration after.

#### 1.2 Add a REST endpoint for article submission

**File:** `recap/routes.py`

```
POST /api/v1/articles
Authorization: Bearer <api_token>
Content-Type: application/json

{"url": "https://example.com/article"}
```

- Looks up user by `api_token` header value.
- Creates `Article` record and fires the existing `recap.tasks.classify_url` RQ task (same logic as `/add_article`).
- Returns JSON: `{"status": "queued", "article_id": <id>}` on success, `{"error": "..."}` on failure.
- No session or CSRF required — token provides authentication.
- Decorate with CORS headers allowing the extension's origin (or `*` for simplicity since it's token-gated).

#### 1.3 Add a "My API Token" page in user settings

**File:** `recap/routes.py` + new template `recap/templates/api_token.html`

```
GET /settings/api-token   → shows the user's token (masked), with a "Reveal" and "Regenerate" button
POST /settings/api-token  → regenerates the token
```

Link this page from the main nav so users can easily copy their token for the extension's options page.

---

### Part 2 — Chrome Extension

#### 2.1 Directory structure

```
chrome-extension/
├── manifest.json       # Manifest V3
├── popup.html          # One-click save UI
├── popup.js            # Reads current tab URL, calls API
├── options.html        # Settings: API base URL + token
├── options.js          # Saves/loads settings via chrome.storage.sync
└── icons/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

No build step. Plain HTML/CSS/JS only.

#### 2.2 `manifest.json` (Manifest V3)

Key fields:
```json
{
  "manifest_version": 3,
  "name": "RecapAI Bookmarker",
  "version": "1.0.0",
  "description": "Save the current page to RecapAI with one click.",
  "permissions": ["activeTab", "storage"],
  "action": {
    "default_popup": "popup.html",
    "default_icon": { "16": "icons/icon16.png", "48": "icons/icon48.png" }
  },
  "options_page": "options.html"
}
```

- `activeTab` — read the URL of the current tab on user gesture (no persistent host permissions needed).
- `storage` — persist API URL + token via `chrome.storage.sync`.
- No `host_permissions` wildcards needed; `fetch()` targets the user-configured URL.

#### 2.3 `popup.html` / `popup.js`

UI (kept minimal — no framework):
- Shows the current page title and URL (truncated).
- A single **"Save to RecapAI"** button.
- A small status area that shows "Saving…", "Saved!", or an error message.
- A gear icon linking to `options.html`.

Logic in `popup.js`:
1. On load, check `chrome.storage.sync` for `apiUrl` and `apiToken`. If missing, prompt user to open options.
2. Read current tab URL via `chrome.tabs.query({active: true, currentWindow: true})`.
3. On button click, `fetch(apiUrl + '/api/v1/articles', { method: 'POST', headers: { Authorization: 'Bearer ' + apiToken, 'Content-Type': 'application/json' }, body: JSON.stringify({ url: tabUrl }) })`.
4. Show success or error feedback inline; disable button after success to prevent double-saves.

#### 2.4 `options.html` / `options.js`

Simple form with two fields:
- **RecapAI URL** (e.g. `https://your-recapai-instance.onrender.com`)
- **API Token** (paste from the `/settings/api-token` page)

Saved to `chrome.storage.sync` on submit. Restored on page load.

---

### Part 3 — CORS

The Flask app needs to allow the extension to call the new endpoint. Chrome extensions send requests with `Origin: chrome-extension://<id>`, which differs per install.

Easiest approach: add `flask-cors` (already in Python ecosystem, small) and apply it only to the `/api/v1/` blueprint:

```python
from flask_cors import CORS
CORS(api_bp, resources={r"/api/v1/*": {"origins": "*"}})
```

Since the endpoint is already token-gated, allowing `*` origins is acceptable.

---

### Part 4 — Icons

Generate simple placeholder PNGs (16×16, 48×48, 128×128) using Python's Pillow or any image editor. A bookmark icon on a colored background works well and requires no design tool.

---

### Part 5 — Testing & Loading the Extension

1. In Chrome, navigate to `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked** → select the `chrome-extension/` folder.
4. Open Options, enter the RecapAI URL and paste the API token from `/settings/api-token`.
5. Navigate to any article, click the extension icon, click Save.
6. Verify the article appears on the RecapAI index page and gets classified.

---

### Sequencing / Work Order

| Step | Task | Files Touched |
|------|------|---------------|
| 1 | Add `api_token` to User model + migration | `models.py`, new migration |
| 2 | Add `POST /api/v1/articles` endpoint | `routes.py` |
| 3 | Add `/settings/api-token` page | `routes.py`, new template |
| 4 | Add CORS support to `/api/v1/` | `recap/__init__.py`, `requirements.txt` |
| 5 | Scaffold `chrome-extension/` directory | new directory |
| 6 | Write `manifest.json` | new file |
| 7 | Write `options.html` + `options.js` | new files |
| 8 | Write `popup.html` + `popup.js` | new files |
| 9 | Generate icons | new files |
| 10 | End-to-end test (load unpacked, save an article) | manual |

---

### Key Design Decisions

- **Manifest V3** — required for new Chrome extensions as of 2024; uses `service_worker` instead of background pages.
- **No build tooling** — keeps the extension lightweight as requested. Plain ES6 modules in the popup.
- **Token auth, not session cookies** — avoids CSRF complexity and works regardless of whether the user has the RecapAI tab open.
- **`flask-cors`** — the only new Python dependency added; it's small (~4 KB) and well-maintained.
- **`chrome.storage.sync`** — syncs extension settings across the user's Chrome profile automatically.
