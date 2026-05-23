# Weekly Synthesis Agent — Technical Design

## Overview

The Weekly Synthesis Agent runs every Sunday morning and delivers a newspaper-style email digest
summarising what the user saved and read during the past week. Unlike a simple template renderer,
it is a genuine **multi-step reasoning agent** built with LangGraph: it assesses the week's
content, clusters articles by theme, synthesises insights across clusters, evaluates quality, and
only then composes and sends the email.

This design is also a deliberate **LangGraph learning vehicle**. The feature covers the core
framework concepts — typed state, conditional edges, checkpointing, and tool nodes — in a
production context without requiring a new Render service.

---

## Goals

| Goal | Notes |
|---|---|
| Deliver a weekly digest email | Sunday morning, per-user |
| Multi-step agentic reasoning | Not a single prompt — agent assesses, clusters, synthesises, quality-checks |
| Learn LangGraph | Cover StateGraph, conditional edges, checkpointing, LangSmith tracing |
| Reuse existing infrastructure | Existing Redis, Postgres, Flask-Mail, aiapi, RQ worker |
| No new Render service (v1) | Agent graph runs inside an RQ job |

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
  ├── strategy: "category"
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
  ├── (approved)
  ▼
send_email
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
| `quality_check` | digest is thin or incoherent | `synthesise` (retry +1) |
| `quality_check` | retry count >= 2 | `send_email` (send best effort) |
| `quality_check` | approved | `send_email` |

---

## State Schema

```python
# aiapi/agents/synthesis/state.py

from datetime import datetime
from typing import TypedDict, Optional

class ArticleData(TypedDict):
    id: int
    title: str
    summary: str
    category: str
    key_topics: list[str]
    url_path: str
    is_read: bool

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

    # populated by gather
    articles: list[ArticleData]

    # populated by assess
    clustering_strategy: str    # "category" | "embedding"
    skip_reason: Optional[str]  # set if agent decides to skip

    # populated by cluster
    clusters: list[Cluster]

    # populated by quality_check
    retry_count: int
    quality_verdict: str        # "approved" | "retry" | "best_effort"
    quality_notes: str          # feedback for the synthesise retry

    # populated by compose
    digest_html: str
    digest_text: str

    # populated by send_email
    sent: bool
    sent_at: Optional[datetime]
```

---

## Node Implementations

### `gather`

Queries the DB for articles saved by `user_id` between `week_start` and `week_end`. Uses
existing SQLAlchemy models — no aiapi call needed.

```python
def gather(state: SynthesisState) -> SynthesisState:
    articles = db.session.execute(
        sa.select(Article)
          .where(Article.user_id == state["user_id"])
          .where(Article.created >= state["week_start"])
          .where(Article.created <= state["week_end"])
          .where(Article.classified.isnot(None))
          .order_by(Article.category, Article.created.desc())
    ).scalars().all()

    state["articles"] = [_to_article_data(a) for a in articles]
    return state
```

### `assess`

The first decision node. Examines article count and chooses clustering strategy. No LLM call —
pure Python logic. If articles < 3, sets `skip_reason` and the conditional edge routes to END.

```python
def assess(state: SynthesisState) -> SynthesisState:
    count = len(state["articles"])
    if count < 3:
        state["skip_reason"] = f"Only {count} article(s) this week — skipping digest."
        return state

    # Use embedding clustering if most articles have embeddings; fall back to category
    embedded = sum(1 for a in state["articles"] if a.get("embedding") is not None)
    if embedded / count >= 0.8:
        state["clustering_strategy"] = "embedding"
    else:
        state["clustering_strategy"] = "category"

    return state
```

### `cluster`

Groups articles into thematic clusters. Two strategies:

**Category strategy** (fast, always available): groups by `article.category`. Simple dict grouping,
no AI call.

**Embedding strategy** (richer): uses `sklearn.cluster.AgglomerativeClustering` on the stored
`article.embedding` vectors to find cross-category thematic groups. Labels each cluster with a
short name via a lightweight aiapi call. Capped at 5 clusters.

