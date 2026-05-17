# RecapAI Operations Runbook

Quick reference for diagnosing and resolving production issues. Start at the top and work down.

---

## 1. First stop — Health Dashboard

`GET /health` (login required) gives a live snapshot of all moving parts:

| What you see | What it means |
|---|---|
| 3 workers, all `idle` | Healthy — workers are ready for jobs |
| 1–2 workers, rest missing | Worker(s) crashed; monitor will restart within 10s |
| 0 workers | Worker monitor itself has crashed or Redis is down |
| Pending jobs > 0 + workers idle | Workers may be stuck; check Render logs |
| AI API ping `no` | Keep-alive hasn't fired yet — not necessarily a problem |

**JSON endpoints** (useful for scripting or curl):
```
GET /health/workers      → worker count, state, pending jobs
GET /health/ping-status  → AI API keep-alive throttle key
```

---

## 2. Articles not being classified

**Symptoms:** Article stays in "processing" state indefinitely.

### Step 1 — Confirm workers are running
Check `/health`. If `worker_count` is 0, workers are down — see section 4.

### Step 2 — Check the queue depth
`/health` shows `Pending jobs`. A non-zero count means jobs are queued but not processing.

### Step 3 — Check worker logs (Render)
In the Render dashboard, filter logs for:
- `recap.tasks.classify_url` — shows job start / success / failure
- `WORKER_MONITOR:` — shows worker start / restart events
- `Error` or `Traceback` — look for OpenAI timeout or connection errors

### Step 4 — Check AI API reachability
```bash
curl https://<your-render-url>/aiapi/hello
# Expected: {"message": "hello from aiapi"}
```
If this fails, the aiapi service may be down or sleeping (Render free tier sleeps after inactivity — the keep-alive ping prevents this but may lag on cold start).

### Step 5 — Manually reclassify
From the article detail page, use the "Reclassify" button to re-enqueue a single article. Watch Render logs for the job.

---

## 3. Stale worker registrations

**Symptom:** `/health` shows more workers than expected (e.g. 9 instead of 3) after a deploy or crash.

Workers that crash or are killed without a clean shutdown leave their Redis registration behind. They expire eventually (worker TTL ≈ 420s) but can be cleared immediately:

1. Go to `/health`
2. Click **"Clean stale workers"** (confirm the dialog)
3. Page reloads showing only live workers

**Via Redis CLI** (Render shell or local):
```bash
# See all registered worker keys
redis-cli -u $RECAP_REDIS_URL keys "rq:worker:*"

# Check queue depth
redis-cli -u $RECAP_REDIS_URL llen rq:queue:RECAP2-Classify

# Nuclear option — clear entire worker registry (workers will re-register on next heartbeat)
redis-cli -u $RECAP_REDIS_URL del rq:workers
```

---

## 4. Workers are down (0 workers on /health)

### Check worker monitor
In Render logs, search for `WORKER_MONITOR:`. You should see:
```
WORKER_MONITOR: All workers started. Beginning monitoring loop (checking every 10s)...
```
If this line is absent, the monitor process didn't start.

### Check Redis connection
Workers fail silently if Redis is unreachable. Verify `RECAP_REDIS_URL` is set correctly in the Render environment variables dashboard.

```bash
# From Render shell or local
redis-cli -u $RECAP_REDIS_URL ping
# Expected: PONG
```

### Force a redeploy
If the worker monitor crashed and didn't restart, triggering a Render redeploy will restart the container and re-launch `worker_monitor.sh`:

```bash
# Trigger via GitHub Actions (push to main) or Render dashboard → Manual Deploy
```

---

## 5. Redis key reference

| Key | What it is |
|---|---|
| `rq:workers` | Set of all registered worker keys |
| `rq:worker:<name>` | Individual worker registration (has TTL) |
| `rq:queue:RECAP2-Classify` | Pending job list |
| `rq:finished:RECAP2-Classify` | Completed jobs (auto-expires) |
| `rq:failed:RECAP2-Classify` | Failed jobs (inspect these for errors) |
| `aiapi:ping:last` | Keep-alive throttle key (TTL ≈ 600s) |

**Inspect a failed job:**
```bash
redis-cli -u $RECAP_REDIS_URL lrange rq:failed:RECAP2-Classify 0 -1
```

---

## 6. Local dev quick-start

```bash
brew services start redis
# In Claude Code:
preview_start("recap")      # localhost:8080
preview_start("aiapi")      # localhost:8082
preview_start("tailwind")   # CSS watch
preview_start("rq-worker")  # background worker

# Then visit localhost:8080/health
```

Run tests before committing:
```bash
.venv/bin/pytest tests/ -v
```
