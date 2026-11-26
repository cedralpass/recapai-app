import urllib.parse
from datetime import datetime, timezone
from functools import wraps

import sqlalchemy as sa
from flask import Blueprint, current_app, g, jsonify, request

from recap import db
from recap.aiapi_helper import extract_article_text
from recap.config import Config
from recap.models import Article, User
from recap.queries import (
    count_articles,
    digest_regenerate_state,
    enqueue_digest,
    latest_completed_digest,
    semantic_search,
    user_article_select,
)

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Page HTML from the extension can be large (Medium pages are ~0.5–1.5 MB); cap the request body.
MAX_BODY_BYTES = 5 * 1024 * 1024
# Upper bound on ?per_page= for the article list.
MAX_PER_PAGE = 50


def _get_user_from_bearer_token():
    """Extract and validate a Bearer token from the Authorization header.

    Returns the matching User or None if the token is missing or invalid.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer ") :]
    if not token:
        return None
    return db.session.execute(sa.select(User).where(User.api_token == token)).scalar_one_or_none()


def token_required(view):
    """Require a valid Bearer token; the user is available as g.api_user. 401 JSON otherwise."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        user = _get_user_from_bearer_token()
        if user is None:
            return jsonify({"error": "Invalid or missing API token"}), 401
        g.api_user = user
        return view(*args, **kwargs)

    return wrapper


def _iso(dt):
    """ISO-8601 UTC timestamp with a Z suffix (naive datetimes are stored as UTC)."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.replace(microsecond=0).isoformat() + "Z"


def _key_topics(article):
    try:
        topics = article.get_key_topics_json()
    except (TypeError, ValueError):
        return []
    return topics if isinstance(topics, list) else []


def article_json(article):
    """Public JSON for an article. Never includes content_text (private extracted text)."""
    return {
        "id": article.id,
        "url": article.url_path,
        "title": article.title,
        "summary": article.summary,
        "author": article.author_name,
        "category": article.category,
        "key_topics": _key_topics(article),
        "source": article.site_name,
        "created": _iso(article.created),
        "read": bool(article.is_read),
        "summary_available": bool(article.summary) and article.url_only_reason is None,
    }


def _get_owned_article(article_id):
    return db.session.execute(user_article_select(g.api_user.id, article_id)).scalar_one_or_none()


def _not_found():
    return jsonify({"error": "Article not found"}), 404


@bp.route("/articles", methods=["POST"])
def create_article():
    """Save a URL to the authenticated user's reading list and queue classification.

    Authorization: Bearer <api_token>
    X-Recap-Client: chrome-extension/<version>   (optional)
    Body (JSON): {"url": "https://...", "html": "<!doctype html>..."}   html optional

    When html is sent, the article text is extracted and stored, and classification uses it
    instead of crawling the URL (which some sites block). Saving a URL that is already in the
    list updates that article instead of creating a duplicate.

    Returns:
        201  {"status": "queued", "article_id": <int>, "content_captured": <bool>}   new article
        200  {"status": "updated", ...}   existing article, new text captured → reclassified
        200  {"status": "exists", ...}    existing article, nothing new → no job queued
        400  {"error": "..."}   bad request
        401  {"error": "..."}   missing / invalid token
        413  {"error": "..."}   body larger than 5 MB
    """
    user = _get_user_from_bearer_token()
    if user is None:
        return jsonify({"error": "Invalid or missing API token"}), 401

    if request.content_length and request.content_length > MAX_BODY_BYTES:
        return jsonify({"error": "Request too large (max 5 MB)"}), 413

    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    url = body.get("url", "").strip()
    if not url:
        return jsonify({"error": "url is required"}), 400

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return jsonify({"error": "Invalid URL"}), 400

    if parsed.scheme != "https":
        return jsonify({"error": "Only HTTPS URLs are accepted. Please update the link to start with https://"}), 400

    if not parsed.hostname:
        return jsonify({"error": "Invalid URL — hostname is missing"}), 400

    html = body.get("html")
    content = extract_article_text(html) if isinstance(html, str) and html else None

    article, created = Article.upsert_for_user(url, user)
    if len(article.url_path) > 255:
        db.session.rollback()
        return jsonify({"error": "URL is too long (max 255 characters after removing tracking parameters)"}), 400
    if request.headers.get("X-Recap-Client"):
        user.extension_last_seen = datetime.now(timezone.utc)
    if content:
        article.content_text = content
        article.content_source = "extension"
    db.session.commit()

    result = {"article_id": article.id, "content_captured": bool(content)}
    if not created and not content:
        return jsonify({"status": "exists", **result}), 200

    current_app.task_queue.enqueue(
        "recap.tasks.classify_url",
        description="using AI to classify url",
        kwargs={"url": article.url_path, "user_id": user.id, "article_id": article.id},
    )
    if created:
        return jsonify({"status": "queued", **result}), 201
    return jsonify({"status": "updated", **result}), 200


@bp.route("/articles", methods=["GET"])
@token_required
def list_articles():
    """Paginated articles, newest first.

    Query: page (default 1), per_page (default ARTICLES_PER_PAGE, max 50), category (optional)
    Returns 200 {"articles": [...], "page": <int>, "has_next": <bool>}
    """
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    per_page = request.args.get("per_page", Config.ARTICLES_PER_PAGE, type=int) or Config.ARTICLES_PER_PAGE
    per_page = min(max(per_page, 1), MAX_PER_PAGE)
    category = request.args.get("category", "").strip() or None
    paginator = g.api_user.get_articles(page=page, per_page=per_page, category=category, unread_first=False)
    return jsonify(
        {
            "articles": [article_json(a) for a in paginator.items],
            "page": page,
            "has_next": paginator.has_next,
        }
    )


@bp.route("/articles/search", methods=["GET"])
@token_required
def search_articles():
    """Semantic search over the user's articles (top 20).

    Query: q (required for results), category (optional)
    Returns 200 {"articles": [...], "query": "<q>"}; empty list for a blank query.
    """
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip() or None
    results = semantic_search(g.api_user, q, category=category)
    return jsonify({"articles": [article_json(a) for a in results], "query": q})


@bp.route("/articles/<int:article_id>", methods=["GET"])
@token_required
def get_article(article_id):
    """One article. 404 if it doesn't exist or belongs to another user."""
    article = _get_owned_article(article_id)
    if article is None:
        return _not_found()
    return jsonify(article_json(article))


