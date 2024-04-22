# Background Jobs

OpenAI apis are time consuming, for example ChatGPT4 takes ~14 seconds for prompts powering recap.  We will use a simple background job processor: [python-rq]([https://python-rq.org/])

This requires redis to be installed

## Redis Installation on Mac
to install redis, reccomend using homebrew
```brew install redis```

Then you have several ways to start it locally:

### Configure using
```/opt/homebrew/etc/redis.conf```

### As a service: 
```brew services start redis```
### In terminal

```/opt/homebrew/opt/redis/bin/redis-server```

## Workers

RQ uses a worker process. We need to spawn a worker using the RQ "worker" option.  
We pass the queue name for the worker to monitor. without a queue passed in, the worker monitors the "default" queue
```rq worker RECAP-Classify```

## HTTPX and Workers
Workers are forked processes.  We are also using HTTPX which is another forked process.  MAC has a security mechanism to block this..  We need to set an Environment variable

```export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES```

also wise to add it to your shell profile. 

Good reference: [Flask Mega-Tuturial: Background Jobs](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xxii-background-jobs)

## Running in a pool - BETA feature of RQ
you can run in a pool of multiple workers.  read more at [RQ Workers](https://python-rq.org/docs/workers/)

``` rq worker-pool RECAP-Classify -n 3```






