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

All other vars come from `recap/.env` baked into the image at build time (via `COPY`).

### What the container runs

`initialize_render_run.sh` is the entrypoint. It:
1. Stamps Alembic if no migration history exists (`flask db stamp <baseline>`)
2. Runs `flask db upgrade` to apply any pending migrations
3. Starts the combined app (recap + aiapi via `DispatcherMiddleware`) on port 8000
4. Launches `worker_monitor.sh` to manage RQ worker processes

---

## Running Tests

```bash
AI_API_LogLevel=DEBUG AI_API_OPENAI=test AI_API_SECRET_KEY=test AI_OPEN_AI_MODEL=gpt-4 \
  .venv/bin/pytest tests/ -v
```

Run tests before committing. The test suite covers unit and integration tests but does not exercise the browser UI — always verify UI changes via the native harness preview.
