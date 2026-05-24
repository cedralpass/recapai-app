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

### Deploying

Deploys are fully automated via GitHub Actions (`.github/workflows/deploy.yml`). Push to `main` and the pipeline runs automatically:
1. **test** job — runs pytest with a Redis service container; blocks deploy on failure
2. **build-and-deploy** job — builds both Docker images, pushes to GHCR, triggers Render deploy hooks

Render env vars are configured directly in the Render dashboard (not baked into the image). The `CR_PAT` and `RENDER_DEPLOY_HOOK_*` secrets live in GitHub Actions secrets. Manual deploys via `devops/build_for_render.sh` still work if needed.

### Worktree dev servers — how they find the right code

`preview_start` sets the server's CWD to the current worktree directory automatically. The launch configs use absolute paths for `.venv` and no hardcoded `cd`, so every server (`recap`, `tailwind`, `rq-worker`) runs from whichever worktree the session is in and picks up that worktree's code.

The `recap` server auto-copies `recap/.env` from the main repo on first start if it isn't already present in the worktree (the file is gitignored and won't be checked out). You don't need to do this manually.

**If a server is running from the wrong worktree** (check `preview_list` — look at the `cwd` field): stop it with `preview_stop` and restart with `preview_start`. The new instance will use the correct CWD.

### Worktree hygiene — end of session checklist

Claude Code sessions run in a git worktree (`claude/blissful-ardinghelli` etc), but **commits go
directly to `main`** — `git status` and `git commit` run from the main repo root (`/Users/geoffreysmalling/development/recapai-app`), which is on branch `main`. The worktree branch itself stays behind and never receives commits.

At session end the Claude Code UI shows a diff between the worktree branch and `main` ("+446 -172"
style). This is expected and harmless — it just reflects that `main` has moved ahead. It does NOT
mean changes are lost or pending.

To verify everything is clean:
```bash
git status                  # should be clean on main (only output.css may be modified)
git log --oneline -3        # confirm latest commits are present
```

If `git status` is clean and commits are present, nothing needs to be done. Ignore the Claude Code
session diff UI — all code is on `main` and pushed.

---

## Commit Checklist

Before committing, run these in order:

1. **`/update-docs`** — reviews what changed and updates any affected docs (`docs/`, `CLAUDE.md`, `tech_design/`, `BUGS.md`, `docs/vision.md`). Run this first so doc changes are included in the same commit.
2. **`ruff check .`** — enforced via pre-commit hook, will block the commit if it fails.
3. **`.venv/bin/pytest tests/ -v`** — confirm tests still pass.

The ruff hook runs automatically on `git commit`. The other two steps are manual.

---

## Code Style

**Ruff** is enforced via a pre-commit hook. All code must pass `ruff check .` and `ruff format .` before committing. The hook runs automatically — do not write code with unused imports, bare `except:`, or `== None` comparisons. See [docs/development.md](docs/development.md) for setup and manual usage.

---

## Running Tests

```bash
.venv/bin/pytest tests/ -v
```

All required test env vars are set as defaults in `tests/conftest.py` — no prefix needed locally. Redis must be running (`brew services start redis`) as the test suite connects to it.

### Integration test approach

HTTP boundaries are mocked with **`respx`** (httpx-native, no VCR.py needed).
Recorded fixtures live in `tests/fixtures/`:
- `flask_tutorial_part1.html` — raw article HTML fetched with the same headers `fetch_article_content` uses
- `openai_flask_tutorial_response.json` — actual OpenAI response captured from a live rq-worker run

To record a new article fixture:
```bash
.venv/bin/python -c "
import httpx
r = httpx.get('YOUR_URL', headers={'User-Agent': 'Recap/1.0'}, follow_redirects=True)
open('tests/fixtures/your_article.html', 'w').write(r.text)
"
```
Then run a live classification and copy the JSON from the rq-worker logs into a matching fixture file.

### Seed data fixtures

`tests/seed_data.py` contains **53 real classified articles across 10 categories**, sourced from a live testuser run. Use these fixtures instead of creating ad-hoc toy data:

| Fixture | What it provides |
|---------|-----------------|
| `seeded_user` | User `seeduser` pre-loaded with all 53 articles; yields the User object |
| `seeded_articles` | All Article objects for `seeded_user`, ordered by category then created |

```python
def test_something(seeded_user, recap_app):
    ...

def test_something_else(seeded_articles):
    ai_articles = [a for a in seeded_articles if a.category == "Artificial Intelligence"]
    assert len(ai_articles) == 27
```

`tests/seed_data.py` also exports `SEED_CATEGORIES` (sorted list) and `SEED_CATEGORY_COUNTS` (dict) for assertion baselines.

---

## Dev Scripts

