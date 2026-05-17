#!/usr/bin/env python
"""Backfill embeddings for articles classified before vector search was added.

Usage:
    .venv/bin/python scripts/backfill_embeddings.py
    .venv/bin/python scripts/backfill_embeddings.py --dry-run
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recap import create_app, db
from recap.aiapi_helper import AiApiHelper
from recap.article_text import build_article_text
from recap.models import Article

parser = argparse.ArgumentParser(description="Backfill article embeddings via aiapi.")
parser.add_argument("--dry-run", action="store_true", help="Show count only, make no changes.")
args = parser.parse_args()

app = create_app()
with app.app_context():
    articles = (
        db.session.execute(db.select(Article).where(Article.embedding.is_(None)).where(Article.summary.isnot(None)))
        .scalars()
        .all()
    )

    print(f"Articles needing embeddings: {len(articles)}")
    if args.dry_run:
        print("Dry run — no changes made.")
        sys.exit(0)

    ok = 0
    skipped = 0
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
            print(f"  WARNING: no embedding returned for article {article.id}")
            skipped += 1
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(articles)} processed ({ok} ok, {skipped} skipped)")
        time.sleep(0.05)

    print(f"Done. {ok} embeddings stored, {skipped} skipped.")
