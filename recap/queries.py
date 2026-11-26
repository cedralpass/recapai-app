"""Queries shared by the web routes (recap/routes.py) and the REST API (recap/api_v1.py).

Keeping them here means the HTML pages and the iOS app see the same articles and digests.
"""

import sqlalchemy as sa
from flask import current_app

from recap import db
from recap.aiapi_helper import AiApiHelper
from recap.config import Config
from recap.models import Article, DigestRun


def user_article_select(user_id, article_id):
    """SELECT for one article owned by `user_id` (callers pick scalar_one / scalar_one_or_none)."""
    return sa.select(Article).where(Article.id == article_id, Article.user_id == user_id)


def latest_completed_digest(user_id):
    """The user's most recent completed DigestRun, or None."""
    return db.session.scalar(
        sa.select(DigestRun)
        .where(DigestRun.user_id == user_id, DigestRun.status == "completed")
        .order_by(DigestRun.created_at.desc())
    )


def count_articles(user_id, since=None):
    """Number of the user's articles, optionally only those created after `since`."""
    stmt = sa.select(sa.func.count(Article.id)).where(Article.user_id == user_id)
    if since is not None:
        stmt = stmt.where(Article.created > since)
    return db.session.scalar(stmt) or 0


def digest_regenerate_state(digest_run):
    """(bookmarks saved since the digest completed, whether to offer a regenerate)."""
    bookmarks_since = count_articles(digest_run.user_id, since=digest_run.completed_at)
    return bookmarks_since, bookmarks_since >= Config.DIGEST_REGENERATE_THRESHOLD


def semantic_search(user, q, category=None, limit=20):
    """Embed `q` and return the user's closest articles; [] for an empty query or failed embedding."""
    if not q:
        return []
    query_vec = AiApiHelper.EmbedText(q)
    if not query_vec:
        return []
    return user.search_articles(query_vec, limit=limit, category=category)


def job_status_value(job):
    """RQ job status as a plain string ("queued", "finished", …).

    JobStatus is a str Enum, so str(status) gives "JobStatus.FINISHED"; the pollers compare
    against the bare value.
    """
    status = job.get_status(refresh=True)
    return getattr(status, "value", status)


def enqueue_digest(user_id):
    """Queue an on-demand (not emailed) weekly digest for the user; returns the RQ job."""
    return current_app.task_queue.enqueue(
        "recap.tasks.weekly_digest_task",
        user_id,
        False,
        job_timeout=600,
    )
