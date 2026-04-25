"""Unit tests for recap/email.py."""
import pytest
from unittest.mock import patch


@pytest.mark.unit
@pytest.mark.recap
class TestSendEmail:
    """Tests for send_email helper."""

    @patch('recap.email.mail.send')
    def test_send_email_builds_message_with_expected_fields(self, mock_mail_send, recap_app):
        """Message is built with subject/sender/recipients and body/html."""
        from recap.email import send_email

        with recap_app.app_context():
            send_email(
                subject='Subject line',
                sender='noreply@example.com',
                recipients=['to@example.com'],
                text_body='plain text body',
                html_body='<p>html body</p>',
            )

        msg = mock_mail_send.call_args.args[0]
        assert mock_mail_send.call_count == 1
        assert msg.subject == 'Subject line'
        assert msg.sender == 'noreply@example.com'
        assert msg.recipients == ['to@example.com']
        assert msg.body == 'plain text body'
        assert msg.html == '<p>html body</p>'

    @patch('recap.email.mail.send')
    def test_send_email_returns_mail_send_result(self, mock_mail_send, recap_app):
        """Return value from mail.send is passed through by helper."""
        from recap.email import send_email

        mock_mail_send.return_value = 'sent-ok'

        with recap_app.app_context():
            result = send_email(
                subject='Subject line',
                sender='noreply@example.com',
                recipients=['to@example.com'],
                text_body='plain text body',
                html_body='<p>html body</p>',
            )

        assert result == 'sent-ok'

