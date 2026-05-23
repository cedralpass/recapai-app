# Weekly Synthesis Agent — Technical Design

## Build Status

**Core agent: Complete and verified** (as of May 2026)

The LangGraph graph runs end-to-end inside an RQ job. A management UI lets you trigger runs manually
and preview the rendered digest in-app. Email sending is implemented but gated by `send_email_flag`
so manual/debug runs store output without sending.

**Next: Scheduled sends** — a Render Cron Job or internal endpoint to run the digest for all users
on a weekly cadence with `send_email_flag=True`.

---

## Overview

The Weekly Synthesis Agent delivers a newspaper-style email digest summarising what the user saved
and read during the past week. Unlike a simple template renderer, it is a genuine **multi-step
reasoning agent** built with LangGraph: it assesses the week's content, clusters articles by theme,
synthesises insights across clusters, evaluates quality, and only then composes and sends the email.

This design is also a deliberate **LangGraph learning vehicle**. The feature covers the core
framework concepts — typed state, conditional edges, checkpointing, and tool nodes — in a
production context without requiring a new Render service.

---

## Goals

| Goal | Status |
|---|---|
| Deliver a weekly digest email | Done — email node implemented; send gated by flag |
| Multi-step agentic reasoning | Done — assess, cluster, synthesise, quality_check nodes |
| Learn LangGraph | Done |
| Reuse existing infrastructure | Done — Redis, Postgres, Flask-Mail, aiapi, RQ worker |
| No new Render service (v1) | Done — graph runs inside RQ job |
| Management UI for debugging | Done — `/settings/digest-runs` list + detail pages |
| Scheduled sends | **Not yet built** — see Scheduling section |

---

## What Makes This "Agentic"

A naive digest would be one big prompt: "here are 20 articles, write a summary." The LangGraph
version makes autonomous decisions at two nodes:

1. **`assess`** — examines the week's article count and quality, and decides whether to proceed,
   skip (too few articles), or sample (too many). It chooses clustering strategy: category-based
   (fast) or embedding-similarity-based (richer, cross-category).

2. **`quality_check`** — reads the composed digest and decides if it is good enough to send. If
   the narrative is thin or incoherent, it routes back to `synthesise` with adjusted instructions
   rather than sending a poor email.

These decision nodes, plus the conditional edges between them, are what distinguish this from a
pipeline.

---

## Graph Structure

```
START
  │
  ▼
gather ──── (no articles this week) ──► END
  │
  ▼
assess ──── (skip: < 3 articles) ──────► END
  │
  ▼
cluster
  │
  ▼
synthesise ◄─────────────────────────────┐
  │                                       │
  ▼                                       │
compose                                   │
  │                                       │
  ▼                                       │
quality_check ── (retry: digest thin) ───┘
  │
  ├── (approved or best_effort)
  ▼
send_email_node
  │
  ▼
END
```

### Edge conditions

| From | Condition | To |
|---|---|---|
| `gather` | `len(articles) == 0` | END |
| `assess` | `len(articles) < 3` | END |
| `assess` | otherwise | `cluster` |
| `quality_check` | retry_count >= 2 | `send_email` (best_effort) |
| `quality_check` | approved | `send_email` |
| `quality_check` | retry | `synthesise` |

---

## State Schema

```python
# aiapi/agents/synthesis/state.py

class ArticleData(TypedDict):
    id: int
    title: str
    summary: str
    category: str
    key_topics: list[str]
    url_path: str
    is_read: bool
    embedding: Optional[list]   # Python float list (NOT numpy) — see Gotchas

class Cluster(TypedDict):
    label: str          # human-readable theme name
    articles: list[ArticleData]
    narrative: str      # written by synthesise node

class SynthesisState(TypedDict):
    # inputs (set by the RQ task before graph invocation)
    user_id: int
    user_email: str
    user_name: str
    week_start: datetime
    week_end: datetime
    send_email_flag: bool       # True = send email; False = store only (debug runs)
    run_id: Optional[int]       # DigestRun PK

    # populated by gather
    articles: list[ArticleData]

    # populated by assess
    clustering_strategy: str    # "category" | "embedding"
    skip_reason: Optional[str]

    # populated by cluster
    clusters: list[Cluster]

    # populated by quality_check
    retry_count: int
    quality_verdict: str        # "approved" | "retry" | "best_effort"
    quality_notes: str

    # populated by compose
    digest_html: str
    digest_text: str

    # populated by send_email_node
    sent: bool
    sent_at: Optional[datetime]
```

---

## Node Implementations

### `gather`

Queries the DB for articles saved by `user_id` between `week_start` and `week_end`. Embeddings
are cast to Python `float` explicitly — see Gotchas.

### `assess`

Pure Python. Skips if < 3 articles. Chooses embedding clustering if ≥ 80% of articles have an
embedding stored; falls back to category clustering otherwise.

### `cluster`

**Category strategy**: groups by `article.category`. Fast, no AI call.

