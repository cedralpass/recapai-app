"""Unit tests for recap/auth/email.py."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
@pytest.mark.recap
class TestSendPasswordResetEmail:
    """Tests for send_password_reset_email."""

    @patch('recap.auth.email.send_email')
    def test_send_password_reset_email_calls_send_email_with_expected_fields(
        self, mock_send_email, recap_app
    ):
        """Reset email is composed with expected subject/sender/recipient."""
        from recap.auth.email import send_password_reset_email
        from recap import Config

        user = MagicMock()
        user.email = 'user@example.com'
        user.get_reset_password_token.return_value = 'token-123'

        with recap_app.test_request_context():
            send_password_reset_email(user)

        kwargs = mock_send_email.call_args.kwargs
        assert mock_send_email.call_count == 1
        assert mock_send_email.call_args.args[0] == '[Recap AI] Reset Your Password'
        assert kwargs['sender'] == Config.MAIL_DEFUALT_FROM
        assert kwargs['recipients'] == ['user@example.com']
        assert 'reset your password' in kwargs['text_body'].lower()
        assert 'reset your password' in kwargs['html_body'].lower()

    @patch('recap.auth.email.render_template')
    @patch('recap.auth.email.send_email')
    def test_send_password_reset_email_uses_generated_token(
        self, mock_send_email, mock_render_template, recap_app
    ):
        """Token from user model is passed into both templates."""
        from recap.auth.email import send_password_reset_email

        user = MagicMock()
        user.email = 'user@example.com'
        user.get_reset_password_token.return_value = 'generated-token'

        mock_render_template.side_effect = ['text body', 'html body']

        with recap_app.app_context():
            send_password_reset_email(user)

        user.get_reset_password_token.assert_called_once()
        mock_render_template.assert_any_call(
            'email/reset_password.txt', user=user, token='generated-token'
        )
        mock_render_template.assert_any_call(
            'email/reset_password.html', user=user, token='generated-token'
        )
        assert mock_send_email.call_count == 1