```python
def cluster(state: SynthesisState) -> SynthesisState:
    if state["clustering_strategy"] == "category":
        state["clusters"] = _cluster_by_category(state["articles"])
    else:
        state["clusters"] = _cluster_by_embedding(state["articles"])
    return state
```

### `synthesise`

Calls `aiapi/process_task` once per cluster (same pattern as existing taxonomy routes) to write a
2–3 sentence narrative insight for each cluster. Incorporates `quality_notes` on retries.

Each cluster prompt:
```
System: "You are synthesising a user's weekly reading for a digest email."
Context: cluster label + article titles + summaries + key topics
Prompt: "Write 2-3 sentences capturing the key insight or theme from these articles.
         Be specific — name concepts, not just 'several articles about X'.
         [On retry: quality_notes injected here]"
```

```python
def synthesise(state: SynthesisState) -> SynthesisState:
    for cluster in state["clusters"]:
        context = _build_cluster_context(cluster, state.get("quality_notes", ""))
        result = AiApiHelper.PerformTask(context, SYNTHESISE_PROMPT, SYNTHESISE_FORMAT, state["user_id"])
        cluster["narrative"] = result.get("narrative", "")
    return state
```

### `compose`

Assembles the full digest from cluster narratives using a Jinja2 template (HTML + plain text).
No AI call — deterministic rendering. Template lives at
`recap/templates/email/weekly_digest.html`.

```python
def compose(state: SynthesisState) -> SynthesisState:
    state["digest_html"] = render_template(
        "email/weekly_digest.html",
        user_name=state["user_name"],
        week_start=state["week_start"],
        clusters=state["clusters"],
        article_count=len(state["articles"]),
    )
    state["digest_text"] = _render_plain_text(state["clusters"])
    return state
```

### `quality_check`

The second decision node. Makes an AI call to evaluate the digest before sending — the agent
reads its own output and decides if it meets the bar.

```python
QUALITY_PROMPT = """
Review this weekly digest email. Respond with JSON:
{
  "verdict": "approved" | "retry",
  "notes": "If retry: specific instructions for improvement. If approved: empty string."
}

Approve if: narratives are specific and insightful, not generic.
Request retry if: any narrative is vague, repetitive, or just restates article titles.
"""

def quality_check(state: SynthesisState) -> SynthesisState:
    if state.get("retry_count", 0) >= 2:
        state["quality_verdict"] = "best_effort"
        return state

    result = AiApiHelper.PerformTask(state["digest_html"], QUALITY_PROMPT, QUALITY_FORMAT, state["user_id"])
    state["quality_verdict"] = result.get("verdict", "approved")
    state["quality_notes"] = result.get("notes", "")
    state["retry_count"] = state.get("retry_count", 0) + 1
    return state
```

### `send_email`

Calls existing `recap.email.send_email`. Uses Flask-Mail, already configured.

```python
def send_email_node(state: SynthesisState) -> SynthesisState:
    send_email(
        subject=f"Your Recap for the week of {state['week_start'].strftime('%B %d')}",
        sender=Config.MAIL_USERNAME,
        recipients=[state["user_email"]],
        text_body=state["digest_text"],
        html_body=state["digest_html"],
    )
    state["sent"] = True
    state["sent_at"] = datetime.now(timezone.utc)
    return state
```

---

## Graph Assembly

