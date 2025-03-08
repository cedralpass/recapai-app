#!/bin/bash
cd /app

# initialize db for this server
#TODO: initialize DB needs to be a task  will do manually for now
#flask --app recap init-db

#start redis server as daemon
#redis-server --daemonize yes

# launch webserver as daemon
gunicorn -w 3 -b 0.0.0.0:8000 app --log-level debug --timeout 90 --daemon



# startup workers
rq worker-pool --url $RECAP_REDIS_URL -n 3