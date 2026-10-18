import urllib.parse
from datetime import datetime, timezone

import sqlalchemy as sa
from flask import Blueprint, current_app, jsonify, request

from recap import db
from recap.aiapi_helper import extract_article_text
from recap.models import Article, User

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Page HTML from the extension can be large (Medium pages are ~0.5–1.5 MB); cap the request body.
MAX_BODY_BYTES = 5 * 1024 * 1024


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
