#!/usr/bin/env python3
"""
reclassify_articles.py — Re-enqueue classification for unclassified (or all) articles.

Usage (from project root):
    .venv/bin/python scripts/reclassify_articles.py [options]

Options:
    --username TEXT    Target user's username  [default: testuser2]
    --all              Reclassify every article, not just unclassified ones
    --delay FLOAT      Seconds to wait between enqueue calls  [default: 2.0]
    --dry-run          Print articles that would be reclassified without doing it

Examples:
    # Reclassify all unclassified articles for testuser2
    .venv/bin/python scripts/reclassify_articles.py

    # Reclassify ALL articles (including already classified ones)
    .venv/bin/python scripts/reclassify_articles.py --all

    # Dry run to preview what would be reclassified
    .venv/bin/python scripts/reclassify_articles.py --dry-run
"""

import sys
import os
import time
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--username", default="testuser2")
    p.add_argument("--all",      action="store_true",
                   help="Reclassify all articles, not just unclassified ones")
    p.add_argument("--delay",    type=float, default=2.0,
                   help="Seconds between enqueue calls (default: 2.0)")
    p.add_argument("--dry-run",  action="store_true",
                   help="Print articles without enqueuing")
    return p.parse_args()


def main():
    args = parse_args()

    from recap import create_app, db
    import sqlalchemy as sa
    from recap.models import User, Article

    app = create_app()

    with app.app_context():
        user = db.session.scalar(sa.select(User).where(User.username == args.username))
        if user is None:
            print(f"Error: user '{args.username}' not found.")
            sys.exit(1)

        query = sa.select(Article).where(Article.user_id == user.id)
        if not args.all:
            query = query.where(Article.classified == None)
        query = query.order_by(Article.id)

        articles = db.session.scalars(query).all()

        if not articles:
            print(f"No {'unclassified ' if not args.all else ''}articles found for '{args.username}'.")
            return

        label = "all" if args.all else "unclassified"
        print(f"Found {len(articles)} {label} article(s) for '{args.username}'.")

        if args.dry_run:
            print(f"\nDry run — would reclassify:\n")
            for a in articles:
                status = f"classified={a.classified}" if a.classified else "unclassified"
                print(f"  id={a.id:4d}  [{status}]  {a.url_path[:70]}")
            return

        print(f"Enqueuing with {args.delay}s delay between calls...\n")
        for i, article in enumerate(articles, 1):
            app.task_queue.enqueue(
                'recap.tasks.classify_url',
                kwargs={'url': article.url_path, 'user_id': user.id},
                description='url classification',
            )
            print(f"  [{i:4d}/{len(articles)}] enqueued  id={article.id:4d}  {article.url_path[:65]}")
            if i < len(articles):
                time.sleep(args.delay)

        print(f"\nDone — {len(articles)} job(s) enqueued.")


if __name__ == "__main__":
    main()
