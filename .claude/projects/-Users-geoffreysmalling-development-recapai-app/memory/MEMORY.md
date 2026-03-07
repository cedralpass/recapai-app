# RecapAI App — Codebase Memory

## What It Does
RecapAI is an AI-powered article bookmarking and classification web app. Users paste URLs of blog posts/articles; the app fetches and classifies them using OpenAI (category, summary, title, author, key topics, sub-categories). Users can browse their saved articles by category and use AI to reorganize their taxonomy.

## Architecture: Two Flask Services

### 1. `recap/` — Main Web App (port 8080 or 8001)
- User-facing Flask app (HTML/Tailwind CSS UI)
- Blueprints: `routes` (main), `auth` (`/auth`), `profile` (`/user`, `/edit_profile`, `/organize_taxonomy`)
- Submits classification jobs to Redis Queue (RQ), does NOT call OpenAI directly
- Calls `aiapi` via HTTP through `AiApiHelper`

### 2. `aiapi/` — Internal AI API Service (port 8082 or 8001/aiapi)
- Internal Flask microservice wrapping OpenAI
- Blueprints: `classify` (`/classify_url`), `task_processor` (`/process_task`)
- Secured with a shared `secret` key in POST form data (not OAuth)
- Uses OpenAI `gpt-*` model from `AIAPIConfig.AI_OPEN_AI_MODEL`

### `app.py` — Combined Runner
Runs both services together under one gunicorn process (`/` → recap, `/aiapi` → aiapi).

## Key Data Flow
1. User submits URL via form → `routes.index` POST
2. Article saved to DB, RQ job enqueued: `recap.tasks.classify_url`
3. RQ worker picks up job → `tasks.classify_url(url, user_id)`
4. `AiApiHelper.ClassifyUrl()` fetches article text via `readability-lxml`, then POSTs to `aiapi/classify_url`
5. `aiapi/classify.py` calls OpenAI with article content → returns JSON
6. Results saved to `Article` model (title, summary, category, author, key_topics, sub_categories)

## Database Models (`recap/models.py`)
- **User**: id, username, email, password_hash (werkzeug), phone. JWT-based password reset.
- **Article**: id, user_id (FK), url_path, title, summary, author_name, category, key_topics (JSON TEXT), sub_categories (JSON TEXT), created, classified
- **Topic**: id (UUID), name, definition — appears to be unused/future feature

## Key Files
| File | Purpose |
|------|---------|
| `recap/__init__.py` | App factory, wires DB/Redis/mail/blueprints |
| `recap/routes.py` | Main routes: index, show, add, delete, reclassify |
| `recap/tasks.py` | RQ background tasks (classify_url, example, password reset) |
| `recap/aiapi_helper.py` | HTTP client calling aiapi service; `fetch_article_content` using readability |
| `recap/models.py` | SQLAlchemy models |
| `recap/config.py` | Loads env vars from `.env`, builds Postgres URI |
| `recap/auth/__init__.py` | Login, logout, register, password reset |
| `recap/profile/__init__.py` | User profile, edit, `organize_taxonomy`, `apply_taxonomy` |
| `aiapi/classify.py` | `/classify_url` endpoint — OpenAI classification |
| `aiapi/task_processor.py` | `/process_task` endpoint — general AI task endpoint |
| `aiapi/config.py` | AIAPIConfig: OpenAI key, model, log level |

## Tech Stack
- **Python/Flask** with SQLAlchemy ORM + Flask-Migrate (Alembic)
- **PostgreSQL** (prod), SQLite in-memory (tests). Neon.tech hosted support with `sslmode=require`
- **Redis + RQ** for background job queue (`RECAP2-Classify` queue)
- **OpenAI API** (configurable model via `AI_OPEN_AI_MODEL` env var)
- **readability-lxml + lxml + httpx** for article content extraction
- **Flask-Login** for session auth, **Flask-Mail** for email, **PyJWT** for password reset tokens
- **Tailwind CSS** (compiled via npx, `input.css` → `output.css`)
- **Gunicorn** for production (not in requirements.txt — installed in Docker build)
- **Render** for hosting (moved away from AWS ECS/CDK — too expensive; then away from DigitalOcean)

## Environment Variables
### recap `.env`
- `SECRET_KEY`, `RECAP_LogLevel`, `RECAP_AI_API_URL`, `RECAP_REDIS_URL`, `RECAP_RQ_QUEUE`
- `ARTICLES_PER_PAGE`, `TASK_SERVER_NAME`
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFUALT_FROM`
- `RECAP_POSTGRES_USER/PASSWORD/HOST/PORT/DB`

### aiapi `.env`
- `AI_API_SECRET_KEY`, `AI_API_LogLevel`, `AI_API_OPENAI`, `AI_OPEN_AI_MODEL`

## Dev Startup
```bash
source .venv/bin/activate
flask --app recap init-db           # init DB
flask --app recap run --debug --port 8080   # recap only
flask --app aiapi run --debug --port 8082   # aiapi only
python run.py                              # both together
rq worker RECAP2-Classify                  # background worker
npx tailwindcss -i ./recap/static/css/input.css -o ./recap/static/css/output.css --watch
```

## Testing
- pytest with pytest-cov and pytest-mock
- Test DB: SQLite in-memory (`env == 'test'`)
- `tests/recap/` and `tests/aiapi/` directories, `conftest.py` at root of tests

## Notable Patterns & Gotchas
- `secret` field in POST data to aiapi is hardcoded `"abc123"` in `aiapi_helper.py` — not secure, a TODO
- `readability-lxml` is optional — gracefully skipped if not installed; needs `libxml2-dev`/`libxslt-dev` on Alpine
- RQ worker must be running or classification jobs silently queue with no processing
- `wtforms` pinned `<3.2` due to breaking change in `field_flags` (dict→tuple)
- `lxml` pinned `>=5.1.0,<5.2` because 5.2+ moved `html.clean`
- `flask-mail` pinned `0.10.0` — older versions not compatible with Flask 3.1.2
