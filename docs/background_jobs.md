# Background Jobs

OpenAI classification calls take 10–30 seconds. RecapAI uses [python-rq](https://python-rq.org/) to run them in the background so the web request returns immediately.

**Queue name:** `RECAP2-Classify`
**rq version:** 2.x (upgraded from 1.x in May 2026)

---

## Redis Installation (Mac)

```bash
brew install redis
brew services start redis          # as a service
# or: /opt/homebrew/opt/redis/bin/redis-server
```

---

## Running Workers

### Local development

Use `preview_start("rq-worker")` in Claude Code, or run directly:

```bash
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES \
  .venv/bin/rq worker RECAP2-Classify
```

The `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` env var is required on macOS — rq workers are forked processes and macOS blocks certain fork patterns (HTTPX is also involved). The launch config in `.claude/launch.json` sets this automatically.

### Production (Render)

`worker_monitor.sh` keeps 3 workers running at all times. It is launched by `initialize_run.sh` as a background daemon alongside gunicorn. Workers are named `<hostname>-0`, `<hostname>-1`, `<hostname>-2` — the hostname prefix avoids name conflicts during rolling deploys.

---

## Monitoring Workers

### Health dashboard (recommended)

`GET /health` — a login-required page showing live worker state, pending job count, and AI API ping status. Use this as the first stop when diagnosing classification issues.

| Field | What it means |
|-------|---------------|
| Worker state `idle` | Worker is registered and waiting for jobs |
| Worker state `busy` | Worker is actively processing a job |
| Pending jobs > 0 | Jobs are queued but workers may be overloaded |
| No workers shown | Worker process has crashed or not started |

**Cleaning stale registrations:** After a crash or rolling deploy, Redis may retain old worker entries. Hit the "Clean stale workers" button on `/health` to remove them. This calls `clean_worker_registry()` which prunes any worker keys that no longer exist in Redis.

### JSON endpoints

- `GET /health/workers` — raw worker + queue data as JSON
- `GET /health/ping-status` — AI API keep-alive throttle key status

### Render logs

In the Render dashboard, filter logs for `WORKER_MONITOR:` to see worker start/restart/stop events, or search for `recap.tasks.classify_url` to see individual job activity.

---

## Worker Pool (rq 2.x)

rq 2.x deprecates `RoundRobinWorker` / `RandomWorker` classes in favour of a CLI flag:

```bash
rq worker --dequeue-strategy round-robin RECAP2-Classify
```

RecapAI does not currently use a dequeue strategy (single queue, so it's not needed).
