#!/bin/bash
cd /app

# initialize db for this server
#TODO: initialize DB needs to be a task  will do manually for now
#flask --app recap init-db

#start redis server as daemon
#redis-server --daemonize yes


# startup workers using worker-pool (fixed in rq 1.16.2)
#rq worker-pool RECAP2-Classify -n 3 &

# startup workers - using individual workers instead of worker-pool
# worker-pool has a bug with --job-class parameter in rq 1.x versions
# Use RECAP_REDIS_URL environment variable for Redis connection
rq worker --url $RECAP_REDIS_URL RECAP2-Classify &
rq worker --url $RECAP_REDIS_URL RECAP2-Classify &
rq worker --url $RECAP_REDIS_URL RECAP2-Classify &

# launch webserver in foreground (don't daemonize so container stays alive)
gunicorn -w 3 -b 0.0.0.0:8000 app --log-level debug --timeout 90