# RecapAI

An AI-powered article bookmarking and classification app. Paste a URL, and the app fetches the article, classifies it using OpenAI (category, summary, title, author, key topics), and organizes your reading library.

Configure Recap and AIAPI via `.env` files. See [environment documentation](docs/environments.md).

## Architecture

Two Flask services run together:
- **`recap/`** — User-facing web app (HTML/Tailwind CSS)
- **`aiapi/`** — Internal AI microservice wrapping OpenAI

## Development Setup

### Activate virtual environment
```bash
source .venv/bin/activate
```

### Initialize the database
```bash
flask --app recap init-db
```

### Run services

**recap only** (port 8080):
```bash
flask --app recap run --debug --port 8080
```

**aiapi only** (port 8082):
```bash
flask --app aiapi run --debug --port 8082
```

**Both together** (`/` → recap, `/aiapi` → aiapi):
```bash
python run.py
```
- [recap index](http://127.0.0.1:8001/)
- [aiapi hello](http://127.0.0.1:8001/aiapi/hello)

### Background worker

A worker must be running for article classification to process:
```bash
rq worker RECAP2-Classify
```

To simulate production (worker pool):
```bash
rq worker-pool RECAP2-Classify -n 1
```

### Build CSS

Tailwind CSS requires a Node process to watch for changes:
```bash
npx tailwindcss -i ./recap/static/css/input.css -o ./recap/static/css/output.css --watch
```

## Production

> Gunicorn is installed as part of the Docker build — it is **not** in `requirements.txt`.

**recap only:**
```bash
gunicorn -w 4 'recap:create_app()' -b 127.0.0.1:8080 --access-logfile=gunicorn.http.log --error-logfile=gunicorn.error.log
```

**aiapi only:**
```bash
gunicorn -w 4 'aiapi:create_app()' -b 127.0.0.1:8080 --access-logfile=gunicorn.http.log --error-logfile=gunicorn.error.log
```

**Both together (Render production):**
```bash
gunicorn -w 3 -b 0.0.0.0:8000 app --log-level debug --timeout 90
```

**Run as daemon:**
```bash
gunicorn -w 4 'app' -b 127.0.0.1:8080 --access-logfile=gunicorn.http.log --error-logfile=gunicorn.error.log --daemon
```

**Kill gunicorn:**
```bash
ps -ef | grep gunicorn
kill -9 <pid>
```

[Gunicorn settings reference](https://docs.gunicorn.org/en/stable/settings.html)

## Docker — Fully Contained Container

Run Recap, AIAPI, and Redis in a single container for local testing or demos.

**Build:**
```bash
docker build -t recap-full . -f Dockerfile.full
```

**Run:**
```bash
docker run --detach -p 8000:8000 -t recap-full
```

**Stop:**
```bash
docker ps                          # find container id
docker stop <container_id>
```

## Deploy to Render

The app is hosted on [Render](https://render.com). Services are deployed as Docker images pulled from GitHub Container Registry (`ghcr.io/cedralpass/`).

**Build and push image:**
```bash
sh ./devops/build_for_render.sh
```

**Services defined in `render.yaml`:**
- `recap-full` — main web app (recap + aiapi + workers)
- `recap-aiapi` — standalone aiapi service
- `recaprai-redis-dev` — managed Redis instance

See [devops/render_hosting.md](devops/render_hosting.md) for Render setup details.