**Embedding strategy**: `sklearn.cluster.AgglomerativeClustering` on stored pgvector embeddings,
capped at 5 clusters. Labels each cluster with a 2–4 word name via a lightweight aiapi call.

### `synthesise`

Calls `aiapi/process_task` once per cluster to write a 2–3 sentence narrative insight. Incorporates
`quality_notes` on retries so the AI can improve on its previous attempt.

### `compose`

Deterministic Jinja2 rendering — no AI call. Produces both HTML and plain text versions.
- Template: `recap/templates/email/weekly_digest.html`
- Plain text: `_render_plain_text()` in `nodes.py`

### `quality_check`

AI self-evaluation: reads the plain text digest and returns `approved` or `retry` with specific
improvement notes. Caps at 2 retries (retry_count >= 2 → `best_effort`).

### `send_email_node`

Respects `send_email_flag`. When `False` (manual/debug runs), sets `sent=False` and exits without
sending. When `True` (scheduled production runs), calls `recap.email.send_email` via Flask-Mail.

```python
def send_email_node(state: SynthesisState) -> SynthesisState:
    if state.get("send_email_flag"):
        from recap.config import Config
        from recap.email import send_email
        send_email(
            subject=f"Your Recap for the week of {state['week_start'].strftime('%B %d')}",
            sender=Config.MAIL_USERNAME,
            recipients=[state["user_email"]],
            text_body=state["digest_text"],
            html_body=state["digest_html"],
        )
        state["sent"] = True
    else:
        state["sent"] = False
    state["sent_at"] = datetime.now(timezone.utc)
    return state
```

---

## DigestRun — Persistence Model

Every task invocation creates a `DigestRun` record before running the graph, and updates it with
the final state once complete. This enables the management UI and provides a debug audit trail.

```python
# recap/models.py
class DigestRun(db.Model):
    id:                  int (PK)
    user_id:             int (FK → user.id, indexed)
    job_id:              str nullable          # RQ job ID
    created_at:          datetime (UTC, indexed)
    completed_at:        datetime nullable
    week_start / week_end: datetime (timezone-aware)
    status:              str                  # "running" | "completed" | "skipped" | "failed"
    article_count:       int nullable
    clustering_strategy: str nullable
    skip_reason:         str nullable
    retry_count:         int default 0
    quality_verdict:     str nullable
    quality_notes:       Text nullable
    digest_html:         Text nullable
    digest_text:         Text nullable
    sent:                bool default False
```

### Management UI

- **`GET /settings/digest-runs`** — paginated list of all runs with status, article count, quality
  verdict, and a "Trigger New Run" button (enqueues with `send_email_flag=False`)
- **`GET /settings/digest-runs/<run_id>`** — detail page: stats row, digest HTML preview with
  plain text toggle, skip/quality notes

---

## Checkpointing

`MemorySaver` is used for checkpointing. The alternatives were evaluated:

| Option | Status | Notes |
|---|---|---|
| `MemorySaver` | **In use** | Lives for the duration of `graph.invoke()` — sufficient for single-run tasks |
| `RedisSaver` (`langgraph-checkpoint-redis`) | Not used | Requires RedisJSON module (`JSON.SET`); not available in Homebrew Redis or standard Render Redis |
| Postgres | Not used | Durable and queryable; viable upgrade if we need cross-run state |

`MemorySaver` is appropriate here because each digest run is a self-contained `graph.invoke()` call
with its own checkpointer instance. No state needs to survive between separate weekly runs.

---

## RQ Task Wrapper

```python
# recap/tasks.py

def weekly_digest_task(user_id: int, send_email_flag: bool = False):
    from langgraph.checkpoint.memory import MemorySaver
    from aiapi.agents.synthesis.graph import build_synthesis_graph
    from recap.models import DigestRun

    user = db.session.get(User, user_id)
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Create run record before graph execution
    run = DigestRun(user_id=user_id, week_start=week_start, week_end=now,
                    status="running", job_id=get_current_job().id)
    db.session.add(run); db.session.commit()

    initial_state = {
        "user_id": user_id, "user_email": user.email, "user_name": user.username,
        "week_start": week_start, "week_end": now,
        "send_email_flag": send_email_flag, "run_id": run.id,
        "articles": [], "clusters": [], "retry_count": 0, ...
    }

    try:
        checkpointer = MemorySaver()
        graph = build_synthesis_graph(checkpointer=checkpointer)
        thread = {"configurable": {"thread_id": f"digest:{user_id}:{week_start.date()}"}}
        final_state = graph.invoke(initial_state, config=thread)
        # Update DigestRun with all final_state values
        run.status = "completed" if final_state.get("digest_html") else "skipped"
        ...
        db.session.commit()
    except Exception:
        run.status = "failed"; run.completed_at = ...; db.session.commit(); raise
```

---

## Scheduling

### Current: Manual trigger (built)

