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
  .venv/bin/rq worker RECAP2-Classify --with-scheduler
```

The `--with-scheduler` flag is required for `queue.enqueue_at()` deferred jobs (used by
`schedule_weekly_digests_task`) to be picked up. One worker acquires a Redis lock and runs the
scheduler loop; others stay dormant and take over if the lock-holder dies.

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

## Job Types

| Task function | Queue | Trigger | What it does |
|---|---|---|---|
| `classify_url` | `RECAP2-Classify` | Article saved (web/extension) | Fetches article, calls OpenAI, stores classification + embedding |
| `organize_taxonomy_task` | `RECAP2-Classify` | User clicks "Consolidate" | AI consolidates categories into a cleaner taxonomy |
| `suggest_splits_task` | `RECAP2-Classify` | User clicks "Split" | AI suggests sub-groups for large categories |
| `weekly_digest_task` | `RECAP2-Classify` | Manual trigger (UI) or scheduled coordinator | LangGraph agent clusters articles, synthesises narratives, composes digest email |
| `schedule_weekly_digests_task` | `RECAP2-Classify` | Self-rescheduling (daily at 08:00 UTC) | Coordinator: enqueues `weekly_digest_task` for all opted-in users, then re-enqueues itself |
| `ping_aiapi` | `RECAP2-Classify` | Internal keep-alive | Wakes the aiapi Render service to prevent cold starts |

### `weekly_digest_task`

The most complex job — a multi-step LangGraph agent. It creates a `DigestRun` DB record before
starting and updates it with the final state (digest HTML, quality verdict, status) when complete.

- **Test Run trigger:** "Test Run" button at `/settings/digest-runs` — `send_email_flag=False`
  (stores digest output, does not send email)
- **Send for Real trigger:** "Send for Real" button at `/settings/digest-runs` — `send_email_flag=True`;
  confirms before sending
- **Scheduled trigger:** fired by `schedule_weekly_digests_task` (see below) — `send_email_flag=True`
- **Timeout:** jobs can take 30–90 seconds depending on article count (multiple OpenAI calls per cluster)
- **Viewing results:** `/settings/digest-runs` shows all runs; click "View" for the rendered digest preview

### `schedule_weekly_digests_task`

Coordinator that runs on a daily cadence (configurable — change `timedelta(days=1)` to `7` for weekly).
Enqueues `weekly_digest_task` for all users with `digest_enabled=True`, then uses `queue.enqueue_at()`
to schedule itself for the next day at 08:00 UTC.

Bootstrapped on deploy via `flask --app recap digest schedule-check`, which checks
`ScheduledJobRegistry` and creates the first scheduled job if none exists. Workers must run with
`--with-scheduler` (already set in `worker_monitor.sh`) for deferred jobs to be promoted.

See [`tech_design/weekly-synthesis-agent.md`](../tech_design/weekly-synthesis-agent.md) for full
architecture details.

---

## Worker Pool (rq 2.x)

rq 2.x deprecates `RoundRobinWorker` / `RandomWorker` classes in favour of a CLI flag:

```bash
rq worker --dequeue-strategy round-robin RECAP2-Classify
```

RecapAI does not currently use a dequeue strategy (single queue, so it's not needed).
