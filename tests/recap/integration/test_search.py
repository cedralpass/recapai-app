"""Integration tests for GET /search.

search_articles() uses pgvector SQL which only runs on Postgres.
We mock it at the User model level so the route logic and template
rendering are tested end-to-end without requiring a real vector DB.
"""

from unittest.mock import MagicMock, patch

import pytest

FAKE_VEC = [1.0] + [0.0] * 1535


def _login(client, username="seeduser", password="seedpass123"):
    client.post("/auth/login", data={"username": username, "password": password})


def _fake_article(title="Test Article", category="Tech", is_read=False):
    from datetime import datetime

    a = MagicMock()
    a.id = 1
    a.title = title
    a.summary = "A test summary."
    a.author_name = "Author"
    a.category = category
    a.url_path = "https://example.com/article"
    a.is_read = is_read
    a.is_viewed = False
    a.created = datetime(2025, 1, 1)
    return a


@pytest.mark.integration
@pytest.mark.recap
class TestSearchRoute:
    def test_requires_login(self, recap_client):
        response = recap_client.get("/search?q=python")
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_empty_query_shows_prompt(self, recap_app, seeded_user):
        client = recap_app.test_client()
        _login(client)
        response = client.get("/search")
        assert response.status_code == 200
        assert b"Type something above" in response.data

    def test_query_with_no_results_shows_empty_state(self, recap_app, seeded_user):
        client = recap_app.test_client()
        _login(client)

        with (
            patch("recap.routes.AiApiHelper.EmbedText", return_value=FAKE_VEC),
            patch("recap.models.User.search_articles", return_value=[]),
        ):
            response = client.get("/search?q=serverless+functions")

        assert response.status_code == 200
        assert b"No articles found" in response.data

    def test_returns_matching_article(self, recap_app, seeded_user):
        client = recap_app.test_client()
        _login(client)

        article = _fake_article(title="Flask Web Development", category="Software Architecture")

        with (
            patch("recap.routes.AiApiHelper.EmbedText", return_value=FAKE_VEC),
            patch("recap.models.User.search_articles", return_value=[article]),
        ):
            response = client.get("/search?q=flask+web+development")

        assert response.status_code == 200
        assert b"Flask Web Development" in response.data

    def test_result_count_shown(self, recap_app, seeded_user):
        client = recap_app.test_client()
        _login(client)

        articles = [_fake_article(title=f"Article {i}") for i in range(3)]

        with (
            patch("recap.routes.AiApiHelper.EmbedText", return_value=FAKE_VEC),
            patch("recap.models.User.search_articles", return_value=articles),
        ):
            response = client.get("/search?q=something")

        assert response.status_code == 200
        assert b"3 results" in response.data

    def test_aiapi_failure_shows_no_results(self, recap_app, seeded_user):
        client = recap_app.test_client()
        _login(client)

        with patch("recap.routes.AiApiHelper.EmbedText", return_value=None):
            response = client.get("/search?q=something")

        assert response.status_code == 200
        assert b"No articles found" in response.data

    def test_category_filter_passed_to_search(self, recap_app, seeded_user):
        """Route passes category arg to search_articles."""
        client = recap_app.test_client()
        _login(client)

        article = _fake_article(title="AI Article", category="AI")

        with (
            patch("recap.routes.AiApiHelper.EmbedText", return_value=FAKE_VEC),
            patch("recap.models.User.search_articles", return_value=[article]) as mock_search,
        ):
            response = client.get("/search?q=article&category=AI")

        assert response.status_code == 200
        assert b"AI Article" in response.data
        mock_search.assert_called_once()
        _, kwargs = mock_search.call_args
        assert kwargs.get("category") == "AI"

    def test_search_bar_present_in_nav_when_authenticated(self, recap_app, seeded_user):
        client = recap_app.test_client()
        _login(client)
        response = client.get("/")
        assert response.status_code == 200
        assert b'placeholder="Search articles..."' in response.data

    def test_search_bar_absent_when_anonymous(self, recap_client):
        response = recap_client.get("/")
        assert response.status_code == 200
        assert b'placeholder="Search articles..."' not in response.data

    def test_query_prefilled_when_arriving_from_article_link(self, recap_app, seeded_user):
        """Arriving via a sub-category/key-topic link pre-fills the search input."""
        client = recap_app.test_client()
        _login(client)

        with (
            patch("recap.routes.AiApiHelper.EmbedText", return_value=FAKE_VEC),
            patch("recap.models.User.search_articles", return_value=[]),
        ):
            response = client.get("/search?q=Conflict+resolution")

        assert response.status_code == 200
        assert b"Conflict resolution" in response.data
