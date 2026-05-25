import pytest

from recap import db
from recap.models import DigestRun


@pytest.mark.integration
@pytest.mark.recap
class TestDigestSidebarFreshState:
    def test_fresh_card_shown_when_unread_digest(
        self, recap_app, seeded_user, completed_digest_run, unread_digest_client
    ):
        response = unread_digest_client.get("/")
        assert response.status_code == 200
        assert b"bg-slate-900" in response.data

    def test_fresh_card_shows_article_and_cluster_count(
        self, recap_app, seeded_user, completed_digest_run, unread_digest_client
    ):
        response = unread_digest_client.get("/")
        assert response.status_code == 200
        assert b"12 articles" in response.data
        assert b"3 topics" in response.data

    def test_fresh_card_has_read_digest_link(self, recap_app, seeded_user, completed_digest_run, unread_digest_client):
        response = unread_digest_client.get("/")
        assert response.status_code == 200
        assert b'href="/digest"' in response.data

    def test_mobile_fresh_card_shown_below_article_list(
        self, recap_app, seeded_user, completed_digest_run, unread_digest_client
    ):
        response = unread_digest_client.get("/")
        assert response.status_code == 200
        assert b'id="digest-card-mobile"' in response.data
        assert b"md:hidden" in response.data


@pytest.mark.integration
@pytest.mark.recap
class TestDigestSidebarEmptyState:
    def test_empty_card_shown_when_no_digest(self, seeded_authenticated_client):
        response = seeded_authenticated_client.get("/")
        assert response.status_code == 200
        assert b"border-dashed" in response.data

    def test_empty_card_shows_generate_button(self, seeded_authenticated_client):
        response = seeded_authenticated_client.get("/")
        assert response.status_code == 200
        assert b"Generate recap now" in response.data

    def test_mobile_empty_card_shown_below_article_list(self, seeded_authenticated_client):
        response = seeded_authenticated_client.get("/")
        assert response.status_code == 200
        assert b'id="digest-card-mobile"' in response.data
        assert b"md:hidden" in response.data


@pytest.mark.integration
@pytest.mark.recap
class TestDigestSidebarOpenedState:
    def test_empty_card_absent_when_digest_opened(self, recap_app, seeded_user, opened_digest_run):
        client = recap_app.test_client()
        client.post("/auth/login", data={"username": "seeduser", "password": "seedpass123"})
        response = client.get("/")
        assert response.status_code == 200
        # Neither fresh card nor generate button should appear
        assert b"Generate recap now" not in response.data
        assert b'id="digest-card"' not in response.data

    def test_mobile_card_absent_when_digest_opened(self, recap_app, seeded_user, opened_digest_run):
        client = recap_app.test_client()
        client.post("/auth/login", data={"username": "seeduser", "password": "seedpass123"})
        response = client.get("/")
        assert response.status_code == 200
        assert b'id="digest-card-mobile"' not in response.data


@pytest.mark.integration
@pytest.mark.recap
class TestDigestSidebarAnonymous:
    def test_fresh_card_absent_for_anonymous_user(self, recap_client):
        response = recap_client.get("/")
        assert response.status_code == 200
        assert b'id="digest-card"' not in response.data
        assert b"Generate recap now" not in response.data
