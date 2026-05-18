# Memory Management on Render

## Instance limit

Render's starter tier caps each service at **512 MB**. The `sqn55` OOM crash on 2026-05-17 showed the original configuration exceeded this.

## Process budget

Every Python process (gunicorn worker or RQ worker) uses roughly 80–120 MB at steady state.

| Configuration | Processes | Estimated peak |
|---|---|---|
| 3 gunicorn + 3 RQ (original) | 6 | ~540 MB — **OOM** |
| 2 gunicorn + 1 RQ (previous) | 3 | ~270 MB — safe |
| 2 gunicorn + 2 RQ (current) | 4 | ~380 MB peak — safe |

## Current settings (`initialize_render_run.sh`)

```
gunicorn -w 2   # 2 web workers
NUM_WORKERS=2   # 2 RQ classification workers
```

2 gunicorn workers is sufficient for a low-traffic personal app. 2 RQ workers allow parallel classification; idle baseline ~300 MB, dual-active peak ~380 MB.

## If memory pressure returns

Signs: Render "Ran out of memory" event, OOM-killed workers, "active worker already exists" Redis errors on restart.

Options in order of preference:

1. **Profile first** — attach to the Render shell and run `ps aux --sort=-%mem` to see which process is the culprit before changing counts.
2. **Reduce gunicorn workers to 1** — single-worker gunicorn still handles concurrent requests via the GIL; only hurts CPU-bound workloads, which this app isn't.
3. **Upgrade the Render plan** — next tier is 1 GB, which comfortably fits the original 6-process setup.
4. **Use gunicorn `--preload`** — loads the app once before forking; workers share read-only memory pages via copy-on-write and typically save 30–50 MB total. Add `--preload` to the gunicorn command in `initialize_render_run.sh`. Note: RQ workers must still be separate processes.

## Worker name conflict errors

OOM kills send SIGKILL, so workers cannot deregister from Redis before dying. On the next startup, new workers see the stale registrations and refuse to start.

Mitigation (already in place as of 2026-05-17): `worker_monitor.sh` appends a startup timestamp to the worker name prefix so each container start produces fresh names regardless of stale Redis state. Stale registrations expire automatically after the RQ worker TTL (~420 seconds).
