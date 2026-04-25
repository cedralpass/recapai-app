#!/bin/bash
cd /app

# initialize db for this server
#TODO: initialize DB needs to be a task  will do manually for now
#flask --app recap init-db

# start redis server as daemon for local all-in-one container
redis-server --daemonize yes

# startup workers using monitoring script (same behavior pattern as Render)
export RQ_QUEUE_NAME="RECAP2-Classify"
export NUM_WORKERS=3
bash /app/worker_monitor.sh &

# launch webserver in foreground so container stays alive
gunicorn -w 3 -b 0.0.0.0:8000 app --log-level debug --timeout 90