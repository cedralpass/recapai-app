# RecapAI

An AI-powered article bookmarking and classification app. Paste a URL, and the app fetches the article, classifies it using OpenAI (category, summary, title, author, key topics), and organizes your reading library.

Configure Recap and AIAPI via `.env` files. See [environment documentation](docs/environments.md).

## Architecture

Two Flask services run together:
- **`recap/`** — User-facing web app (HTML/Tailwind CSS)
- **`aiapi/`** — Internal AI microservice wrapping OpenAI

## Development Setup

### Activate virtual environment
```bash
source .venv/bin/activate
```

### Initialize the database
```bash
flask --app recap init-db
```

### Run services

**recap only** (port 8080):
```bash
flask --app recap run --debug --port 8080
```

**aiapi only** (port 8082):
```bash
flask --app aiapi run --debug --port 8082
```

**Both together** (`/` → recap, `/aiapi` → aiapi):
```bash
python run.py
```
- [recap index](http://127.0.0.1:8001/)
- [aiapi hello](http://127.0.0.1:8001/aiapi/hello)

### Background worker

A worker must be running for article classification to process:
```bash
rq worker RECAP2-Classify
```

To simulate production (worker pool):
```bash
rq worker-pool RECAP2-Classify -n 1
```

### Build CSS

Tailwind CSS requires a Node process to watch for changes:
```bash
npx tailwindcss -i ./recap/static/css/input.css -o ./recap/static/css/output.css --watch
```

## Production

> Gunicorn is installed as part of the Docker build — it is **not** in `requirements.txt`.

**recap only:**
```bash
gunicorn -w 4 'recap:create_app()' -b 127.0.0.1:8080 --access-logfile=gunicorn.http.log --error-logfile=gunicorn.error.log
```

**aiapi only:**
```bash
gunicorn -w 4 'aiapi:create_app()' -b 127.0.0.1:8080 --access-logfile=gunicorn.http.log --error-logfile=gunicorn.error.log
```

**Both together (Render production):**
```bash
gunicorn -w 3 -b 0.0.0.0:8000 app --log-level debug --timeout 90
```

**Run as daemon:**
```bash
gunicorn -w 4 'app' -b 127.0.0.1:8080 --access-logfile=gunicorn.http.log --error-logfile=gunicorn.error.log --daemon
```

**Kill gunicorn:**
```bash
ps -ef | grep gunicorn
kill -9 <pid>
```

[Gunicorn settings reference](https://docs.gunicorn.org/en/stable/settings.html)

## Docker — Fully Contained Container

Run Recap, AIAPI, and Redis in a single container for local testing or demos.

**Build:**
```bash
docker build -t recap-full . -f Dockerfile.full
```

**Run:**
```bash
docker run --detach -p 8000:8000 -t recap-full
```

**Stop:**
```bash
docker ps                          # find container id
docker stop <container_id>
```

## Deploy to Render

The app is hosted on [Render](https://render.com). Services are deployed as Docker images pulled from GitHub Container Registry (`ghcr.io/cedralpass/`).

**Build and push image:**
```bash
sh ./devops/build_for_render.sh
```

**Services defined in `render.yaml`:**
- `recap-full` — main web app (recap + aiapi + workers)
- `recap-aiapi` — standalone aiapi service
- `recaprai-redis-dev` — managed Redis instance

See [devops/render_hosting.md](devops/render_hosting.md) for Render setup details.


## Chrome Extension

The `chrome-extension/` directory contains a Manifest V3 Chrome Extension that lets you save any page to RecapAI with a single click — no copy/paste required.

### First-time setup

**1. Get your API token**

Log in to RecapAI and navigate to **Settings → API Token** (`/settings/api-token`). Copy the token shown on the page (or click **Regenerate** to create a fresh one).

**2. Load the extension in Chrome**

1. Open `chrome://extensions` in Chrome.
2. Enable **Developer mode** (toggle in the top-right corner).
3. Click **Load unpacked**.
4. Select the `chrome-extension/` folder from this repository.

The RecapAI icon (black "R") will appear in your Chrome toolbar.

**3. Configure the extension**

1. Click the RecapAI icon, then click the **⚙ gear icon** (or right-click the toolbar icon → **Options**).
2. Enter your **RecapAI Server URL** — e.g. `https://your-app.onrender.com` (no trailing slash).
3. Paste your **API Token** from step 1.
4. Click **Save Settings**.

### Saving an article

1. Browse to any article or page you want to save.
2. Click the RecapAI toolbar icon.
3. Click **Save to Recap AI**.
4. You'll see ✅ **Saved! Recap AI is classifying it.** — the article will appear in your reading list within ~20 seconds once the AI worker processes it.

### API Token management

| Action | Where |
|--------|-------|
| View your token | RecapAI → Settings → API Token |
| Regenerate token | Same page → **Regenerate Token** button |
| Update extension after regeneration | Extension Options → paste new token → Save |

> **Note:** Regenerating your token immediately invalidates the old one. Update the extension options page with the new token to restore functionality.

### Smoke-test the API directly

```bash
curl -X POST http://localhost:8080/api/v1/articles \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.sabrina.dev/p/claude-code-full-course-for-beginners"}'
```