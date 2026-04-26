# RecapAI — Claude Code Guide

## Project Overview

RecapAI is a personal reading list app. Users save articles via a web UI or Chrome Extension. An RQ background worker calls OpenAI to classify each article (category, summary, author, key topics).

**Stack:** Python 3.12 · Flask · SQLAlchemy · Flask-Login · RQ + Redis · Tailwind CSS · OpenAI API

---

## Dev Environment

**Python environment:** pyenv + `.venv/` virtual environment at the project root.
- Never call `flask`, `rq`, or `python` directly — they won't be found unless the venv is active.
- Always prefix with `.venv/bin/` or use `bash -c "cd /path && .venv/bin/..."`.

**Environment variables:** Loaded from `.env` (gitignored). Required vars include `SECRET_KEY`, `OPENAI_API_KEY`, `AI_API_SECRET_KEY`, `SQLALCHEMY_DATABASE_URI`.

**RQ workers on macOS** require:
```
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```
This is already set in the `rq-worker` launch config below.

---

## Dev Servers (`preview_start`)

The `.claude/launch.json` file is committed and ready. Use `preview_start` with these server names:

| Name | Port | What it does |
|------|------|--------------|
| `recap` | 8080 | Main Flask web app (hot-reloads on code/template changes) |
| `aiapi` | 8082 | AI/classification Flask API (hot-reloads on code changes) |
| `rq-worker` | — | Background job worker (Redis must be running) |
| `tailwind` | — | CSS watch/rebuild (recompiles on template changes) |
| `combined` | 8001 | Both apps via DispatcherMiddleware — aiapi at `/aiapi/` prefix |

**Important:** The launch configs use `bash -c "cd /Users/geoffreysmalling/development/recapai-app && ..."` wrappers. This is required because `preview_start` does not run from the project root and the `recap` Flask module must be importable from the project root.

**Redis** must be running before starting `rq-worker`:
```bash
brew services start redis
# or: /opt/homebrew/opt/redis/bin/redis-server
```

### Recommended harness for active Claude Code development

For UI/logic changes, run all four services natively — changes are visible instantly with no rebuild:
1. `preview_start("recap")` — main app at localhost:8080
2. `preview_start("aiapi")` — AI API at localhost:8082
3. `preview_start("tailwind")` — CSS auto-recompiles on template changes
4. `preview_start("rq-worker")` — background worker (after Redis is running)

The preview browser connects to `recap` at port 8080. Template edits, Python changes, and CSS changes all take effect without restarting.

**Monitoring background services (`tailwind`, `rq-worker`):**
These have no web UI. Use `preview_logs` with their server ID to check output:
- `tailwind` — shows "Done in Xms" on each CSS rebuild
- `rq-worker` — shows job start/finish/failure as articles are classified

**Stale process warning:**
If the preview browser shows a `host.docker.internal` DB error, the `recap` server was reused from a previous session with old env vars. Fix: `preview_stop` then `preview_start("recap")`.

### Environment variables

`recap/.env` is the single source of truth for local development:
```
RECAP_POSTGRES_HOST=localhost
RECAP_AI_API_URL=http://localhost:8082/
```

**Never change these values for Docker.** Pass overrides via `-e` at runtime instead.

| Variable | Local dev | Docker override |
|----------|-----------|-----------------|
| `RECAP_POSTGRES_HOST` | `localhost` | `host.docker.internal` |
| `RECAP_AI_API_URL` | `http://localhost:8082/` | `http://localhost:8000/aiapi/` |

### Use Docker only for

- Pre-deploy smoke testing (`devops/Dockerfile.full`)
- Testing `initialize_render_run.sh` startup behavior
- Simulating the Render container environment

**Local Docker run command** (for integration testing):
```bash
docker build -t recap-full . -f ./devops/Dockerfile.full
docker run --detach -p 8000:8000 \
  --add-host host.docker.internal:host-gateway \
  -e RECAP_POSTGRES_HOST=host.docker.internal \
  -e RECAP_AI_API_URL=http://localhost:8000/aiapi/ \
  recap-full
```

The preview browser cannot reach port 8000 (sandboxed to 8080). Use your regular browser for Docker testing.

See [docs/development.md](docs/development.md) for the full development strategy.

---

## Running Tests

```bash
# Source env vars first, then run pytest
AI_API_LogLevel=DEBUG AI_API_OPENAI=test AI_API_SECRET_KEY=test AI_OPEN_AI_MODEL=gpt-4 \
  .venv/bin/pytest tests/ -v
```

---

## Key Architecture

```
recap/              ← Main Flask app (web UI)
  __init__.py       ← App factory, blueprint registration, CORS, RQ setup
  models.py         ← SQLAlchemy models (User, Article)
  api_v1.py         ← REST API blueprint: POST /api/v1/articles (Bearer token auth)
  profile/          ← Profile/settings blueprint (incl. /settings/api-token)
  tasks.py          ← RQ task: classify_url (calls OpenAI)
  templates/        ← Jinja2 templates
  static/css/       ← Tailwind output.css (rebuilt by tailwind server)

aiapi/              ← Separate AI API Flask app
chrome-extension/   ← Manifest V3 Chrome Extension (no build step)
tests/              ← pytest: unit + integration
migrations/         ← Alembic migrations
```

---

## Chrome Extension

Loaded unpacked from `chrome-extension/`. No build step required.
- Token-authenticated: users get their token from `/settings/api-token`
- Calls `POST /api/v1/articles` with `Authorization: Bearer <token>`
- See `docs/chrome_extension.md` for full setup guide
