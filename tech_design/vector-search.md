# Article Vector Search

## Problem

Users with large reading lists (50+ articles across 10+ categories with sub-categories) have no way
to find a specific article except by paging through the list or clicking a category filter. Text
search over titles alone misses articles where only the summary or key topics match what the user
remembers.

## Goal

Full-article semantic search: a user types a phrase ("serverless edge functions" or "that article
about burnout in startups") and gets a ranked list of matching articles from their own library,
ordered by relevance.

---

## Approach: pgvector on Neon

Store a single `vector(1536)` embedding per article in the existing Postgres database. Query with
cosine similarity using the `<=>` operator, filtered by `user_id` so each user only searches their
own library.

**Why not OpenAI vector stores:**
- Requires keeping a second system in sync with Postgres
- Per-search API call (latency + cost)
- Multi-tenant user isolation is awkward (vector stores aren't designed for per-user namespacing)

**Why pgvector on Neon:**
- Data already lives in Postgres — no sync layer
- Search composes naturally with existing SQLAlchemy filters (user, category, date)
- Embedding cost is write-time only (`text-embedding-3-small` is very cheap: ~$0.02 per 1M tokens)
- Neon supports HNSW indexes, which give fast approximate nearest-neighbour at scale

---

## Embedding content

Concatenate these fields into a single string for embedding at classify time:

```
{title}. {summary} Category: {category}. Sub-categories: {sub_categories_flat}. Topics: {key_topics_flat}.
```

This gives the embedding semantic coverage over everything the user might search for. Key topics
and sub-categories are stored as JSON arrays — flatten them to comma-separated strings before
concatenating.

**Model:** `text-embedding-3-small` — 1536 dimensions, fast, cheap. Already available via the
existing `OPENAI_API_KEY`.

---

## Implementation plan

### Step 1 — Enable pgvector on Neon

Run once on the Neon console or via psql:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Neon supports pgvector natively; no instance restart required.

### Step 2 — Alembic migration

New migration file: `migrations/versions/xxxx_add_article_embedding.py`

```python
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("article", sa.Column("embedding", Vector(1536), nullable=True))
    op.execute("""
        CREATE INDEX article_embedding_hnsw_idx
        ON article
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

def downgrade():
    op.execute("DROP INDEX IF EXISTS article_embedding_hnsw_idx")
    op.drop_column("article", "embedding")
```

`nullable=True` is required because existing articles have no embedding yet (backfilled separately).

**New dependency:** add `pgvector` to `requirements.txt`.

### Step 3 — Model change (`recap/models.py`)

Add the column to `Article`:

```python
from pgvector.sqlalchemy import Vector

class Article(db.Model):
    ...
    embedding: so.Mapped[Optional[list]] = so.mapped_column(Vector(1536), nullable=True)
```

Add a search method to `User`:

```python
def search_articles(self, query_embedding, limit=20, category=None):
    stmt = (
        sa.select(Article)
        .where(Article.user_id == self.id)
        .where(Article.embedding.isnot(None))
        .order_by(Article.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    if category:
        stmt = stmt.where(Article.category == category)
    return db.session.execute(stmt).scalars().all()
```

### Step 4 — Embed endpoint in aiapi (`aiapi/embeddings.py`)

All OpenAI calls live in the aiapi microservice. Add a new blueprint with a single endpoint that
accepts text and returns a vector. This follows the same pattern as `classify_url` and
`process_task`.

```python
# aiapi/embeddings.py
import openai
from flask import Blueprint, jsonify, request
from aiapi.classify import login_required

bp = Blueprint("embeddings", __name__)

EMBEDDING_MODEL = "text-embedding-3-small"

@bp.route("/embed", methods=["POST"])
@login_required
def embed():
    text = request.form.get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    client = openai.OpenAI()
    response = client.embeddings.create(input=text, model=EMBEDDING_MODEL)
    return jsonify({"embedding": response.data[0].embedding})
```

Register the blueprint in `aiapi/__init__.py`:

```python
from aiapi import embeddings
app.register_blueprint(embeddings.bp)
```

### Step 4b — Article text builder (`recap/article_text.py`)

A small helper in recap that builds the string to embed from an Article. No OpenAI dependency —
this belongs in recap because it knows the Article model.

```python
def build_article_text(article):
    topics = ", ".join(article.get_key_topics_json() or [])
    subs = ", ".join(article.get_sub_categories_json() or [])
    parts = [
        article.title or "",
        article.summary or "",
        f"Category: {article.category}" if article.category else "",
        f"Sub-categories: {subs}" if subs else "",
        f"Topics: {topics}" if topics else "",
    ]
    return ". ".join(p for p in parts if p).strip()
```

### Step 4c — `AiApiHelper.EmbedText()` (`recap/aiapi_helper.py`)

Extend `AiApiHelper` with a new method that calls the aiapi `/embed` endpoint, matching the
existing `ClassifyUrl` / `PerformTask` pattern:

```python
@staticmethod
def EmbedText(text: str) -> list[float] | None:
    ai_url = env("RECAP_AI_API_URL") + "/embed"
    response = httpx.post(ai_url, data={"text": text}, ...)
    if response.status_code == 200:
        return response.json()["embedding"]
    return None
```

### Step 5 — Generate embedding after classification (`recap/tasks.py`)

In the RQ `classify_url` task, after `save_classification_result(...)`:

```python
from recap.article_text import build_article_text
from recap.aiapi_helper import AiApiHelper

# after article.category, article.summary, etc. are set:
text = build_article_text(article)
if text:
    embedding = AiApiHelper.EmbedText(text)
    if embedding:
        article.embedding = embedding
db.session.commit()
```

The RQ worker is already the async boundary between the web app and AI work. The aiapi call here
is synchronous within the job — identical to how `ClassifyUrl` works. `text-embedding-3-small`
adds ~100ms to the job, which runs entirely in the background.

### Step 6 — Backfill script (`scripts/backfill_embeddings.py`)

One-time script to generate embeddings for all existing articles that lack one. Routes through
aiapi so all OpenAI calls remain in one place:

```python
#!/usr/bin/env python
"""Backfill embeddings for articles that were classified before vector search was added."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from recap import create_app, db
from recap.models import Article
from recap.article_text import build_article_text
from recap.aiapi_helper import AiApiHelper
import time

app = create_app()
with app.app_context():
    articles = db.session.execute(
        db.select(Article).where(Article.embedding.is_(None)).where(Article.summary.isnot(None))
    ).scalars().all()

    print(f"Backfilling {len(articles)} articles...")
    for i, article in enumerate(articles):
        text = build_article_text(article)
        if text:
            embedding = AiApiHelper.EmbedText(text)
            if embedding:
                article.embedding = embedding
                db.session.commit()
        if i % 10 == 0:
            print(f"  {i}/{len(articles)}")
        time.sleep(0.05)  # stay well under aiapi rate limits

    print("Done.")
```

Run with:
```bash
.venv/bin/python scripts/backfill_embeddings.py
```

At 53 seed articles this completes in under 10 seconds. At 1000 articles, ~1 minute.

### Step 7 — Search route (`recap/routes.py`)

The search route embeds the query via aiapi, then queries Postgres directly. The aiapi call is
synchronous and fast (~100ms), so no RQ job is needed for search.

```python
from recap.aiapi_helper import AiApiHelper

@bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    category = request.args.get("category")
    results = []

    if q:
        query_vec = AiApiHelper.EmbedText(q)
        if query_vec:
            results = current_user.search_articles(query_vec, limit=20, category=category or None)

    return render_template(
        "search.html",
        query=q,
        results=results,
        active_category=category,
        categories=current_user.get_categories(),
    )
```

### Step 8 — Search UI

**Search bar** — add to the nav in `base.html` (desktop: inline in top bar, mobile: below nav):

```html
<form action="{{ url_for('routes.search') }}" method="get" class="relative">
    <input type="text" name="q" value="{{ request.args.get('q', '') }}"
           placeholder="Search your articles..."
           class="w-64 rounded-lg border border-gray-200 px-3 py-1.5 text-sm
                  focus:outline-none focus:ring-2 focus:ring-blue-500">
</form>
```

**`recap/templates/search.html`** — inherits `base.html`, reuses the existing article card
component. Shows a "No results" empty state if `q` is set but `results` is empty. Shows a prompt
("What are you looking for?") if `q` is blank.

Results render identically to the index article list — same card markup, same read/unread state,
same mark-as-read button — so no new components are needed.

---

## Data flow summary

```
New article saved
      │
      ▼
RQ classify_url task
      │  (existing) POST aiapi/classify_url → OpenAI → sets title, summary, category, sub_categories, key_topics
      │  (new)      POST aiapi/embed         → OpenAI → stores vector(1536) in article.embedding
      ▼
Postgres (Neon) — article row complete

User types in search bar
      │
      ▼
GET /search?q=...  (recap app)
      │  POST aiapi/embed → OpenAI → query vector
      │  SELECT ... ORDER BY embedding <=> :query_vec WHERE user_id = :uid LIMIT 20
      ▼
Ranked results rendered as article cards
```

All OpenAI calls — classification, taxonomy, and embeddings — flow through aiapi. The recap app
never imports `openai` directly.

---

## Cost model

| Operation | Model | Cost |
|-----------|-------|------|
| Embed one article at classify time | text-embedding-3-small | ~$0.00002 |
| Embed one search query | text-embedding-3-small | <$0.000001 |
| Backfill 53 articles | text-embedding-3-small | ~$0.001 total |

At 1000 articles and 10 searches/day, monthly cost is well under $0.01.

---

## Test plan

### Unit — `tests/recap/unit/test_article_text.py`

| Test | What it checks |
|------|----------------|
| `test_build_article_text_full` | Concatenates all fields correctly |
| `test_build_article_text_missing_fields` | Handles `None` summary / topics gracefully |

### Unit — `tests/recap/unit/test_models.py`

| Test | What it checks |
|------|----------------|
| `test_search_articles_filters_by_user` | `search_articles` only returns articles owned by the querying user |
| `test_search_articles_filters_by_category` | Category filter applied on top of vector search |

Use a pre-computed fixture embedding (a list of 1536 floats saved in `tests/fixtures/`) rather
than calling aiapi. The model method just does SQL — no AI call to mock.

### Unit — `tests/aiapi/unit/test_embed_endpoint.py`

| Test | What it checks |
|------|----------------|
| `test_embed_returns_vector` | `POST /embed` with valid text returns a 1536-element list |
| `test_embed_missing_text_returns_400` | Empty `text` field returns HTTP 400 |
| `test_embed_requires_auth` | Unauthenticated request returns 401 |

Mock `openai.OpenAI` at the aiapi unit test level — same approach as existing aiapi tests.

### Integration — `tests/recap/integration/test_search.py`

| Test | What it checks |
|------|----------------|
| `test_search_returns_relevant_article` | Mock `AiApiHelper.EmbedText` to return a fixture vector; seed an article with that embedding; confirm it appears in results |
| `test_search_empty_query_shows_prompt` | `GET /search` with no `q` returns 200 and no article cards |
| `test_search_no_results_shows_empty_state` | Query that matches nothing shows empty state message |
| `test_search_requires_login` | `GET /search` unauthenticated redirects to login |

Mock `AiApiHelper.EmbedText` with `respx` (matching the existing `AiApiHelper` mock pattern) so
integration tests never hit aiapi or OpenAI.

---

## Out of scope

- Hybrid search (BM25 full-text + vector reranking) — pgvector cosine similarity is sufficient for
  personal library scale (< 10k articles per user)
- Caching query embeddings — search volume per user is low enough that per-request embedding calls
  are acceptable
- Search result highlighting — the article card summary is shown as-is; snippet extraction adds
  complexity without much benefit at this scale
- Cross-user or admin search
