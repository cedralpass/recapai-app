"""Integration tests for the 'Summary not available' notice on URL-only (blocked/down) articles."""

from datetime import datetime, timezone

import pytest

from recap import db
from recap.models import Article

_NOW = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)
_MEDIUM_URL = "https://medium.com/blogflyer/12-claude-code-techniques-3f1ab92cc301"


def _make_article(recap_app, user_id, summary):
    with recap_app.app_context():
        article = Article(
            url_path=_MEDIUM_URL,
            title="12 Claude Code Techniques",
            summary=summary,
            author_name="Unknown",
            category="AI Tools",
            classified=_NOW,
            user_id=user_id,
        )
        db.session.add(article)
        db.session.commit()
        return article.id


@pytest.mark.integration
@pytest.mark.recap
class TestUrlOnlyNotice:
    def test_index_card_shows_blocked_notice_instead_of_summary(self, recap_app, authenticated_client, test_user):
        _make_article(recap_app, test_user.id, "[URL only – site blocked] A guess from the slug.")
        html = authenticated_client.get("/index").get_data(as_text=True)
        assert "Summary not available — Medium is blocking our crawler." in html
        assert "[URL only" not in html
        assert "A guess from the slug." not in html

    def test_index_card_shows_down_notice(self, recap_app, authenticated_client, test_user):
        _make_article(recap_app, test_user.id, "[URL only – site unreachable] A guess.")
        html = authenticated_client.get("/index").get_data(as_text=True)
        assert "Summary not available — Medium couldn't be reached." in html

    def test_index_card_legacy_placeholder_gets_notice(self, recap_app, authenticated_client, test_user):
        _make_article(recap_app, test_user.id, "Bot Blocked – Classifying by URL Only")
        html = authenticated_client.get("/index").get_data(as_text=True)
        assert "Summary not available — Medium is blocking our crawler." in html
        assert "Bot Blocked" not in html

    def test_detail_page_shows_notice_and_labeled_guess(self, recap_app, authenticated_client, test_user):
        article_id = _make_article(recap_app, test_user.id, "[URL only – site blocked] A guess from the slug.")
        html = authenticated_client.get(f"/{article_id}/show").get_data(as_text=True)
        assert "Summary not available — Medium is blocking our crawler." in html
        assert "Guess from the link:" in html
        assert "A guess from the slug." in html
        assert "[URL only" not in html

    def test_normal_article_has_no_notice(self, recap_app, authenticated_client, test_user):
        article_id = _make_article(recap_app, test_user.id, "A real summary of the article.")
        index_html = authenticated_client.get("/index").get_data(as_text=True)
        detail_html = authenticated_client.get(f"/{article_id}/show").get_data(as_text=True)
        for html in (index_html, detail_html):
            assert "Summary not available" not in html
            assert "A real summary of the article." in html
