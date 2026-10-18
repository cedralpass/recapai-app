"""Unit tests for recap/tasks.py background jobs."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@pytest.mark.recap
class TestSaveClassificationResult:
    """Tests for save_classification_result — pure attribute-mapping logic."""

    def test_sets_all_fields(self, recap_app):
        """All classification fields are written to the article."""
        from recap.models import Article
        from recap.tasks import save_classification_result

        with recap_app.app_context():
            article = Article(url_path="https://example.com/article", user_id=1)
            classify_result = {
                "summary": "A summary.",
                "blog_title": "Blog Title",
                "author": "Jane Doe",
                "category": "Technology",
                "key_topics": ["AI", "ML"],
                "sub_categories": ["Deep Learning"],
            }
            save_classification_result(classify_result, article)

        assert article.summary == "A summary."
        assert article.title == "Blog Title"
        assert article.author_name == "Jane Doe"
        assert article.category == "Technology"
        assert json.loads(article.key_topics) == ["AI", "ML"]
        assert json.loads(article.sub_categories) == ["Deep Learning"]
        assert article.classified is not None

    def test_classified_timestamp_is_recent_utc(self, recap_app):
        """classified is set to approximately now in UTC."""
        from recap.models import Article
        from recap.tasks import save_classification_result

        before = datetime.now(timezone.utc)
        with recap_app.app_context():
            article = Article(url_path="https://example.com/ts", user_id=1)
            save_classification_result(
                {
                    "summary": "S",
                    "blog_title": "T",
                    "author": "A",
                    "category": "C",
                    "key_topics": [],
                    "sub_categories": [],
                },
                article,
            )
        after = datetime.now(timezone.utc)

        classified = article.classified
        if classified.tzinfo is None:
            classified = classified.replace(tzinfo=timezone.utc)
        assert before <= classified <= after

    def test_missing_key_topics_defaults_to_empty_list(self, recap_app):
        """When key_topics is absent, article.key_topics is serialised as []."""
        from recap.models import Article
        from recap.tasks import save_classification_result

        with recap_app.app_context():
            article = Article(url_path="https://example.com/notopics", user_id=1)
            save_classification_result(
                {"summary": "S", "blog_title": "T", "author": "A", "category": "C"},
                article,
            )

        assert json.loads(article.key_topics) == []

    def test_missing_sub_categories_defaults_to_empty_list(self, recap_app):
        """When sub_categories is absent, article.sub_categories is serialised as []."""
        from recap.models import Article
        from recap.tasks import save_classification_result

        with recap_app.app_context():
            article = Article(url_path="https://example.com/nosub", user_id=1)
            save_classification_result(
                {"summary": "S", "blog_title": "T", "author": "A", "category": "C", "key_topics": ["X"]},
                article,
            )

        assert json.loads(article.sub_categories) == []


@pytest.mark.unit
@pytest.mark.recap
class TestClassifyUrl:
    """Tests for classify_url — orchestration of article lookup, AI call, and save."""

    @patch("recap.tasks._build_category_list", return_value=["Technology", "AI"])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_happy_path_returns_classify_result(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        """classify_url finds article, calls ClassifyUrl, saves result, and returns it."""
        from recap.tasks import classify_url

        mock_article = MagicMock()
        mock_Article.get_article_by_url_path.return_value = mock_article

        classify_result = {
            "summary": "Test summary",
            "blog_title": "Test Title",
            "author": "Author",
            "category": "Technology",
            "key_topics": ["AI"],
            "sub_categories": ["ML"],
        }
        mock_AiApiHelper.ClassifyUrl.return_value = classify_result

        with recap_app.app_context():
            result = classify_url("https://example.com/article", 1)

        assert result == classify_result
        mock_Article.get_article_by_url_path.assert_called_once_with("https://example.com/article", 1)
        mock_AiApiHelper.ClassifyUrl.assert_called_once_with(
            "https://example.com/article", 1, categories=["Technology", "AI"], content=None
        )

    @patch("recap.tasks._build_category_list", return_value=["Technology"])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_happy_path_commits_article_to_db(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        """After classification, article is added and committed to the DB session."""
        from recap.tasks import classify_url

        mock_article = MagicMock()
        mock_Article.get_article_by_url_path.return_value = mock_article
        mock_AiApiHelper.ClassifyUrl.return_value = {
            "summary": "S",
            "blog_title": "T",
            "author": "A",
            "category": "C",
            "key_topics": [],
            "sub_categories": [],
        }

        with recap_app.app_context():
            classify_url("https://example.com/article", 1)

        mock_db.session.add.assert_called_once_with(mock_article)
        mock_db.session.commit.assert_called_once()

    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_exception_is_caught_and_returns_none(self, mock_db, mock_Article, mock_AiApiHelper, recap_app):
        """When AiApiHelper raises, classify_url swallows the error and returns None."""
        from recap.tasks import classify_url

        mock_Article.get_article_by_url_path.return_value = MagicMock()
        mock_AiApiHelper.ClassifyUrl.side_effect = Exception("API failure")

        with recap_app.app_context():
            result = classify_url("https://example.com/article", 1)

        assert result is None
        mock_db.session.commit.assert_not_called()

    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_article_not_found_exception_caught(self, mock_db, mock_Article, mock_AiApiHelper, recap_app):
        """When get_article_by_url_path raises, exception is caught gracefully."""
        from recap.tasks import classify_url

        mock_Article.get_article_by_url_path.side_effect = Exception("DB error")

        with recap_app.app_context():
            result = classify_url("https://example.com/article", 1)

        assert result is None
        mock_AiApiHelper.ClassifyUrl.assert_not_called()

    @patch("recap.tasks._build_category_list", return_value=["Technology"])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_site_down_preserves_existing_classification(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        """When site is down and article is already classified, save is skipped.

        This models the real cq2.co case: the site returns a DNS ConnectError, so
        fetch_article_content returns False, ClassifyUrl adds site_down=True, and
        the task must not overwrite the good existing classification with a URL-only guess.
        """
        from datetime import datetime, timezone

        from recap import tasks
        from recap.tasks import classify_url

        mock_article = MagicMock()
        mock_article.classified = datetime(2025, 1, 1, tzinfo=timezone.utc)  # already classified
        mock_Article.get_article_by_url_path.return_value = mock_article

        mock_AiApiHelper.ClassifyUrl.return_value = {
            "site_down": True,
            "summary": "Site Down – Classifying by URL Only",
            "blog_title": "Unknown",
            "author": "Unknown",
            "category": "Technology",
            "key_topics": [],
            "sub_categories": [],
        }

        mock_redis = MagicMock()
        with patch.object(tasks.app, "redis", mock_redis):
            with recap_app.app_context():
                result = classify_url("https://cq2.co/blog/the-best-way-to-have-complex-discussions", 42)

        assert result is None
        mock_db.session.commit.assert_not_called()
        # Article fields must NOT be overwritten
        assert mock_article.summary != "Site Down – Classifying by URL Only"
        assert mock_article.classified == datetime(2025, 1, 1, tzinfo=timezone.utc)

    @patch("recap.tasks._build_category_list", return_value=["Technology"])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_site_down_stores_redis_flash_for_user(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        """When site is down and article is classified, a flash message is stored in Redis."""
        from datetime import datetime, timezone

        from recap import tasks
        from recap.tasks import classify_url

        mock_article = MagicMock()
        mock_article.classified = datetime(2025, 1, 1, tzinfo=timezone.utc)
        mock_Article.get_article_by_url_path.return_value = mock_article

        mock_AiApiHelper.ClassifyUrl.return_value = {
            "site_down": True,
            "summary": "Site Down – Classifying by URL Only",
            "blog_title": "Unknown",
            "author": "Unknown",
            "category": "Technology",
            "key_topics": [],
            "sub_categories": [],
        }

        mock_redis = MagicMock()
        with patch.object(tasks.app, "redis", mock_redis):
            with recap_app.app_context():
                classify_url("https://cq2.co/blog/the-best-way-to-have-complex-discussions", 42)

        mock_redis.setex.assert_called_once()
        key, ttl, message = mock_redis.setex.call_args[0]
        assert key == "user_flash:42"
        assert ttl == 300
        assert "cq2.co" in message
        assert "down" in message.lower()

    @patch("recap.tasks._build_category_list", return_value=["Technology"])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_site_down_proceeds_for_unclassified_article(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        """When site is down but article has never been classified, classification still runs.

        A brand-new article with no prior data is better off with a URL-only classification
        than no classification at all.
        """
        from recap import tasks
        from recap.tasks import URL_ONLY_DOWN_PREFIX, classify_url

        mock_article = MagicMock()
        mock_article.classified = None  # not yet classified
        mock_Article.get_article_by_url_path.return_value = mock_article

        classify_result = {
            "site_down": True,
            "summary": "How to structure complex discussions.",
            "blog_title": "Complex Discussions",
            "author": "Unknown",
            "category": "Technology",
            "key_topics": [],
            "sub_categories": [],
        }
        mock_AiApiHelper.ClassifyUrl.return_value = classify_result

        mock_redis = MagicMock()
        with patch.object(tasks.app, "redis", mock_redis):
            with recap_app.app_context():
                classify_url("https://cq2.co/blog/the-best-way-to-have-complex-discussions", 7)

        # Classification should proceed (save + commit called)
        mock_db.session.commit.assert_called_once()
        mock_redis.setex.assert_not_called()  # no flash for a new article
        assert mock_article.summary == URL_ONLY_DOWN_PREFIX + "How to structure complex discussions."

    @patch("recap.tasks._build_category_list", return_value=["Technology"])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_bot_blocked_preserves_existing_classification(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        """When site returns 403 and article is already classified, existing data is kept.

        Models the Medium bot-blocking case: site_blocked=True on reclassify of an
        article that already has good data — we preserve it and flash the user.
        """
        from datetime import datetime, timezone

        from recap import tasks
        from recap.tasks import classify_url

        mock_article = MagicMock()
        mock_article.classified = datetime(2025, 3, 1, tzinfo=timezone.utc)
        mock_article.title = "Improve Retrieval Using MMR"
        mock_Article.get_article_by_url_path.return_value = mock_article

        mock_AiApiHelper.ClassifyUrl.return_value = {
            "site_blocked": True,
            "summary": "Bot Blocked – Classifying by URL Only",
            "blog_title": "Unknown",
            "author": "Unknown",
            "category": "Technology",
            "key_topics": [],
            "sub_categories": [],
        }

        mock_redis = MagicMock()
        with patch.object(tasks.app, "redis", mock_redis):
            with recap_app.app_context():
                result = classify_url(
                    "https://kaustavmukherjee-66179.medium.com/improve-retrieval-of-documents-from-vectordb-using-maximum-marginal-relevance-mmr-for-balancing-f6ae56fb9512",
                    99,
                )

        assert result is None
        mock_db.session.commit.assert_not_called()
        assert mock_article.title == "Improve Retrieval Using MMR"  # unchanged

    @patch("recap.tasks._build_category_list", return_value=["Technology"])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_bot_blocked_stores_redis_flash_distinct_from_site_down(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        """Bot-blocked flash message mentions 'blocking' (different wording from site-down)."""
        from datetime import datetime, timezone

        from recap import tasks
        from recap.tasks import classify_url

        mock_article = MagicMock()
        mock_article.classified = datetime(2025, 3, 1, tzinfo=timezone.utc)
        mock_Article.get_article_by_url_path.return_value = mock_article

        mock_AiApiHelper.ClassifyUrl.return_value = {
            "site_blocked": True,
            "summary": "S",
            "blog_title": "T",
            "author": "A",
            "category": "C",
            "key_topics": [],
            "sub_categories": [],
        }

        mock_redis = MagicMock()
        with patch.object(tasks.app, "redis", mock_redis):
            with recap_app.app_context():
                classify_url("https://medium.com/some-article", 5)

        mock_redis.setex.assert_called_once()
        _key, _ttl, message = mock_redis.setex.call_args[0]
        assert "blocking" in message.lower() or "blocked" in message.lower()
        assert "down" not in message.lower()  # distinct from site-down wording

    @patch("recap.tasks._build_category_list", return_value=["Technology"])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_bot_blocked_keeps_model_title_for_new_article(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        """For a brand-new article blocked by Medium, the model's URL-based title is kept
        and the summary is marked as URL-only (no more 'Medium Blocked – <url>' titles)."""
        from recap import tasks
        from recap.tasks import URL_ONLY_BLOCKED_PREFIX, classify_url

        url = "https://medium.com/blogflyer/12-claude-code-techniques-that-make-ai-coding-feel-more-like-engineering-3f1ab92cc301"

        mock_article = MagicMock()
        mock_article.classified = None  # never classified
        mock_Article.get_article_by_url_path.return_value = mock_article

        mock_AiApiHelper.ClassifyUrl.return_value = {
            "site_blocked": True,
            "summary": "Practical Claude Code techniques for more disciplined AI-assisted coding.",
            "blog_title": "12 Claude Code Techniques That Make AI Coding Feel More Like Engineering",
            "author": "Unknown",
            "category": "AI Tools",
            "key_topics": [],
            "sub_categories": [],
        }

        mock_redis = MagicMock()
        with patch.object(tasks.app, "redis", mock_redis):
            with recap_app.app_context():
                classify_url(url, 3)

        mock_db.session.commit.assert_called_once()
        mock_redis.setex.assert_not_called()  # no flash for a new article
        assert mock_article.title == "12 Claude Code Techniques That Make AI Coding Feel More Like Engineering"
        assert mock_article.summary == (
            URL_ONLY_BLOCKED_PREFIX + "Practical Claude Code techniques for more disciplined AI-assisted coding."
        )

    @patch("recap.tasks._build_category_list", return_value=["Technology"])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_bot_blocked_falls_back_to_slug_title_when_model_unknown(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        """If the model returns 'Unknown' for the title, the URL slug becomes the title."""
        from recap import tasks
        from recap.tasks import URL_ONLY_BLOCKED_PREFIX, classify_url

        url = "https://medium.com/blogflyer/12-claude-code-techniques-that-make-ai-coding-feel-more-like-engineering-3f1ab92cc301"

        mock_article = MagicMock()
        mock_article.classified = None
        mock_Article.get_article_by_url_path.return_value = mock_article

        mock_AiApiHelper.ClassifyUrl.return_value = {
            "site_blocked": True,
            "summary": "Unknown",
            "blog_title": "Unknown",
            "author": "Unknown",
            "category": "AI Tools",
            "key_topics": [],
            "sub_categories": [],
        }

        with patch.object(tasks.app, "redis", MagicMock()):
            with recap_app.app_context():
                classify_url(url, 3)

        assert mock_article.title == "12 claude code techniques that make ai coding feel more like engineering"
        assert mock_article.summary.startswith(URL_ONLY_BLOCKED_PREFIX)
        assert "Unknown" not in mock_article.summary

    @patch("recap.tasks._build_category_list", return_value=["Technology"])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_bot_blocked_falls_back_to_site_blocked_title_for_opaque_slug(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        """No usable title from the model or the slug → '<Site> Blocked – <url>'."""
        from recap import tasks
        from recap.tasks import classify_url

        url = "https://medium.com/p/3f1ab92cc301"

        mock_article = MagicMock()
        mock_article.classified = None
        mock_Article.get_article_by_url_path.return_value = mock_article

        mock_AiApiHelper.ClassifyUrl.return_value = {
            "site_blocked": True,
            "summary": "Unknown",
            "blog_title": "Unknown",
            "author": "Unknown",
            "category": "Technology",
            "key_topics": [],
            "sub_categories": [],
        }

        with patch.object(tasks.app, "redis", MagicMock()):
            with recap_app.app_context():
                classify_url(url, 3)

        assert mock_article.title == f"Medium Blocked – {url}"

    @pytest.mark.parametrize(
        "old_summary",
        [
            "Bot Blocked – Classifying by URL Only",
            "Site Down – Classifying by URL Only",
            "[URL only – site blocked] An earlier guess.",
        ],
    )
    @patch("recap.tasks._build_category_list", return_value=["Technology"])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_bot_blocked_reclassify_replaces_url_only_placeholder(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, old_summary, recap_app
    ):
        """Reclassifying an article whose existing data is itself a URL-only placeholder
        overwrites it, so old 'Medium Blocked' entries can be repaired from Reclassify."""
        from datetime import datetime, timezone

        from recap import tasks
        from recap.tasks import classify_url

        mock_article = MagicMock()
        mock_article.classified = datetime(2026, 10, 10, tzinfo=timezone.utc)
        mock_article.summary = old_summary
        mock_article.title = "Medium Blocked – https://medium.com/blogflyer/some-post-3f1ab92cc301"
        mock_Article.get_article_by_url_path.return_value = mock_article

        mock_AiApiHelper.ClassifyUrl.return_value = {
            "site_blocked": True,
            "summary": "A post about something.",
            "blog_title": "Some Post",
            "author": "Unknown",
            "category": "Technology",
            "key_topics": [],
            "sub_categories": [],
        }

        mock_redis = MagicMock()
        with patch.object(tasks.app, "redis", mock_redis):
            with recap_app.app_context():
                classify_url("https://medium.com/blogflyer/some-post-3f1ab92cc301", 3)

        mock_db.session.commit.assert_called_once()
        mock_redis.setex.assert_not_called()
        assert mock_article.title == "Some Post"


@pytest.mark.unit
@pytest.mark.recap
class TestClassifyUrlByArticleId:
    """classify_url(article_id=...) targets the exact row, even when the URL was saved twice."""

    _RESULT = {
        "summary": "S",
        "blog_title": "T",
        "author": "A",
        "category": "C",
        "key_topics": [],
        "sub_categories": [],
    }

    @patch("recap.tasks._build_category_list", return_value=[])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_uses_article_id_instead_of_url_lookup(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        from recap.tasks import classify_url

        mock_article = MagicMock()
        mock_article.user_id = 7
        mock_db.session.get.return_value = mock_article
        mock_AiApiHelper.ClassifyUrl.return_value = dict(self._RESULT)

        with recap_app.app_context():
            classify_url("https://example.com/dup", 7, article_id=42)

        mock_db.session.get.assert_called_once_with(mock_Article, 42)
        mock_Article.get_article_by_url_path.assert_not_called()
        assert mock_article.title == "T"

    @patch("recap.tasks._build_category_list", return_value=[])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_other_users_article_is_ignored(self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app):
        from recap.tasks import classify_url

        mock_article = MagicMock()
        mock_article.user_id = 99  # belongs to someone else
        mock_db.session.get.return_value = mock_article

        with recap_app.app_context():
            result = classify_url("https://example.com/dup", 7, article_id=42)

        assert result is None
        mock_AiApiHelper.ClassifyUrl.assert_not_called()

    @patch("recap.tasks._build_category_list", return_value=[])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_legacy_jobs_without_article_id_use_url_lookup(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        from recap.tasks import classify_url

        mock_Article.get_article_by_url_path.return_value = MagicMock()
        mock_AiApiHelper.ClassifyUrl.return_value = dict(self._RESULT)

        with recap_app.app_context():
            classify_url("https://example.com/old-job", 7)

        mock_Article.get_article_by_url_path.assert_called_once_with("https://example.com/old-job", 7)
        mock_db.session.get.assert_not_called()


@pytest.mark.unit
@pytest.mark.recap
class TestClassifyUrlContentStorage:
    """classify_url uses stored text when present, stores crawled text, and records the fetch result."""

    _RESULT = {
        "summary": "S",
        "blog_title": "T",
        "author": "A",
        "category": "C",
        "key_topics": [],
        "sub_categories": [],
    }

    def _run(self, recap_app, mock_db, mock_AiApiHelper, article, result):
        from recap import tasks
        from recap.tasks import classify_url

        mock_db.session.get.return_value = article
        mock_AiApiHelper.ClassifyUrl.return_value = result
        with patch.object(tasks.app, "redis", MagicMock()):
            with recap_app.app_context():
                return classify_url("https://medium.com/x/post", 7, article_id=1)

    @patch("recap.tasks._build_category_list", return_value=[])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_stored_extension_text_is_classified_without_crawl(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        article = MagicMock(user_id=7, content_text="Text captured by the extension.", content_source="extension")
        self._run(recap_app, mock_db, mock_AiApiHelper, article, dict(self._RESULT))

        assert mock_AiApiHelper.ClassifyUrl.call_args[1]["content"] == "Text captured by the extension."
        assert article.content_source == "extension"  # unchanged
        assert article.content_text == "Text captured by the extension."

    @patch("recap.tasks._build_category_list", return_value=[])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_crawled_text_is_stored_and_kept_out_of_job_result(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, recap_app
    ):
        article = MagicMock(user_id=7, content_text=None)
        result = self._run(
            recap_app, mock_db, mock_AiApiHelper, article, {**self._RESULT, "fetched_content": "Crawled text."}
        )

        assert article.content_text == "Crawled text."
        assert article.content_source == "crawl"
        assert article.fetch_status == "ok"
        assert "fetched_content" not in result

    @pytest.mark.parametrize(
        "flags, expected_status",
        [({"site_blocked": True}, "blocked"), ({"site_down": True}, "down"), ({}, "empty")],
    )
    @patch("recap.tasks._build_category_list", return_value=[])
    @patch("recap.tasks.AiApiHelper")
    @patch("recap.tasks.Article")
    @patch("recap.tasks.db")
    def test_failed_crawl_records_fetch_status(
        self, mock_db, mock_Article, mock_AiApiHelper, mock_build_cats, flags, expected_status, recap_app
    ):
        article = MagicMock(user_id=7, content_text=None, classified=None)
        self._run(recap_app, mock_db, mock_AiApiHelper, article, {**self._RESULT, **flags})

        assert article.content_source == "url_only"
        assert article.fetch_status == expected_status


@pytest.mark.unit
@pytest.mark.recap
class TestMaybePingAiapi:
    """Tests for maybe_ping_aiapi() — Redis-throttled keep-alive enqueue logic."""

    def test_enqueues_when_key_absent(self, recap_app):
        """When the throttle key is absent, sets it and enqueues the ping task."""
        from recap import maybe_ping_aiapi

        mock_redis = MagicMock()
        mock_redis.exists.return_value = False
        mock_queue = MagicMock()

        with patch.object(recap_app, "redis", mock_redis), patch.object(recap_app, "task_queue", mock_queue):
            with recap_app.app_context():
                maybe_ping_aiapi()

        mock_redis.exists.assert_called_once_with("aiapi:ping:last")
        mock_redis.setex.assert_called_once_with("aiapi:ping:last", 600, "1")
        mock_queue.enqueue.assert_called_once_with("recap.tasks.ping_aiapi")

    def test_no_enqueue_when_key_present(self, recap_app):
        """When the throttle key exists, nothing is enqueued (throttle active)."""
        from recap import maybe_ping_aiapi

        mock_redis = MagicMock()
        mock_redis.exists.return_value = True
        mock_queue = MagicMock()

        with patch.object(recap_app, "redis", mock_redis), patch.object(recap_app, "task_queue", mock_queue):
            with recap_app.app_context():
                maybe_ping_aiapi()

        mock_redis.setex.assert_not_called()
        mock_queue.enqueue.assert_not_called()


@pytest.mark.unit
@pytest.mark.recap
class TestSendPasswordResetEmailTask:
    """Tests for send_password_reset_email_task."""

    @patch("recap.tasks.send_password_reset_email")
    @patch("recap.tasks.User")
    def test_looks_up_user_and_sends_email(self, mock_User, mock_send_email, recap_app):
        """Task fetches the user by ID and passes it to send_password_reset_email."""
        from recap.tasks import send_password_reset_email_task

        mock_user = MagicMock()
        mock_User.query.get.return_value = mock_user

        send_password_reset_email_task(42)

        mock_User.query.get.assert_called_once_with(42)
        mock_send_email.assert_called_once_with(mock_user)

    @patch("recap.tasks.send_password_reset_email")
    @patch("recap.tasks.User")
    def test_sends_email_for_correct_user_id(self, mock_User, mock_send_email, recap_app):
        """User ID is forwarded correctly to the query."""
        from recap.tasks import send_password_reset_email_task

        mock_User.query.get.return_value = MagicMock(id=99)

        send_password_reset_email_task(99)

        called_with = mock_User.query.get.call_args[0][0]
        assert called_with == 99
