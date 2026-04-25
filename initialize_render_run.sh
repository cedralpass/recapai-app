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
# The monitoring script ensures 3 workers are always running
export RQ_QUEUE_NAME="RECAP2-Classify"
export NUM_WORKERS=3
/app/worker_monitor.sh &

# launch webserver in foreground (don't daemonize so container stays alive)
# This keeps the container running - if gunicorn dies, Render will restart the container
gunicorn -w 3 -b 0.0.0.0:8000 app --log-level debug --timeout 90