```python
# aiapi/agents/synthesis/graph.py

from langgraph.graph import StateGraph, END
from .state import SynthesisState
from .nodes import gather, assess, cluster, synthesise, compose, quality_check, send_email_node

def _route_after_gather(state: SynthesisState) -> str:
    return END if not state["articles"] else "assess"

def _route_after_assess(state: SynthesisState) -> str:
    return END if state.get("skip_reason") else "cluster"

def _route_after_quality(state: SynthesisState) -> str:
    if state["quality_verdict"] in ("approved", "best_effort"):
        return "send_email"
    return "synthesise"

def build_synthesis_graph(checkpointer=None):
    g = StateGraph(SynthesisState)

    g.add_node("gather",       gather)
    g.add_node("assess",       assess)
    g.add_node("cluster",      cluster)
    g.add_node("synthesise",   synthesise)
    g.add_node("compose",      compose)
    g.add_node("quality_check", quality_check)
    g.add_node("send_email",   send_email_node)

    g.set_entry_point("gather")
    g.add_conditional_edges("gather",       _route_after_gather)
    g.add_conditional_edges("assess",       _route_after_assess)
    g.add_edge("cluster",      "synthesise")
    g.add_edge("synthesise",   "compose")
    g.add_edge("compose",      "quality_check")
    g.add_conditional_edges("quality_check", _route_after_quality)
    g.add_edge("send_email",   END)

    return g.compile(checkpointer=checkpointer)
```

---

## Checkpointing (State Persistence)

LangGraph checkpointers persist graph state between nodes so that long-running jobs can survive
worker restarts. Two options — both infrastructure already exists:

| Option | Package | Connection | Notes |
|---|---|---|---|
| **Redis** (recommended for v1) | `langgraph-checkpoint-redis` | Existing `RECAP_REDIS_URL` | TTL-based, no migration needed |
| Postgres | `langgraph-checkpoint-postgres` | Existing Neon Postgres | Durable, queryable, needs table migration |

```python
# Redis checkpointer setup (in the RQ task)
from langgraph.checkpoint.redis import RedisSaver

with RedisSaver.from_conn_string(Config.RECAP_REDIS_URL) as checkpointer:
    graph = build_synthesis_graph(checkpointer=checkpointer)
    thread = {"configurable": {"thread_id": f"digest:{user_id}:{week_start.date()}"}}
    graph.invoke(initial_state, config=thread)
```

The `thread_id` is deterministic per user per week, so re-running the job is idempotent —
LangGraph resumes from the last checkpoint rather than starting over.

---

## RQ Task Wrapper

The graph runs inside a standard RQ task, following the same pattern as `classify_url` and
`organize_taxonomy_task`. No new Render service needed for v1.

```python
# recap/tasks.py — new task

def weekly_digest_task(user_id: int):
    from datetime import timedelta
    from langgraph.checkpoint.redis import RedisSaver
    from aiapi.agents.synthesis.graph import build_synthesis_graph

    user = db.session.get(User, user_id)
    if not user or not user.email:
        return

    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

    initial_state = {
        "user_id": user_id,
        "user_email": user.email,
        "user_name": user.username,
        "week_start": week_start,
        "week_end": now,
        "articles": [],
        "clusters": [],
        "retry_count": 0,
        "sent": False,
    }

    with RedisSaver.from_conn_string(Config.RECAP_REDIS_URL) as checkpointer:
        graph = build_synthesis_graph(checkpointer=checkpointer)
        thread = {"configurable": {"thread_id": f"digest:{user_id}:{week_start.date()}"}}
        graph.invoke(initial_state, config=thread)

    app.logger.info("weekly_digest_task: completed for user_id=%s", user_id)
```

---

## Scheduling

**v1: Manual trigger from the profile page** — "Send me this week's digest" button. Enqueues
the RQ task immediately. No new scheduler infrastructure, easy to test.

**v2: Render Cron Job** — A Render cron job (free tier) hits an internal endpoint every Sunday
at 08:00 UTC. The endpoint iterates all users and enqueues one `weekly_digest_task` per user.

```python
# recap/routes.py — internal cron endpoint (v2)
@bp.route("/internal/cron/weekly-digest", methods=["POST"])
def cron_weekly_digest():
    secret = request.headers.get("X-Cron-Secret")
    if secret != Config.INTERNAL_CRON_SECRET:
        abort(403)
    users = db.session.execute(sa.select(User)).scalars().all()
    for user in users:
        current_app.task_queue.enqueue("recap.tasks.weekly_digest_task", user.id)
    return jsonify({"enqueued": len(users)})
```

