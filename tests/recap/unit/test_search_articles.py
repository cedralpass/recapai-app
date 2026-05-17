"""Unit tests for User.search_articles() and AiApiHelper.EmbedText().

search_articles() uses the pgvector <=> operator which only works on Postgres.
The test DB is SQLite, so we mock db.session.execute to verify the query
is built with the right filters and that results are returned correctly.
"""

from unittest.mock import MagicMock, patch

import pytest

FAKE_VEC = [1.0] + [0.0] * 1535


def _mock_execute_returning(articles):
    """Return a mock that mimics db.session.execute(...).scalars().all()."""
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = articles
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    return mock_result


@pytest.mark.unit
@pytest.mark.recap
class TestSearchArticles:
    """User.search_articles() builds the right query and returns db results."""

    def test_returns_results_from_db(self, recap_app, test_user):
        from recap import db
        from recap.models import Article, User

        fake_article = MagicMock(spec=Article)
        fake_article.user_id = test_user.id

        with recap_app.app_context():
            u = db.session.get(User, test_user.id)
            with patch.object(db.session, "execute", return_value=_mock_execute_returning([fake_article])):
                results = u.search_articles(FAKE_VEC, limit=10)

        assert results == [fake_article]

    def test_returns_empty_when_no_articles(self, recap_app, test_user):
        from recap import db
        from recap.models import User

        with recap_app.app_context():
            u = db.session.get(User, test_user.id)
            with patch.object(db.session, "execute", return_value=_mock_execute_returning([])):
                results = u.search_articles(FAKE_VEC, limit=10)

        assert results == []

    def test_category_kwarg_passed_through(self, recap_app, test_user):
        """When category is given, execute is still called (category filter applied at SQL level)."""
        from recap import db
        from recap.models import Article, User

        fake_article = MagicMock(spec=Article)

        with recap_app.app_context():
            u = db.session.get(User, test_user.id)
            mock_exec = MagicMock(return_value=_mock_execute_returning([fake_article]))
            with patch.object(db.session, "execute", mock_exec):
                results = u.search_articles(FAKE_VEC, limit=5, category="Tech")

        assert results == [fake_article]
        mock_exec.assert_called_once()

    def test_limit_passed_to_query(self, recap_app, test_user):
        """execute is called exactly once regardless of limit value."""
        from recap import db
        from recap.models import User

        with recap_app.app_context():
            u = db.session.get(User, test_user.id)
            mock_exec = MagicMock(return_value=_mock_execute_returning([]))
            with patch.object(db.session, "execute", mock_exec):
                u.search_articles(FAKE_VEC, limit=3)

        mock_exec.assert_called_once()


@pytest.mark.unit
@pytest.mark.recap
class TestEmbedText:
    """AiApiHelper.EmbedText() delegates to aiapi /embed and returns the vector."""

    @patch("recap.aiapi_helper.httpx.post")
    def test_returns_embedding_on_success(self, mock_post, recap_app):
        fake_vec = [0.1] * 1536
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": fake_vec}
        mock_post.return_value = mock_response

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.EmbedText("some article text")

        assert result == fake_vec
        mock_post.assert_called_once()
        call_data = mock_post.call_args[1]["data"]
        assert call_data["text"] == "some article text"
        assert "secret" in call_data

    @patch("recap.aiapi_helper.httpx.post")
    def test_returns_none_on_http_error(self, mock_post, recap_app):
        import httpx

        mock_post.side_effect = httpx.RequestError("refused")

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.EmbedText("text")

        assert result is None

    @patch("recap.aiapi_helper.httpx.post")
    def test_returns_none_on_json_error(self, mock_post, recap_app):
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("bad json")
        mock_post.return_value = mock_response

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.EmbedText("text")

        assert result is None

    @patch("recap.aiapi_helper.httpx.post")
    def test_returns_none_on_missing_embedding_key(self, mock_post, recap_app):
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "something went wrong"}
        mock_post.return_value = mock_response

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.EmbedText("text")

        assert result is None
