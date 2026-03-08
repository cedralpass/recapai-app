# Chrome Extension

The RecapAI Chrome Extension lets you save any web page to your reading list with a single click, without ever leaving the browser tab.

It talks directly to the RecapAI backend via a token-authenticated REST API (`POST /api/v1/articles`), so no browser session or open RecapAI tab is required.

---

## Architecture overview

```
[Chrome Extension popup]
        │
        │  POST /api/v1/articles
        │  Authorization: Bearer <api_token>
        │  { "url": "https://..." }
        ▼
[RecapAI Flask app]
        │
        ├─ Creates Article row in DB
        └─ Enqueues recap.tasks.classify_url via RQ
                │
                ▼
        [RQ Worker → OpenAI → updates Article]
```

The extension files live at `chrome-extension/` in the repo root.

```
chrome-extension/
├── manifest.json       # Manifest V3 configuration
├── popup.html          # One-click save UI (320 px wide)
├── popup.js            # Popup logic: reads tab URL, calls API
├── options.html        # Settings form
├── options.js          # Saves/loads settings via chrome.storage.sync
├── generate_icons.py   # One-time Pillow script used to produce icons
└── icons/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

---

## Prerequisites

- Chrome browser (version 88+, Manifest V3 support)
- A running RecapAI instance (local or production)
- A RecapAI user account

---

## First-time setup

### Step 1 — Get your API token

1. Log in to your RecapAI instance.
2. Navigate to **Settings → API Token** (URL: `/settings/api-token`).
3. Your token is displayed on the page. Copy it.
   - If no token exists yet the page generates one automatically on first visit.
   - Click **Regenerate Token** to replace an existing token (the old one is immediately invalidated).

### Step 2 — Load the extension in Chrome

1. Open **`chrome://extensions`** in Chrome.
2. Enable **Developer mode** using the toggle in the top-right corner.
3. Click **Load unpacked**.
4. Navigate to and select the `chrome-extension/` folder from this repository.

The black "R" RecapAI icon will appear in your Chrome toolbar. If you don't see it, click the puzzle-piece icon (Extensions menu) and pin RecapAI Bookmarker.

### Step 3 — Configure the extension

1. Click the RecapAI toolbar icon.
2. Click the **⚙ gear icon** in the popup header
   *(or right-click the toolbar icon → **Options**)*.
3. Fill in the two fields:
   - **RecapAI Server URL** — the base URL of your instance, e.g.
     `https://your-app.onrender.com`  or  `http://localhost:8080`
     *(no trailing slash)*
   - **API Token** — paste the token you copied in Step 1.
4. Click **Save Settings**. You'll see a green "Settings saved!" confirmation.

---

## Daily usage

1. Browse to any article or page you want to save.
2. Click the **RecapAI** icon in the toolbar.
3. The popup shows the page title and URL.
4. Click **Save to Recap AI**.
5. You'll see **✅ Saved! Recap AI is classifying it.**

The article appears in your RecapAI reading list immediately. The AI worker will classify it (category, summary, author, key topics) within ~20 seconds.

---

## Error messages

| Message | Cause | Fix |
|---------|-------|-----|
| ⚠ Please configure settings | No URL or token saved | Open Options and fill in both fields |
| ❌ Invalid API token | Token rejected by server (401) | Open Options, paste a fresh token from `/settings/api-token` |
| ❌ Could not reach RecapAI | Network failure or wrong URL | Check the Server URL in Options; confirm the app is running |
| ❌ Bad request | Malformed URL sent (400) | Refresh the page and try again |
| ❌ Server error (5xx) | Server-side failure | Check the RecapAI server logs |

---

## API Token management

| Action | How |
|--------|-----|
| View your token | RecapAI → Settings → API Token |
| Regenerate token | Same page → **Regenerate Token** button |
| Update extension after regeneration | Extension Options → paste new token → Save Settings |

> **Important:** Regenerating invalidates the old token immediately. Any device or tool using the old token will start receiving 401 errors until updated.

---

## Permissions explained

The extension requests the following Chrome permissions:

| Permission | Why it's needed |
|------------|-----------------|
| `activeTab` | Read the URL and title of the current tab when you click Save. Granted only on user gesture — no persistent background access. |
| `storage` | Persist your Server URL and API token in `chrome.storage.sync` so settings sync across your Chrome profile. |
| `host_permissions: http://*/*, https://*/*` | Allow `fetch()` calls to your RecapAI server. Because the server URL is user-configured (not known at build time), broad permissions are required. The API token ensures only you can post to your account. |

---

## Updating the extension

The extension is loaded unpacked from your local repo, so any file changes take effect after reloading:

1. Make changes to files in `chrome-extension/`.
2. Go to `chrome://extensions`.
3. Click the **↺ refresh icon** on the RecapAI Bookmarker card.
4. Re-open the popup to see your changes.

---

## Regenerating icons

Icons were generated using `generate_icons.py` (requires Pillow). If you want to redesign them:

```bash
cd chrome-extension
pip install Pillow
python generate_icons.py
# outputs icons/icon16.png, icons/icon48.png, icons/icon128.png
```

Edit `generate_icons.py` to change the colour, glyph, or shape before running.

---

## Smoke-testing the API directly

You can verify the backend endpoint independently of the extension:

```bash
# Local dev
curl -X POST http://localhost:8080/api/v1/articles \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/some-article"}'

# Expected response (201)
{"article_id": 42, "status": "queued"}
```

**Common response codes:**

| Code | Meaning |
|------|---------|
| 201 | Article queued successfully |
| 400 | Missing or empty `url` field in request body |
| 401 | Token missing, invalid, or not associated with any user |
