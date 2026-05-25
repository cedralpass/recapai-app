import pytest

from recap import db
from recap.models import DigestRun


@pytest.mark.integration
@pytest.mark.recap
class TestDigestNavLink:
    def test_nav_link_present_when_authenticated(self, seeded_authenticated_client):
        response = seeded_authenticated_client.get("/")
        assert response.status_code == 200
        assert b'href="/digest"' in response.data

    def test_nav_link_absent_when_anonymous(self, recap_client):
        response = recap_client.get("/")
        assert response.status_code == 200
        assert b'href="/digest"' not in response.data

    def test_nav_link_href_correct(self, seeded_authenticated_client):
        response = seeded_authenticated_client.get("/")
        assert response.status_code == 200
        assert b'href="/digest"' in response.data


@pytest.mark.integration
@pytest.mark.recap
class TestDigestNavUnreadDot:
    def test_unread_dot_present_when_unread_digest(
        self, recap_app, seeded_user, completed_digest_run, unread_digest_client
    ):
        response = unread_digest_client.get("/")
        assert response.status_code == 200
        assert b"bg-amber-400" in response.data

    def test_unread_dot_absent_when_no_digest(self, seeded_authenticated_client):
        response = seeded_authenticated_client.get("/")
        assert response.status_code == 200
        assert b"bg-amber-400" not in response.data

    def test_unread_dot_absent_after_opening_digest(
        self, recap_app, seeded_user, completed_digest_run, unread_digest_client
    ):
        # Dot present before visiting /digest
        response = unread_digest_client.get("/")
        assert b"bg-amber-400" in response.data

        # Visit /digest — sets opened_at
        unread_digest_client.get("/digest")

        # Dot should now be gone
        response = unread_digest_client.get("/")
        assert b"bg-amber-400" not in response.data
