"""Unit tests for Flask context processors defined in recap/__init__.py."""

import pytest


@pytest.mark.unit
@pytest.mark.recap
class TestInjectDigestState:
    """Tests for inject_digest_state context processor.

    The critical regression scenario: an RQ worker calls render_template to
    build the digest email.  There is an active app context but NO request
    context, so Flask-Login's current_user (a Werkzeug LocalProxy) cannot
    resolve to a real user object.  Accessing .is_authenticated on an
    unresolvable proxy raises AttributeError.

    The broken guard `current_user is None` always returned False because the
    proxy object itself is never None — only what it proxies can be absent.
    The fix uses try/except AttributeError.
    """

    def test_no_request_context_returns_safe_defaults(self, recap_app):
        """Context processor must not raise when called without a request context.

        This is the exact scenario that crashed the compose node: render_template
        triggered inject_digest_state inside the RQ worker (app context only,
        no request context, no current_user resolution).
        """
        from flask import render_template_string

        with recap_app.app_context():
            # No request context pushed — simulates the RQ worker environment.
            # render_template_string triggers all context processors; this must
            # complete without AttributeError.
            html = render_template_string("{{ has_unread_digest }}|{{ latest_digest }}")

        assert html == "False|None"

    def test_no_request_context_has_unread_digest_is_false(self, recap_app):
        """has_unread_digest must be False (not missing) outside a request context."""
        from flask import render_template_string

        with recap_app.app_context():
            html = render_template_string("{{ has_unread_digest }}")

        assert html == "False"

    def test_no_request_context_latest_digest_is_none(self, recap_app):
        """latest_digest must be None (not missing) outside a request context."""
        from flask import render_template_string

        with recap_app.app_context():
            html = render_template_string("{{ latest_digest }}")

        assert html == "None"
