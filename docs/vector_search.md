# Vector Search

RecapAI uses pgvector on Neon Postgres to provide semantic search over a user's article library.
Users type a natural-language phrase into the nav search bar and get articles ranked by cosine
similarity to the query embedding.

---

## Architecture

All OpenAI calls (classification, taxonomy, and embeddings) flow through the `aiapi` microservice.
The `recap` app never calls OpenAI directly.

```
User types query
      │
      ▼
GET /search?q=...  (recap)
      │  POST aiapi/embed → OpenAI text-embedding-3-small → 1536-dim vector
      │  SELECT ... ORDER BY embedding <=> :query_vec WHERE user_id = :uid LIMIT 20
      ▼
Ranked article cards

New article saved
      │
      ▼
RQ classify_url task
      │  POST aiapi/classify_url → sets title, summary, category, topics
      │  POST aiapi/embed        → stores vector(1536) in article.embedding
      ▼
Postgres — article row complete
```

---

## Key files

| File | Purpose |
|------|---------|
| `aiapi/embeddings.py` | `POST /embed` endpoint — accepts text, returns 1536-float vector via OpenAI |
| `recap/article_text.py` | Builds the string to embed from an Article (title, summary, category, topics) |
| `recap/aiapi_helper.py` | `AiApiHelper.EmbedText()` — calls aiapi `/embed`, returns vector or `None` on error |
| `recap/models.py` | `Article.embedding` column (`Vector(1536)`) + `User.search_articles()` cosine query |
| `recap/routes.py` | `GET /search` route |
| `recap/templates/search.html` | Search results page |
| `recap/templates/base.html` | Nav search bar (authenticated users only) |
| `migrations/versions/a1b2c3d4e5f6_add_article_embedding.py` | Enables pgvector extension, adds column and HNSW index |

---

## Embedding model

- **Model:** `text-embedding-3-small`
- **Dimensions:** 1536
- **Index:** HNSW (`m=16, ef_construction=64`) with cosine distance ops
- **Cost:** ~$0.00002 per article at classify time; <$0.000001 per search query

---

## Database setup

The migration (`a1b2c3d4e5f6`) handles everything automatically on deploy:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE article ADD COLUMN embedding vector(1536);
CREATE INDEX article_embedding_hnsw_idx ON article
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

**Neon:** pgvector is available on all Neon Postgres instances — no dashboard configuration needed.

**Local Docker:** requires `pgvector/pgvector:pg16` image (not the standard `postgres:16-alpine`).
See `devops/postgres_docker.txt` for the upgrade procedure.

---

## Backfilling existing articles

Articles classified before vector search was added have `embedding IS NULL`. To backfill, run this
from the Render Shell tab (or locally against your DB):

```python
python - <<'EOF'
import os, sys, time
sys.path.insert(0, '/app')
from recap import create_app, db
from recap.aiapi_helper import AiApiHelper
from recap.article_text import build_article_text
from recap.models import Article

app = create_app()
with app.app_context():
    articles = db.session.execute(
        db.select(Article)
          .where(Article.embedding.is_(None))
          .where(Article.summary.isnot(None))
    ).scalars().all()
    print(f"Articles needing embeddings: {len(articles)}")
    ok = skipped = 0
    for i, article in enumerate(articles):
        text = build_article_text(article)
        if not text:
            skipped += 1
            continue
        embedding = AiApiHelper.EmbedText(text)
        if embedding:
            article.embedding = embedding
            db.session.commit()
            ok += 1
        else:
            print(f"  WARNING: no embedding for article {article.id}")
            skipped += 1
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(articles)} ({ok} ok, {skipped} skipped)")
        time.sleep(0.05)
    print(f"Done. {ok} stored, {skipped} skipped.")
EOF
```

The script is not included in the Docker image — paste it directly into the Render Shell. New
articles are embedded automatically at classify time, so the backfill is a one-time operation.

---

## Deploying to a new environment

1. Ensure the Postgres instance supports pgvector (Neon: yes by default; self-hosted: install the
   extension manually).
2. Run `flask db upgrade` — the migration enables the extension and creates the column and index.
3. Run the backfill script above for any articles that pre-date this feature.

---

## Design notes

See `tech_design/vector-search.md` for the original design doc — motivation, approach comparison
(pgvector vs OpenAI vector stores), cost model, and test plan.
