# RecapAI Development Strategy

## Two-Mode Development Model

RecapAI uses two distinct environments depending on the goal:

| Mode | When to use | Iteration speed |
|------|-------------|-----------------|
| **Native harness** | Active development with Claude Code | Instant (hot-reload) |
| **Docker container** | Pre-deploy validation, smoke testing | 60–90s rebuild |

---

## Native Harness (Claude Code / Active Development)

Run four services natively via `preview_start`. Code and template changes appear instantly — no rebuild required.

### Start order

```bash
# 1. Ensure Redis is running (required by rq-worker)
brew services start redis

# 2. Start all four services (in Claude Code via preview_start, or terminal)
flask --app recap run --debug --port 8080          # Main app
flask --app aiapi run --debug --port 8082          # AI/classification API
npx tailwindcss -i ./recap/static/css/input.css \
  -o ./recap/static/css/output.css --watch         # CSS watch compiler
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES \
  .venv/bin/rq worker RECAP2-Classify              # Background worker
```

Or use Claude Code's `preview_start` with the names defined in `.claude/launch.json`:
- `recap` → port 8080 (preview browser connects here)
- `aiapi` → port 8082
- `tailwind` → CSS watch (no port, check via `preview_logs`)
- `rq-worker` → background worker (no port, check via `preview_logs`)

### Monitoring background services

`tailwind` and `rq-worker` have no web UI. Use `preview_logs` (in Claude Code) to check their output:
- **tailwind** — shows "Done in Xms" on each CSS rebuild
- **rq-worker** — shows job start/finish/failure as articles are classified

#### Health dashboard

`GET /health` (login required) shows live worker state, pending job count, and AI API ping status — useful for both local dev and production diagnosis. It also has a "Clean stale workers" button that prunes dead worker registrations from Redis. See [docs/background_jobs.md](background_jobs.md) for details.

### Environment (local dev)

`recap/.env` is the single source of truth for local development:

```
RECAP_POSTGRES_HOST=localhost
RECAP_AI_API_URL=http://localhost:8082/
```

**Never change these values for Docker** — pass overrides via `-e` at runtime instead.

### Python environment

Always prefix Python commands with `.venv/bin/` — never call `flask`, `rq`, or `python` directly:

```bash
.venv/bin/flask --app recap run --debug --port 8080
.venv/bin/pytest tests/ -v
```

### Stale process warning

If the preview browser shows a `host.docker.internal` DB error after restarting a session, the `recap` server was reused from a previous session with old env vars. Fix: stop and restart it.

---

## Docker Container (Pre-Deploy Validation)

Use Docker only for:
- Smoke testing the full bundled image before pushing to Render
- Testing `initialize_render_run.sh` startup behavior (migrations, worker monitor)
- Simulating the Render container environment

### Build and run

```bash
# Build
docker build -t recap-full . -f ./devops/Dockerfile.full

# Run (override the 2 vars that differ from local dev)
docker run --detach -p 8000:8000 \
  --add-host host.docker.internal:host-gateway \
  -e RECAP_POSTGRES_HOST=host.docker.internal \
  -e RECAP_AI_API_URL=http://localhost:8000/aiapi/ \
  recap-full
```

The app is available at `http://localhost:8000`. The Claude Code preview browser cannot reach this port (sandboxed to 8080) — use your regular browser.

### Environment overrides for Docker

| Variable | Local dev value | Docker override |
|----------|----------------|-----------------|
| `RECAP_POSTGRES_HOST` | `localhost` | `host.docker.internal` |
| `RECAP_AI_API_URL` | `http://localhost:8082/` | `http://localhost:8000/aiapi/` |

All other vars are set directly in the Render dashboard — they are no longer baked into the image.

### What the container runs

`initialize_render_run.sh` is the entrypoint. It:
1. Stamps Alembic if no migration history exists (`flask db stamp <baseline>`)
2. Runs `flask db upgrade` to apply any pending migrations
3. Starts the combined app (recap + aiapi via `DispatcherMiddleware`) on port 8000
4. Launches `worker_monitor.sh` to manage RQ worker processes

---

## Linting and Code Style

RecapAI uses **Ruff** for linting and formatting. A pre-commit hook runs automatically on every `git commit`.

### First-time setup

```bash
pip install -r requirements-dev.txt
pre-commit install
```

That's it — the hook fires on every commit from then on.

### What it does

- **Ruff** — checks for unused imports, bad style, common bugs, and sorts imports
- **ruff-format** — enforces consistent formatting (similar to Black)

Auto-fixable issues are corrected in-place; the commit is blocked only if unfixable issues remain.

### Run manually

```bash
# Check for issues
.venv/bin/ruff check .

# Fix auto-fixable issues
.venv/bin/ruff check . --fix

# Format all files
.venv/bin/ruff format .
```

### Adding to CI

The linter is not yet wired into GitHub Actions — it runs locally only until the codebase is fully clean. To add it, insert a lint step before the test job in `.github/workflows/deploy.yml`:

```yaml
- name: Lint
  run: .venv/bin/ruff check .
```

---

## Running Tests

```bash
.venv/bin/pytest tests/ -v
```

All required env vars default in `tests/conftest.py` — no prefix needed. Redis must be running locally (`brew services start redis`).

Run tests before committing. The test suite covers unit and integration tests but does not exercise the browser UI — always verify UI changes via the native harness preview.

---

## CI/CD (GitHub Actions)

Pushing to `main` automatically triggers `.github/workflows/deploy.yml`:

1. **test** — runs pytest against a Redis service container; deploy is blocked if tests fail
2. **build-and-deploy** — builds `recap-aiapi` and `recap-full` Docker images, pushes to GHCR (`ghcr.io/cedralpass/`), then fires Render deploy hooks

**Secrets required in GitHub Actions** (`Settings → Secrets and variables → Actions`):
- `CR_PAT` — GitHub personal access token with `write:packages` scope
- `RENDER_DEPLOY_HOOK_AIAPI` — deploy hook URL from Render dashboard
- `RENDER_DEPLOY_HOOK_FULL` — deploy hook URL from Render dashboard

**Production env vars** are set in the Render dashboard, not in the image. Update them there when adding new required config.
