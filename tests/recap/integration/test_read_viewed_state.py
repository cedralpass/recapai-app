"""Integration tests for article read/viewed state feature."""

from datetime import datetime, timezone

import pytest

from recap import db
from recap.models import Article, User

_NOW = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_article(recap_app, user_id, **kwargs):
    """Helper: create a classified article in the DB and return its id."""
    with recap_app.app_context():
        article = Article(
            url_path=kwargs.get("url_path", "https://example.com/article"),
            title=kwargs.get("title", "Test Title"),
            summary=kwargs.get("summary", "Summary text."),
            author_name=kwargs.get("author_name", "Author"),
            category=kwargs.get("category", "Tech"),
            classified=kwargs.get("classified", _NOW),
            user_id=user_id,
            is_viewed=kwargs.get("is_viewed", False),
            is_read=kwargs.get("is_read", False),
        )
        db.session.add(article)
        db.session.commit()
        return article.id


@pytest.mark.integration
@pytest.mark.recap
class TestArticleModelFields:
    def test_new_article_defaults_to_not_viewed(self, recap_app, test_user):
        """is_viewed defaults to False on new articles."""
        with recap_app.app_context():
            article = Article(url_path="https://example.com/x", user_id=test_user.id)
            db.session.add(article)
            db.session.commit()
            assert article.is_viewed is False

    def test_new_article_defaults_to_not_read(self, recap_app, test_user):
        """is_read defaults to False on new articles."""
        with recap_app.app_context():
            article = Article(url_path="https://example.com/y", user_id=test_user.id)
            db.session.add(article)
            db.session.commit()
            assert article.is_read is False

    def test_get_articles_excludes_read_by_default(self, recap_app, test_user):
        """get_articles(include_read=False) omits articles where is_read=True."""
        with recap_app.app_context():
            user = db.session.get(User, test_user.id)
            db.session.add(Article(url_path="https://example.com/unread", user_id=test_user.id, is_read=False))
            db.session.add(Article(url_path="https://example.com/read", user_id=test_user.id, is_read=True))
            db.session.commit()
            paginator = user.get_articles(include_read=False)
            urls = [a.url_path for a in paginator.items]
            assert "https://example.com/unread" in urls
            assert "https://example.com/read" not in urls

    def test_get_articles_includes_read_when_requested(self, recap_app, test_user):
        """get_articles(include_read=True) returns all articles."""
        with recap_app.app_context():
            user = db.session.get(User, test_user.id)
            db.session.add(Article(url_path="https://example.com/unread2", user_id=test_user.id, is_read=False))
            db.session.add(Article(url_path="https://example.com/read2", user_id=test_user.id, is_read=True))
            db.session.commit()
            paginator = user.get_articles(include_read=True)
            urls = [a.url_path for a in paginator.items]
            assert "https://example.com/unread2" in urls
            assert "https://example.com/read2" in urls


