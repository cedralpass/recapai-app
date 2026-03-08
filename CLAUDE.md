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
| `recap` | 8080 | Main Flask web app |
| `aiapi` | 8082 | AI/classification Flask API |
| `rq-worker` | — | Background job worker (Redis must be running) |
| `tailwind` | — | CSS watch/rebuild |
| `combined` | 8001 | Combined app entry point |

**Important:** The launch configs use `bash -c "cd /Users/geoffreysmalling/development/recapai-app && ..."` wrappers. This is required because `preview_start` does not run from the project root and the `recap` Flask module must be importable from the project root.

**Redis** must be running before starting `rq-worker`:
```bash
brew services start redis
# or: /opt/homebrew/opt/redis/bin/redis-server
```

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