The "Trigger New Run" button on `/settings/digest-runs` enqueues `weekly_digest_task` with
`send_email_flag=False`. Output is stored in `DigestRun` and viewable in-app.

The profile page `/user/<username>` links to the runs management page rather than triggering
directly — the trigger button lives on the management page.

### Next: Scheduled sends (not yet built)

The simplest Render-native approach:

**Option A — Render Cron Job** (recommended)

Add a Render Cron Job service that runs every Sunday at 08:00 UTC, calling an internal endpoint:

```python
# recap/routes.py (or a new internal blueprint)
@bp.route("/internal/cron/weekly-digest", methods=["POST"])
def cron_weekly_digest():
    secret = request.headers.get("X-Cron-Secret")
    if secret != Config.INTERNAL_CRON_SECRET:
        abort(403)
    users = db.session.execute(sa.select(User)).scalars().all()
    for user in users:
        current_app.task_queue.enqueue(
            "recap.tasks.weekly_digest_task", user.id, send_email_flag=True
        )
    return jsonify({"enqueued": len(users)})
```

Render cron config (dashboard):
```
Schedule:  0 8 * * 0        (08:00 UTC every Sunday)
Command:   curl -X POST https://recapai.onrender.com/internal/cron/weekly-digest \
                -H "X-Cron-Secret: $INTERNAL_CRON_SECRET"
```

Add `INTERNAL_CRON_SECRET` to Render environment variables.

**Option B — User opt-in flag**

Before the cron iterates users, consider adding `digest_enabled: bool` to the `User` model so
users can opt out. Default `True` for new accounts.

---

## New Files Added

```
aiapi/
  agents/
    __init__.py
    synthesis/
      __init__.py
      state.py          ← SynthesisState TypedDict, ArticleData, Cluster
      nodes.py          ← all 7 node functions
      graph.py          ← build_synthesis_graph(), routing functions

recap/
  models.py             ← DigestRun model added
  tasks.py              ← weekly_digest_task added
  profile/__init__.py   ← digest_runs, digest_run_detail routes added
  templates/
    email/
      weekly_digest.html    ← HTML digest email template
      weekly_digest.txt     ← plain text fallback
    profile/
      digest_runs.html      ← management list page
      digest_run_detail.html ← run detail + digest preview page

migrations/versions/
  0dbf2a19c462_add_digest_run_table.py

tests/
  aiapi/
    unit/
      test_synthesis_nodes.py   ← 36 unit tests (all passing)
```

---

## New Dependencies

```txt
langgraph>=0.2.0
langgraph-checkpoint-redis>=0.1.0   # installed but not used locally (see Checkpointing)
scikit-learn>=1.4.0
```

---

## Gotchas & Known Issues

### numpy.float32 serialization

`list(article.embedding)` on a pgvector column returns `numpy.float32` values. LangGraph's
`MemorySaver` uses msgpack serialization which rejects numpy scalars. Always cast explicitly:

```python
# nodes.py — _to_article_data()
"embedding": [float(x) for x in article.embedding] if article.embedding is not None else None,
```

### FORMAT strings must contain "json"

`AiApiHelper.PerformTask` uses `response_format={"type": "json_object"}`. OpenAI requires the
word "json" to appear somewhere in the messages. All FORMAT constants must follow this pattern:

```python
FORMAT = 'Respond with JSON: {"key": "value"}'  # correct
FORMAT = '{"key": "value"}'                      # WRONG — BadRequestError at runtime
```

### Cluster labeling quality

Single-article clusters can receive nonsensical AI-generated labels (e.g. "Renewable Energy
Innovations" for a LangGraph article). See [`BUGS.md`](../BUGS.md) for details and proposed fixes.

---

## Testing

36 unit tests in `tests/aiapi/unit/test_synthesis_nodes.py` covering all nodes, routing functions,
graph compilation, and the email flag behaviour. All pass with `MemorySaver`.

```bash
.venv/bin/pytest tests/aiapi/unit/test_synthesis_nodes.py -v
```

Integration test (full task with mocked aiapi): not yet written — currently verified by manual
trigger via the management UI.

---

## Build Sequence (completed steps marked)

- [x] Install dependencies — `langgraph`, `scikit-learn` added to `requirements.txt`
- [x] State + nodes — `state.py` and `nodes.py` implemented; 36 unit tests green
- [x] Graph assembly — `graph.py` wired; routing verified
- [x] RQ task — `weekly_digest_task` in `recap/tasks.py`; creates/updates `DigestRun`
- [x] Email templates — `weekly_digest.html` + `.txt` built; verified via preview
- [x] DigestRun model + migration — `0dbf2a19c462_add_digest_run_table.py`
- [x] Management UI — `/settings/digest-runs` list + detail pages
- [x] Profile page updated — Weekly Digest button → link to management page
- [ ] LangSmith tracing — env vars to add; not yet configured
- [ ] Render Cron Job — internal endpoint + Render cron service for scheduled sends
- [ ] User opt-in flag — `digest_enabled` on User model; filter in cron endpoint
