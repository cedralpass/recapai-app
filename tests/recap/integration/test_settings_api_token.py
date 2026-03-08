import pytest
from recap.models import User
from recap import db


@pytest.mark.integration
@pytest.mark.recap
class TestApiTokenSettingsPage:
    def test_get_requires_login(self, recap_client):
        """Unauthenticated GET is redirected to login."""
        response = recap_client.get('/settings/api-token')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']

    def test_get_returns_200_for_authenticated_user(self, authenticated_client):
        """Authenticated GET returns 200."""
        response = authenticated_client.get('/settings/api-token')
        assert response.status_code == 200

    def test_get_shows_token_on_page(self, authenticated_client, test_user, recap_app):
        """Page renders the user's API token."""
        with recap_app.app_context():
            token = test_user.get_or_create_api_token()

        response = authenticated_client.get('/settings/api-token')
        assert token.encode() in response.data

    def test_get_creates_token_if_none_exists(self, authenticated_client, test_user, recap_app):
        """GET generates a token for a user that has none yet."""
        with recap_app.app_context():
            assert test_user.api_token is None

        response = authenticated_client.get('/settings/api-token')
        assert response.status_code == 200

        with recap_app.app_context():
            # Re-fetch from DB to see committed value
            user = db.session.get(User, test_user.id)
            assert user.api_token is not None

    def test_post_regenerates_token(self, authenticated_client, test_user, recap_app):
        """POST to the page replaces the existing token with a new one."""
        with recap_app.app_context():
            old_token = test_user.get_or_create_api_token()

        response = authenticated_client.post(
            '/settings/api-token',
            data={'action': 'regenerate'},
            follow_redirects=True,
        )
        assert response.status_code == 200

        with recap_app.app_context():
            user = db.session.get(User, test_user.id)
            assert user.api_token != old_token
            assert user.api_token is not None

    def test_post_shows_new_token_on_page(self, authenticated_client, test_user, recap_app):
        """After POST the response page displays the newly generated token."""
        with recap_app.app_context():
            test_user.get_or_create_api_token()

        response = authenticated_client.post(
            '/settings/api-token',
            data={'action': 'regenerate'},
            follow_redirects=True,
        )

        with recap_app.app_context():
            user = db.session.get(User, test_user.id)
            new_token = user.api_token

        assert new_token.encode() in response.data
