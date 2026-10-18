import pytest
import sqlalchemy as sa

from recap import db
from recap.models import Article, User


@pytest.mark.integration
@pytest.mark.recap
class TestPostArticleApi:
    def test_returns_401_without_auth_header(self, recap_client):
        """Request with no Authorization header returns 401."""
        response = recap_client.post(
            "/api/v1/articles",
            json={"url": "https://example.com/article"},
        )
        assert response.status_code == 401

    def test_returns_401_with_invalid_token(self, recap_client):
        """Request with a token that matches no user returns 401."""
        response = recap_client.post(
            "/api/v1/articles",
            json={"url": "https://example.com/article"},
            headers={"Authorization": "Bearer notarealtoken"},
        )
        assert response.status_code == 401

    def test_returns_400_when_url_missing(self, recap_client, test_user, recap_app):
        """Request with a valid token but no url field returns 400."""
        with recap_app.app_context():
            token = test_user.get_or_create_api_token()

        response = recap_client.post(
            "/api/v1/articles",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert b"url" in response.data

    def test_returns_400_when_body_is_not_json(self, recap_client, test_user, recap_app):
        """Non-JSON request body returns 400."""
        with recap_app.app_context():
            token = test_user.get_or_create_api_token()

        response = recap_client.post(
            "/api/v1/articles",
            data="not json",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "text/plain",
            },
        )
        assert response.status_code == 400

    def test_returns_201_and_queues_job(self, recap_client, test_user, recap_app, mocker):
        """Valid request creates an article and returns 201 with article_id."""
        mock_job = mocker.MagicMock()
        mock_job.id = "test-job-abc"
        mocker.patch.object(recap_app.task_queue, "enqueue", return_value=mock_job)

        with recap_app.app_context():
            token = test_user.get_or_create_api_token()

        response = recap_client.post(
            "/api/v1/articles",
            json={"url": "https://example.com/test-article"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "queued"
        assert "article_id" in data

    def test_creates_article_record_in_db(self, recap_client, test_user, recap_app, mocker):
        """Valid request persists an Article row linked to the token owner."""
        mock_job = mocker.MagicMock()
        mock_job.id = "test-job-xyz"
        mocker.patch.object(recap_app.task_queue, "enqueue", return_value=mock_job)

        url = "https://example.com/db-article"
        with recap_app.app_context():
            token = test_user.get_or_create_api_token()
            user_id = test_user.id

        recap_client.post(
            "/api/v1/articles",
            json={"url": url},
            headers={"Authorization": f"Bearer {token}"},
        )

        with recap_app.app_context():
            article = Article.get_article_by_url_path(url, user_id)
            assert article is not None
            assert article.url_path == url
            assert article.user_id == user_id

    def test_returns_400_for_http_url(self, recap_client, test_user, recap_app):
        """http:// URLs are rejected with a 400 and a helpful error message."""
        with recap_app.app_context():
            token = test_user.get_or_create_api_token()

        response = recap_client.post(
            "/api/v1/articles",
            json={"url": "http://example.com/article"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "HTTPS" in data["error"]

    def test_returns_400_for_non_url_string(self, recap_client, test_user, recap_app):
        """Strings that aren't URLs are rejected with a 400."""
        with recap_app.app_context():
            token = test_user.get_or_create_api_token()

        response = recap_client.post(
            "/api/v1/articles",
            json={"url": "not-a-url"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

    def test_enqueues_classify_url_task(self, recap_client, test_user, recap_app, mocker):
        """Valid request enqueues the recap.tasks.classify_url RQ task."""
        mock_job = mocker.MagicMock()
        mock_job.id = "test-job-enqueue"
        mock_enqueue = mocker.patch.object(recap_app.task_queue, "enqueue", return_value=mock_job)

        url = "https://example.com/enqueue-article"
        with recap_app.app_context():
            token = test_user.get_or_create_api_token()

        recap_client.post(
            "/api/v1/articles",
            json={"url": url},
            headers={"Authorization": f"Bearer {token}"},
        )

        mock_enqueue.assert_called_once()
        call_kwargs = mock_enqueue.call_args
        # First positional arg is the task name
        assert call_kwargs[0][0] == "recap.tasks.classify_url"
        # The job targets the new row by id, not just by URL
        assert call_kwargs[1]["kwargs"]["article_id"] is not None


@pytest.mark.integration
@pytest.mark.recap
class TestCreateArticleContentCapture:
    """Phase 1: page HTML from the extension, duplicate handling, and the X-Recap-Client header."""

    URL = "https://medium.com/blogflyer/some-post-3f1ab92cc301"

    def _token(self, recap_app, user):
        with recap_app.app_context():
            return user.get_or_create_api_token()

    def _html(self):
        from pathlib import Path

        return (Path(__file__).parents[2] / "fixtures" / "flask_tutorial_part1.html").read_text()

    def test_html_is_extracted_and_stored(self, recap_client, test_user, recap_app, mocker):
        mocker.patch.object(recap_app.task_queue, "enqueue")
        token = self._token(recap_app, test_user)
        response = recap_client.post(
            "/api/v1/articles",
            json={"url": self.URL, "html": self._html()},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        body = response.get_json()
        assert body["content_captured"] is True
        assert "content_text" not in body  # private — never echoed back
        with recap_app.app_context():
            article = db.session.get(Article, body["article_id"])
            assert article.content_source == "extension"
            assert "Flask" in article.content_text

    def test_saving_same_url_again_returns_exists_without_duplicate(self, recap_client, test_user, recap_app, mocker):
        mock_enqueue = mocker.patch.object(recap_app.task_queue, "enqueue")
        token = self._token(recap_app, test_user)
        headers = {"Authorization": f"Bearer {token}"}
        first = recap_client.post("/api/v1/articles", json={"url": self.URL}, headers=headers)
        # Same article with Medium tracking params added
        second = recap_client.post("/api/v1/articles", json={"url": self.URL + "?source=rss&gi=abc"}, headers=headers)

        assert first.status_code == 201
        assert second.status_code == 200
        assert second.get_json()["status"] == "exists"
        assert second.get_json()["article_id"] == first.get_json()["article_id"]
        assert mock_enqueue.call_count == 1  # nothing new → no second job
        with recap_app.app_context():
            count = db.session.scalar(sa.select(sa.func.count(Article.id)).where(Article.user_id == test_user.id))
            assert count == 1

    def test_existing_url_with_html_is_updated_and_reclassified(self, recap_client, test_user, recap_app, mocker):
        mock_enqueue = mocker.patch.object(recap_app.task_queue, "enqueue")
        token = self._token(recap_app, test_user)
        headers = {"Authorization": f"Bearer {token}"}
        first = recap_client.post("/api/v1/articles", json={"url": self.URL}, headers=headers)
        second = recap_client.post("/api/v1/articles", json={"url": self.URL, "html": self._html()}, headers=headers)

        assert second.status_code == 200
        assert second.get_json()["status"] == "updated"
        assert second.get_json()["content_captured"] is True
        assert mock_enqueue.call_count == 2
        assert mock_enqueue.call_args[1]["kwargs"]["article_id"] == first.get_json()["article_id"]
        with recap_app.app_context():
            article = db.session.get(Article, first.get_json()["article_id"])
            assert article.content_source == "extension"

    def test_html_without_article_text_falls_back_to_crawl(self, recap_client, test_user, recap_app, mocker):
        mocker.patch.object(recap_app.task_queue, "enqueue")
        token = self._token(recap_app, test_user)
        response = recap_client.post(
            "/api/v1/articles",
            json={"url": self.URL, "html": "<html><body></body></html>"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        assert response.get_json()["content_captured"] is False
        with recap_app.app_context():
            article = db.session.get(Article, response.get_json()["article_id"])
            assert article.content_text is None

    def test_body_over_5mb_is_rejected(self, recap_client, test_user, recap_app, mocker):
        mock_enqueue = mocker.patch.object(recap_app.task_queue, "enqueue")
        token = self._token(recap_app, test_user)
        response = recap_client.post(
            "/api/v1/articles",
            json={"url": self.URL, "html": "x" * (5 * 1024 * 1024 + 1)},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 413
        mock_enqueue.assert_not_called()

    def test_client_header_records_extension_last_seen(self, recap_client, test_user, recap_app, mocker):
        mocker.patch.object(recap_app.task_queue, "enqueue")
        token = self._token(recap_app, test_user)
        recap_client.post(
            "/api/v1/articles",
            json={"url": self.URL},
            headers={"Authorization": f"Bearer {token}", "X-Recap-Client": "chrome-extension/1.1.0"},
        )

        with recap_app.app_context():
            assert db.session.get(User, test_user.id).extension_last_seen is not None

    def test_no_client_header_leaves_extension_last_seen_empty(self, recap_client, test_user, recap_app, mocker):
        mocker.patch.object(recap_app.task_queue, "enqueue")
        token = self._token(recap_app, test_user)
        recap_client.post("/api/v1/articles", json={"url": self.URL}, headers={"Authorization": f"Bearer {token}"})

        with recap_app.app_context():
            assert db.session.get(User, test_user.id).extension_last_seen is None