@pytest.mark.integration
@pytest.mark.recap
class TestShowRouteMarksViewed:
    def test_visiting_show_marks_article_as_viewed(self, authenticated_client, recap_app, test_user):
        """GET /<id>/show sets is_viewed=True on the article."""
        article_id = _make_article(recap_app, test_user.id)

        authenticated_client.get(f"/{article_id}/show")

        with recap_app.app_context():
            article = db.session.get(Article, article_id)
            assert article.is_viewed is True

    def test_show_does_not_mark_read(self, authenticated_client, recap_app, test_user):
        """GET /<id>/show does not set is_read=True."""
        article_id = _make_article(recap_app, test_user.id)

        authenticated_client.get(f"/{article_id}/show")

        with recap_app.app_context():
            article = db.session.get(Article, article_id)
            assert article.is_read is False

    def test_show_idempotent_viewed(self, authenticated_client, recap_app, test_user):
        """GET /<id>/show twice does not raise an error."""
        article_id = _make_article(recap_app, test_user.id)
        authenticated_client.get(f"/{article_id}/show")
        response = authenticated_client.get(f"/{article_id}/show")
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.recap
class TestReadArticleRoute:
    def test_read_article_marks_read_and_redirects(self, authenticated_client, recap_app, test_user):
        """GET /articles/<id>/read sets is_read=True and redirects to article url."""
        article_id = _make_article(recap_app, test_user.id, url_path="https://example.com/the-article")

        response = authenticated_client.get(f"/articles/{article_id}/read")

        assert response.status_code == 302
        assert response.headers["Location"] == "https://example.com/the-article"

        with recap_app.app_context():
            article = db.session.get(Article, article_id)
            assert article.is_read is True

    def test_read_article_requires_login(self, recap_client, recap_app, test_user):
        """Unauthenticated GET /articles/<id>/read redirects to login."""
        article_id = _make_article(recap_app, test_user.id)
        response = recap_client.get(f"/articles/{article_id}/read")
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_read_article_idempotent(self, authenticated_client, recap_app, test_user):
        """Calling read route on an already-read article doesn't error."""
        article_id = _make_article(recap_app, test_user.id, is_read=True)
        response = authenticated_client.get(f"/articles/{article_id}/read")
        assert response.status_code == 302


@pytest.mark.integration
@pytest.mark.recap
class TestToggleReadRoute:
    def test_toggle_read_false_to_true(self, authenticated_client, recap_app, test_user):
        """POST /articles/<id>/toggle-read flips is_read from False to True."""
        article_id = _make_article(recap_app, test_user.id, is_read=False)

        authenticated_client.post(f"/articles/{article_id}/toggle-read")

        with recap_app.app_context():
            article = db.session.get(Article, article_id)
            assert article.is_read is True

    def test_toggle_read_true_to_false(self, authenticated_client, recap_app, test_user):
        """POST /articles/<id>/toggle-read flips is_read from True to False."""
        article_id = _make_article(recap_app, test_user.id, is_read=True)

        authenticated_client.post(f"/articles/{article_id}/toggle-read")

        with recap_app.app_context():
            article = db.session.get(Article, article_id)
            assert article.is_read is False

    def test_toggle_read_redirects(self, authenticated_client, recap_app, test_user):
        """POST /articles/<id>/toggle-read redirects (302) after toggling."""
        article_id = _make_article(recap_app, test_user.id)
        response = authenticated_client.post(f"/articles/{article_id}/toggle-read")
        assert response.status_code == 302

    def test_toggle_read_requires_login(self, recap_client, recap_app, test_user):
        """Unauthenticated POST redirects to login."""
        article_id = _make_article(recap_app, test_user.id)
        response = recap_client.post(f"/articles/{article_id}/toggle-read")
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]


@pytest.mark.integration
@pytest.mark.recap
class TestIndexReadFilter:
    def test_index_excludes_read_articles_by_default(self, authenticated_client, recap_app, test_user):
        """GET / does not show read articles unless ?include_read=true."""
        _make_article(recap_app, test_user.id, url_path="https://example.com/unread-a", title="Unread Article")
        _make_article(
            recap_app, test_user.id, url_path="https://example.com/read-a", title="Read Article", is_read=True
        )

        response = authenticated_client.get("/")
        assert b"Unread Article" in response.data
        assert b"Read Article" not in response.data

    def test_index_includes_read_articles_with_param(self, authenticated_client, recap_app, test_user):
        """GET /?include_read=true shows both read and unread articles."""
        _make_article(recap_app, test_user.id, url_path="https://example.com/unread-b", title="Unread B")
        _make_article(recap_app, test_user.id, url_path="https://example.com/read-b", title="Read B", is_read=True)

        response = authenticated_client.get("/?include_read=true")
        assert b"Unread B" in response.data
        assert b"Read B" in response.data

    def test_index_renders_include_read_checkbox(self, authenticated_client, recap_app, test_user):
        """GET / renders a checkbox for toggling read article visibility."""
        response = authenticated_client.get("/")
        assert b"include_read" in response.data
        assert b"Include read articles" in response.data