@bp.route("/articles/<int:article_id>/read", methods=["POST"])
@token_required
def set_article_read(article_id):
    """Set read state. Body {"read": true|false}; with no "read" key the state is toggled."""
    article = _get_owned_article(article_id)
    if article is None:
        return _not_found()
    body = request.get_json(silent=True) or {}
    read = body.get("read")
    if read is None:
        article.is_read = not article.is_read
    elif isinstance(read, bool):
        article.is_read = read
    else:
        return jsonify({"error": "read must be true or false"}), 400
    db.session.commit()
    return jsonify(article_json(article))


@bp.route("/articles/<int:article_id>", methods=["DELETE"])
@token_required
def delete_article(article_id):
    """Delete an article. Returns 200 {"status": "deleted", "id": <int>}."""
    article = _get_owned_article(article_id)
    if article is None:
        return _not_found()
    db.session.delete(article)
    db.session.commit()
    return jsonify({"status": "deleted", "id": article_id})


@bp.route("/categories", methods=["GET"])
@token_required
def list_categories():
    """Categories with article counts, largest first: {"categories": [{"name", "count"}]}.

    Unclassified articles (no category yet) are left out.
    """
    groupings = g.api_user.get_categories()
    return jsonify({"categories": [{"name": name, "count": count} for name, count in groupings if name]})


@bp.route("/digest/latest", methods=["GET"])
@token_required
def latest_digest():
    """Latest completed digest; marks it opened on first fetch.

    Query: mark_opened=false peeks without setting opened_at (the iOS app uses it for the tab dot).

    Returns 200 {id, week_start, article_count, cluster_count, digest_html, bookmarks_since,
    show_regenerate, was_unread} or 404 {"status": "none", "articles_since_last": <int>}.
    """
    user = g.api_user
    digest_run = latest_completed_digest(user.id)
    if digest_run is None:
        return jsonify({"status": "none", "articles_since_last": count_articles(user.id)}), 404
    was_unread = digest_run.opened_at is None
    mark_opened = request.args.get("mark_opened", "true").lower() != "false"
    if was_unread and mark_opened:
        digest_run.opened_at = datetime.now(timezone.utc)
        db.session.commit()
    bookmarks_since, show_regenerate = digest_regenerate_state(digest_run)
    return jsonify(
        {
            "id": digest_run.id,
            "week_start": digest_run.week_start.date().isoformat() if digest_run.week_start else None,
            "article_count": digest_run.article_count,
            "cluster_count": digest_run.cluster_count,
            "digest_html": digest_run.digest_html,
            "bookmarks_since": bookmarks_since,
            "show_regenerate": show_regenerate,
            "was_unread": was_unread,
        }
    )


@bp.route("/digest/generate", methods=["POST"])
@token_required
def generate_digest():
    """Queue an on-demand digest. Returns 202 {"status": "queued", "job_id": "<id>"}."""
    job = enqueue_digest(g.api_user.id)
    return jsonify({"status": "queued", "job_id": job.id}), 202


@bp.route("/digest/job/<job_id>", methods=["GET"])
@token_required
def digest_job(job_id):
    """Poll a digest job: {"status": "queued|started|finished|failed|..."}.

    404 {"status": "not_found"} if the job is unknown or was queued for another user.
    """
    job = current_app.task_queue.fetch_job(job_id)
    is_users_digest_job = (
        job is not None
        and job.func_name == "recap.tasks.weekly_digest_task"
        and bool(job.args)
        and job.args[0] == g.api_user.id
    )
    if not is_users_digest_job:
        return jsonify({"status": "not_found"}), 404
    status = job.get_status(refresh=True)
    # JobStatus is a str Enum; str() would give "JobStatus.FINISHED", so send the value.
    return jsonify({"status": getattr(status, "value", status)})
