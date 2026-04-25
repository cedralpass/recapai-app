"""Integration tests for recap/auth — logout, password reset flows, redirect guards."""
import pytest
from unittest.mock import patch
from recap.models import User
from recap import db


@pytest.mark.integration
@pytest.mark.recap
class TestLogout:
    def test_logout_redirects_to_index(self, authenticated_client):
        """GET /auth/logout redirects to the index page."""
        response = authenticated_client.get('/auth/logout', follow_redirects=False)
        assert response.status_code == 302
        assert '/' in response.headers['Location']

    def test_logout_clears_session(self, authenticated_client):
        """After logout, accessing a protected page redirects to login."""
        authenticated_client.get('/auth/logout')
        response = authenticated_client.get('/add_article')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.integration
@pytest.mark.recap
class TestAuthRedirectGuards:
    """Authenticated users should be redirected away from auth pages."""

    def test_authenticated_user_redirected_from_login(self, authenticated_client):
        """Logged-in user hitting /auth/login is redirected to index."""
        response = authenticated_client.get('/auth/login', follow_redirects=False)
        assert response.status_code == 302

    def test_authenticated_user_redirected_from_register(self, authenticated_client):
        """Logged-in user hitting /auth/register is redirected to index."""
        response = authenticated_client.get('/auth/register', follow_redirects=False)
        assert response.status_code == 302

    def test_authenticated_user_redirected_from_reset_request(self, authenticated_client):
        """Logged-in user hitting /auth/reset_password_request is redirected."""
        response = authenticated_client.get(
            '/auth/reset_password_request', follow_redirects=False
        )
        assert response.status_code == 302


@pytest.mark.integration
@pytest.mark.recap
class TestPasswordResetRequest:
    def test_reset_request_page_loads(self, recap_client):
        """GET /auth/reset_password_request returns 200."""
        response = recap_client.get('/auth/reset_password_request')
        assert response.status_code == 200

    @patch('recap.auth.send_password_reset_email')
    def test_reset_request_with_known_email_sends_email(
        self, mock_send_email, recap_client, recap_app, test_user
    ):
        """POST with a registered email calls send_password_reset_email."""
        with recap_app.app_context():
            email = test_user.email

        response = recap_client.post(
            '/auth/reset_password_request',
            data={'email': email},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'Check your email' in response.data
        mock_send_email.assert_called_once()

    @patch('recap.auth.send_password_reset_email')
    def test_reset_request_with_unknown_email_does_not_send_email(
        self, mock_send_email, recap_client
    ):
        """POST with an unknown email still shows the confirmation message but sends nothing.

        This prevents user enumeration via the reset page.
        """
        response = recap_client.post(
            '/auth/reset_password_request',
            data={'email': 'nobody@example.com'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'Check your email' in response.data
        mock_send_email.assert_not_called()

    @patch('recap.auth.send_password_reset_email')
    def test_reset_request_redirects_to_login(
        self, mock_send_email, recap_client, recap_app, test_user
    ):
        """After a reset request, the user ends up on the login page."""
        with recap_app.app_context():
            email = test_user.email

        response = recap_client.post(
            '/auth/reset_password_request',
            data={'email': email},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.integration
@pytest.mark.recap
class TestPasswordReset:
    def test_reset_with_invalid_token_redirects_to_index(self, recap_client):
        """GET /auth/reset_password/<bad-token> redirects to index."""
        response = recap_client.get(
            '/auth/reset_password/notavalidtoken', follow_redirects=False
        )
        assert response.status_code == 302

    def test_reset_with_valid_token_shows_form(self, recap_client, recap_app, test_user):
        """GET /auth/reset_password/<valid-token> returns 200 with the reset form."""
        with recap_app.app_context():
            token = test_user.get_reset_password_token()

        response = recap_client.get(f'/auth/reset_password/{token}')
        assert response.status_code == 200

    def test_reset_changes_password(self, recap_client, recap_app, test_user):
        """POST /auth/reset_password/<token> updates the user's password."""
        with recap_app.app_context():
            token = test_user.get_reset_password_token()
            user_id = test_user.id

        recap_client.post(
            f'/auth/reset_password/{token}',
            data={'password': 'newpass456', 'password2': 'newpass456'},
            follow_redirects=True,
        )

        with recap_app.app_context():
            user = db.session.get(User, user_id)
            assert user.check_password('newpass456')
            assert not user.check_password('testpass123')

    def test_reset_redirects_to_login_on_success(self, recap_client, recap_app, test_user):
        """Successful password reset redirects to the login page."""
        with recap_app.app_context():
            token = test_user.get_reset_password_token()

        response = recap_client.post(
            f'/auth/reset_password/{token}',
            data={'password': 'newpass456', 'password2': 'newpass456'},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']

    def test_authenticated_user_redirected_from_reset_password_token_page(
        self, authenticated_client, recap_app, test_user
    ):
        """Logged-in user hitting /auth/reset_password/<token> is redirected."""
        with recap_app.app_context():
            token = test_user.get_reset_password_token()

        response = authenticated_client.get(
            f'/auth/reset_password/{token}', follow_redirects=False
        )
        assert response.status_code == 302


@pytest.mark.integration
@pytest.mark.recap
class TestInvalidLogin:
    def test_wrong_password_flashes_error(self, recap_client, recap_app, test_user):
        """POST /auth/login with wrong password flashes the invalid-credentials message."""
        response = recap_client.post(
            '/auth/login',
            data={'username': test_user.username, 'password': 'wrongpassword'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'Invalid username or password' in response.data

    def test_unknown_username_flashes_error(self, recap_client):
        """POST /auth/login with a username that does not exist shows an error."""
        response = recap_client.post(
            '/auth/login',
            data={'username': 'doesnotexist', 'password': 'anypassword'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'Invalid username or password' in response.data

    def test_invalid_login_stays_on_login_page(self, recap_client, recap_app, test_user):
        """After invalid credentials the user ends up back on the login page."""
        response = recap_client.post(
            '/auth/login',
            data={'username': test_user.username, 'password': 'bad'},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']
