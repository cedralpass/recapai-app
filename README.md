# recap

Currently Amazon Web Services with ECS is too expensive $5 a day as configured in CDK. For now, we will deploy with DigitalOcean and run App Platform. To get back to CDK, we need to add the python libraries back that are commented out in our requirements.txt.  Removing CDK also removes 180MB from our container size.

Configure Recap and AIAPI via .env files.  See documentation [here](docs/environments.md)

#setup
## Init DB
Run the following command to init DB
```bash
flask --app recap init-db   
```

## Init dev webserver
Run the following command to run the development, builtin webserver

### For just the recap service: 
```bash
flask --app recap run --debug  --port 8081
```
[recap index page](http://127.0.0.1:8081/)

### For just the aiapi service: 
```bash
flask --app aiapi run --debug  --port 8082
```

### Two run recap and aiapi together with
/ -> recap
/aiapi -> aiapi

use the following script
```bash
python run.py
```

[recap index page ](http://127.0.0.1:8001/)
[aiapi hello function ](http://127.0.0.1:8001/aiapi/hello)

## Background processing worker
Make sure a worker is running in a python terminal for background processing.

```rq worker RECAP-Classify```

# Produciton

!! Gunicorn is installed as part of the docker build scripts. It is not in requirements.txt !!
## recap - Run the produciton gunicorn web server
Run the following command to run in produciton
```bash
gunicorn -w 4 'recap:create_app()' -b 127.0.0.1:8080 --access-logfile=gunicorn.http.log --error-logfile=gunicorn.error.log
```

## aiapi - Run the produciton gunicorn web server
Run the following command to run the aiapi produciton
```bash
gunicorn -w 4 'aiapi:create_app()' -b 127.0.0.1:8080 --access-logfile=gunicorn.http.log --error-logfile=gunicorn.error.log
```

## recap + aiapi - Run recap and aiapi together under one server

```bash
 gunicorn -w 4 'app' -b 127.0.0.1:8080 --access-logfile=gunicorn.http.log --error-logfile=gunicorn.error.log
```

## run gunicorn as daemon
``` gunicorn -w 4 'app' -b 127.0.0.1:8080 --access-logfile=gunicorn.http.log --error-logfile=gunicorn.error.log --daemon```

### kill gunicorn
1. ``` ps -ef | grep gunicorn```
2. ```kill -9 [prgm pid]```

[recap index page ](http://127.0.0.1:8080/)
[aiapi hello function ](http://127.0.0.1:8080/aiapi/hello)

[gunicorn settings](https://docs.gunicorn.org/en/stable/settings.html)

## Fully Contained Docker Contaner
We can also run Recap, API, REDIS in one container for testing / demo...

Dockerfile is Dockerfile.aws.full

### Build with this command

```docker build -t recap-full . -f Dockerfile.full```

### Run with this command
```docker run --detach  -p 8000:8000 -t recap-full```
### Stop the container with this command

1. to list the docker containers running ```docker ps```
2. to stop the container: ```docker stop <container id>``` example ```docker stop 9e498c6d5732```