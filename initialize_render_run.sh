#!/bin/bash
cd /app

# initialize db for this server
#TODO: initialize DB needs to be a task  will do manually for now
#flask --app recap init-db

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