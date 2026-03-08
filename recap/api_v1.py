from flask import Blueprint, request, jsonify, current_app
import sqlalchemy as sa
from recap import db
from recap.models import User, Article

bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')


def _get_user_from_bearer_token():
    """Extract and validate a Bearer token from the Authorization header.

    Returns the matching User or None if the token is missing or invalid.
    """
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[len('Bearer '):]
    if not token:
        return None
    return db.session.execute(
        sa.select(User).where(User.api_token == token)
    ).scalar_one_or_none()


@bp.route('/articles', methods=['POST'])
def create_article():
    """Save a URL to the authenticated user's reading list and queue classification.

    Authorization: Bearer <api_token>
    Body (JSON): {"url": "https://..."}

    Returns:
        201  {"status": "queued", "article_id": <int>}
        400  {"error": "..."}   bad request
        401  {"error": "..."}   missing / invalid token
    """
    user = _get_user_from_bearer_token()
    if user is None:
        return jsonify({'error': 'Invalid or missing API token'}), 401

    body = request.get_json(silent=True)
    if body is None:
        return jsonify({'error': 'Request body must be valid JSON'}), 400

    url = body.get('url', '').strip()
    if not url:
        return jsonify({'error': 'url is required'}), 400

    article = Article(url_path=url, user=user)
    db.session.add(article)
    db.session.commit()

    current_app.task_queue.enqueue(
        'recap.tasks.classify_url',
        description='using AI to classify url',
        kwargs={'url': url, 'user_id': user.id},
    )

    return jsonify({'status': 'queued', 'article_id': article.id}), 201