Render cron config (in Render dashboard):
```
Schedule:  0 8 * * 0        (08:00 UTC every Sunday)
Command:   curl -X POST https://recapai.onrender.com/internal/cron/weekly-digest \
                -H "X-Cron-Secret: $INTERNAL_CRON_SECRET"
```

---

## New Dependencies

```txt
# requirements.txt additions
langgraph>=0.2.0
langgraph-checkpoint-redis>=0.1.0
scikit-learn>=1.4.0          # for AgglomerativeClustering in embedding strategy
```

`scikit-learn` is already likely present (numpy is installed). Verify with
`.venv/bin/pip show scikit-learn` before adding.

---

## New Files

```
aiapi/
  agents/
    __init__.py
    synthesis/
      __init__.py
      state.py          ← SynthesisState TypedDict
      nodes.py          ← all 7 node functions
      graph.py          ← build_synthesis_graph()

recap/
  templates/
    email/
      weekly_digest.html    ← HTML digest template
      weekly_digest.txt     ← plain text fallback

tests/
  aiapi/
    unit/
      test_synthesis_nodes.py   ← unit tests per node (no LLM calls mocked)
  recap/
    integration/
      test_weekly_digest_task.py
```

---

## LangSmith Observability

LangGraph integrates with LangSmith (LangChain's tracing tool) with two env vars. Free tier
covers development and moderate production volume.

```bash
# recap/.env additions
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<your-langsmith-key>
LANGCHAIN_PROJECT=recapai-weekly-digest
```

With tracing enabled, every graph run is visible in the LangSmith UI: each node's input/output,
latency, token counts, and the retry path when `quality_check` sends the agent back to
`synthesise`.

---

## Testing Strategy

| Layer | What to test | How |
|---|---|---|
| Unit — each node | Input state → output state, no LLM | Mock `AiApiHelper.PerformTask`, use `seeded_articles` fixture |
| Unit — graph routing | Conditional edges fire correctly | Invoke graph with states that trigger each branch |
| Integration — full task | End-to-end with mocked aiapi | `respx` to mock `/process_task`, assert `sent=True` |
| Manual | Actual email delivered | Trigger via profile page button against local SMTP (Mailhog or Mailtrap) |

Node unit tests are the highest value — each node is a pure function (state in → state out) and
can be tested without running the full graph.

---

## Build Sequence

1. **Install dependencies** — add `langgraph` and `langgraph-checkpoint-redis` to
   `requirements.txt`, install in `.venv`.
2. **State + nodes** — implement `state.py` and `nodes.py` with stubs; get unit tests green
   against mocked aiapi.
3. **Graph assembly** — wire `graph.py`, run the graph locally against dev DB with a manual
   `graph.invoke()` call.
4. **RQ task** — add `weekly_digest_task` to `recap/tasks.py`; trigger manually via Flask shell.
5. **Email template** — build `weekly_digest.html`; verify rendering against seed data.
6. **Profile page trigger** — add "Send digest" button to profile; test the full loop end-to-end.
7. **LangSmith tracing** — add env vars, verify traces appear in the dashboard.
8. **Render cron** — add internal endpoint + Render cron job config; deploy and verify.

---

## Open Questions

| Question | Options | Recommendation |
|---|---|---|
| Which LLM for synthesis nodes? | OpenAI (existing), Claude via aiapi | Start with OpenAI (existing pipeline); Claude is the upgrade path |
| Opt-in or opt-out per user? | Always send / user preference field | Add `digest_enabled` bool to User model; default true |
| Digest cadence user preference | Sunday only / user-configurable day | Sunday only for v1; configurable in v2 |
| What if user has zero articles all week? | Skip silently / send "quiet week" email | Skip silently (handled by `assess` node) |
| Human-in-the-loop preview? | Agent pauses, user approves in UI | Strong future feature; LangGraph supports it natively via `interrupt_before` |
