"""Unit tests for recap.article_text.build_article_text."""

import json
from unittest.mock import MagicMock

import pytest


def _make_article(title=None, summary=None, category=None, key_topics=None, sub_categories=None):
    article = MagicMock()
    article.title = title
    article.summary = summary
    article.category = category
    article.get_key_topics_json.return_value = key_topics
    article.get_sub_categories_json.return_value = sub_categories
    return article


@pytest.mark.unit
@pytest.mark.recap
class TestBuildArticleText:
    def test_full_article_includes_all_fields(self):
        from recap.article_text import build_article_text

        article = _make_article(
            title="My Title",
            summary="A short summary.",
            category="Technology",
            key_topics=["Python", "Flask"],
            sub_categories=["Web Dev", "APIs"],
        )
        text = build_article_text(article)
        assert "My Title" in text
        assert "A short summary" in text
        assert "Technology" in text
        assert "Python" in text
        assert "Flask" in text
        assert "Web Dev" in text
        assert "APIs" in text

    def test_missing_summary_excluded(self):
        from recap.article_text import build_article_text

        article = _make_article(title="Title Only", summary=None, category="AI")
        text = build_article_text(article)
        assert "Title Only" in text
        assert "AI" in text

    def test_missing_title_excluded(self):
        from recap.article_text import build_article_text

        article = _make_article(title=None, summary="Just a summary.", category="Science")
        text = build_article_text(article)
        assert "Just a summary" in text
        assert text  # not empty

    def test_all_none_returns_empty(self):
        from recap.article_text import build_article_text

        article = _make_article()
        text = build_article_text(article)
        assert text == ""

    def test_empty_topics_and_subs_excluded(self):
        from recap.article_text import build_article_text

        article = _make_article(title="T", summary="S", category="C", key_topics=[], sub_categories=[])
        text = build_article_text(article)
        assert "Topics" not in text
        assert "Sub-categories" not in text

    def test_none_topics_handled(self):
        from recap.article_text import build_article_text

        article = _make_article(title="T", summary="S", key_topics=None, sub_categories=None)
        text = build_article_text(article)
        assert "Topics" not in text
        assert text  # still produces output from title/summary