`scripts/load_test_articles.py` — seeds a running local instance with the same 50 URLs used to generate the seed data:

```bash
# Creates testuser if needed, submits all URLs, classification happens via RQ
.venv/bin/python scripts/load_test_articles.py

# Wait and print results as articles are classified
.venv/bin/python scripts/load_test_articles.py --status
```

Run `--help` for all options (username, email, password, api-url, delay, dry-run).

---

## UI Development

Before making any template or style changes, read **[docs/design-system.md](docs/design-system.md)**.

It documents the complete visual language of the app: color tokens, typography scale, every component pattern (cards, buttons, forms, badges, sidebar, flash messages, pagination), responsive breakpoints, and interaction patterns. It's the fastest way to understand what classes to use and why before touching a template.

Key things to know without reading the whole doc:
- **All styling is Tailwind utility classes** — no custom component CSS except a few global `@apply` rules in `recap/static/css/input.css`
- **Two-column desktop layout on index** — article list (`flex-1 max-w-2xl`) + sticky filter sidebar (`w-60`), collapses to single-column on mobile
- **Mobile filter is a horizontal scroll pill row** (`flex gap-2 overflow-x-auto`, no JS toggle); desktop filter is the persistent `<aside>` in `index.html` — they are separate elements
- **Tailwind must be rebuilt** after any template class changes: the `tailwind` preview server watches templates and recompiles `recap/static/css/output.css` automatically during development

### Redesign (completed)

All major pages have been redesigned via Claude Code using the specs in `design_handoff/`. Before editing any template, read **[design_handoff/README.md](design_handoff/README.md)** for layout and component specs, and **[design_handoff/design-system.md](design_handoff/design-system.md)** (identical to `docs/design-system.md`) for tokens and patterns.

Pages covered: unauthenticated homepage, login, register, forgot/reset password, authenticated index, article detail, profile, edit profile, API token, organise taxonomy.

---

## Key Architecture

```
recap/              ← Main Flask app (web UI)
  __init__.py       ← App factory, blueprint registration, CORS, RQ setup
  models.py         ← SQLAlchemy models (User, Article, DigestRun)
  api_v1.py         ← REST API blueprint: POST /api/v1/articles (Bearer token auth)
  profile/          ← Profile/settings blueprint (incl. /settings/api-token)
    __init__.py     ← Taxonomy routes + digest run routes (/settings/digest-runs)
                       (see docs/taxonomy_organnization.md and tech_design/weekly-synthesis-agent.md)
  tasks.py          ← RQ tasks: classify_url, weekly_digest_task, schedule_weekly_digests_task, taxonomy tasks
  cli.py            ← Flask CLI: `flask digest schedule-check` (bootstraps scheduled sends on deploy)
  templates/        ← Jinja2 templates
    email/          ← weekly_digest.html + .txt (digest email templates)
  static/css/       ← Tailwind output.css (rebuilt by tailwind server)

aiapi/              ← Separate AI API Flask app
  task_processor.py ← build_prompt(), OpenAI call (temp=0.3, max_tokens=4096, timeout=180s)
  agents/           ← LangGraph agents
    synthesis/      ← Weekly digest agent
      state.py      ← SynthesisState TypedDict
      nodes.py      ← 7 graph node functions (gather, assess, cluster, synthesise, compose,
                       quality_check, send_email_node)
      graph.py      ← build_synthesis_graph() — StateGraph assembly + routing functions

chrome-extension/   ← Manifest V3 Chrome Extension (no build step)
tests/              ← pytest: unit + integration
  aiapi/unit/       ← test_synthesis_nodes.py (36 tests, all node functions mocked)
migrations/         ← Alembic migrations
tech_design/        ← Technical design docs for major features
BUGS.md             ← Known bugs tracked here (open issues not yet scheduled)
```

### Taxonomy AI features

Two user-facing routes let users reorganise their article taxonomy with AI assistance:

- **Consolidate** (`GET /organize_taxonomy`) — merges similar/overlapping categories
- **Split** (`GET /user/<username>/suggest_splits`) — breaks large categories (≥12 articles) into sub-groups

Both use `AiApiHelper.PerformTask()` → `aiapi/task_processor.py` → OpenAI. Prompt structure,
example payloads, OpenAI parameters, and tuning levers are documented in
**[docs/taxonomy_organnization.md](docs/taxonomy_organnization.md)**. Read that before modifying
any prompt strings, context builders, or the OpenAI call parameters in `task_processor.py`.

---

## Chrome Extension

Loaded unpacked from `chrome-extension/`. No build step required.
- Token-authenticated: users get their token from `/settings/api-token`
- Calls `POST /api/v1/articles` with `Authorization: Bearer <token>`
- See `docs/chrome_extension.md` for full setup guide
