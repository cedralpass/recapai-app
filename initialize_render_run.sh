#!/bin/bash
cd /app

# Run any pending Alembic migrations before starting the server.
# If alembic_version is empty the DB was created outside Alembic (e.g. init-db).
# Stamp at the last known-good revision so upgrade only applies new migrations.
CURRENT=$(flask --app recap db current 2>/dev/null)
if [ -z "$CURRENT" ]; then
    echo "No Alembic revision found - stamping at baseline before upgrading"
    flask --app recap db stamp 66e1c054e7e8
fi
flask --app recap db upgrade

#start redis server as daemon
#redis-server --daemonize yes


# startup workers using monitoring script (auto-restarts workers if they crash)
# 2 RQ workers: idle ~300MB, dual-active peak ~380MB — within 512MB Render limit
export RQ_QUEUE_NAME="RECAP2-Classify"
export NUM_WORKERS=2
/app/worker_monitor.sh &

# Daily digest scheduler: fire coordinator at 4pm Pacific Time.
# Checks every 60 s; triggers once per calendar day (PT) during the 16:xx hour.
# Does NOT rely on RQ's --with-scheduler / enqueue_at machinery.
# Edge case: if the container restarts between 16:00–16:59 PT the coordinator may
# fire a second time that day — the resulting DigestRun will status=skipped (benign).
(
  DIGEST_LAST_RUN=""   # tracks "YYYY-MM-DD-HH" of last trigger to allow 2 runs/day
  DIGEST_LAST_HEARTBEAT_HOUR=""
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] daily-digest-scheduler: started — will trigger at 8am and 4pm PT daily"
  while true; do
    NOW_HOUR=$(TZ=America/Los_Angeles date +%H)
    NOW_DATE=$(TZ=America/Los_Angeles date +%Y-%m-%d)
    NOW_KEY="${NOW_DATE}-${NOW_HOUR}"
    # Hourly heartbeat so the loop is visible in Render logs
    if [ "$NOW_HOUR" != "$DIGEST_LAST_HEARTBEAT_HOUR" ]; then
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] daily-digest-scheduler: heartbeat — PT hour=$NOW_HOUR"
      DIGEST_LAST_HEARTBEAT_HOUR="$NOW_HOUR"
    fi
    # Fire at 8am PT and 4pm PT; key includes the hour so both slots fire independently
    if { [ "$NOW_HOUR" = "08" ] || [ "$NOW_HOUR" = "16" ]; } && [ "$NOW_KEY" != "$DIGEST_LAST_RUN" ]; then
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] daily-digest-scheduler: triggering coordinator (PT hour=$NOW_HOUR)"
      flask --app recap digest run-now
      DIGEST_LAST_RUN="$NOW_KEY"
    fi
    sleep 60
  done
) &

# launch webserver in foreground (don't daemonize so container stays alive)
# 2 gunicorn workers + 2 RQ workers ≈ 4 processes, within 512MB
gunicorn -w 2 -b 0.0.0.0:8000 app --log-level info --timeout 90