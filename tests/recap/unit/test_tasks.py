"""Unit tests for recap/tasks.py background jobs."""
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock


@pytest.mark.unit
@pytest.mark.recap
class TestSaveClassificationResult:
    """Tests for save_classification_result — pure attribute-mapping logic."""

    def test_sets_all_fields(self, recap_app):
        """All classification fields are written to the article."""
        from recap.tasks import save_classification_result
        from recap.models import Article

        with recap_app.app_context():
            article = Article(url_path='https://example.com/article', user_id=1)
            classify_result = {
                'summary': 'A summary.',
                'blog_title': 'Blog Title',
                'author': 'Jane Doe',
                'category': 'Technology',
                'key_topics': ['AI', 'ML'],
                'sub_categories': ['Deep Learning'],
            }
            save_classification_result(classify_result, article)

        assert article.summary == 'A summary.'
        assert article.title == 'Blog Title'
        assert article.author_name == 'Jane Doe'
        assert article.category == 'Technology'
        assert json.loads(article.key_topics) == ['AI', 'ML']
        assert json.loads(article.sub_categories) == ['Deep Learning']
        assert article.classified is not None

    def test_classified_timestamp_is_recent_utc(self, recap_app):
        """classified is set to approximately now in UTC."""
        from recap.tasks import save_classification_result
        from recap.models import Article

        before = datetime.now(timezone.utc)
        with recap_app.app_context():
            article = Article(url_path='https://example.com/ts', user_id=1)
            save_classification_result(
                {'summary': 'S', 'blog_title': 'T', 'author': 'A',
                 'category': 'C', 'key_topics': [], 'sub_categories': []},
                article,
            )
        after = datetime.now(timezone.utc)

        classified = article.classified
        if classified.tzinfo is None:
            classified = classified.replace(tzinfo=timezone.utc)
        assert before <= classified <= after

    def test_missing_key_topics_defaults_to_empty_list(self, recap_app):
        """When key_topics is absent, article.key_topics is serialised as []."""
        from recap.tasks import save_classification_result
        from recap.models import Article

        with recap_app.app_context():
            article = Article(url_path='https://example.com/notopics', user_id=1)
            save_classification_result(
                {'summary': 'S', 'blog_title': 'T', 'author': 'A', 'category': 'C'},
                article,
            )

        assert json.loads(article.key_topics) == []

    def test_missing_sub_categories_defaults_to_empty_list(self, recap_app):
        """When sub_categories is absent, article.sub_categories is serialised as []."""
        from recap.tasks import save_classification_result
        from recap.models import Article

        with recap_app.app_context():
            article = Article(url_path='https://example.com/nosub', user_id=1)
            save_classification_result(
                {'summary': 'S', 'blog_title': 'T', 'author': 'A',
                 'category': 'C', 'key_topics': ['X']},
                article,
            )

        assert json.loads(article.sub_categories) == []


@pytest.mark.unit
@pytest.mark.recap
class TestClassifyUrl:
    """Tests for classify_url — orchestration of article lookup, AI call, and save."""

    @patch('recap.tasks.AiApiHelper')
    @patch('recap.tasks.Article')
    @patch('recap.tasks.db')
    def test_happy_path_returns_classify_result(
        self, mock_db, mock_Article, mock_AiApiHelper, recap_app
    ):
        """classify_url finds article, calls ClassifyUrl, saves result, and returns it."""
        from recap.tasks import classify_url

        mock_article = MagicMock()
        mock_Article.get_article_by_url_path.return_value = mock_article

        classify_result = {
            'summary': 'Test summary',
            'blog_title': 'Test Title',
            'author': 'Author',
            'category': 'Technology',
            'key_topics': ['AI'],
            'sub_categories': ['ML'],
        }
        mock_AiApiHelper.ClassifyUrl.return_value = classify_result

        with recap_app.app_context():
            result = classify_url('https://example.com/article', 1)

        assert result == classify_result
        mock_Article.get_article_by_url_path.assert_called_once_with(
            'https://example.com/article', 1
        )
        mock_AiApiHelper.ClassifyUrl.assert_called_once_with(
            'https://example.com/article', 1
        )

    @patch('recap.tasks.AiApiHelper')
    @patch('recap.tasks.Article')
    @patch('recap.tasks.db')
    def test_happy_path_commits_article_to_db(
        self, mock_db, mock_Article, mock_AiApiHelper, recap_app
    ):
        """After classification, article is added and committed to the DB session."""
        from recap.tasks import classify_url

        mock_article = MagicMock()
        mock_Article.get_article_by_url_path.return_value = mock_article
        mock_AiApiHelper.ClassifyUrl.return_value = {
            'summary': 'S', 'blog_title': 'T', 'author': 'A',
            'category': 'C', 'key_topics': [], 'sub_categories': [],
        }

        with recap_app.app_context():
            classify_url('https://example.com/article', 1)

        mock_db.session.add.assert_called_once_with(mock_article)
        mock_db.session.commit.assert_called_once()

    @patch('recap.tasks.AiApiHelper')
    @patch('recap.tasks.Article')
    @patch('recap.tasks.db')
    def test_exception_is_caught_and_returns_none(
        self, mock_db, mock_Article, mock_AiApiHelper, recap_app
    ):
        """When AiApiHelper raises, classify_url swallows the error and returns None."""
        from recap.tasks import classify_url

        mock_Article.get_article_by_url_path.return_value = MagicMock()
        mock_AiApiHelper.ClassifyUrl.side_effect = Exception('API failure')

        with recap_app.app_context():
            result = classify_url('https://example.com/article', 1)

        assert result is None
        mock_db.session.commit.assert_not_called()

    @patch('recap.tasks.AiApiHelper')
    @patch('recap.tasks.Article')
    @patch('recap.tasks.db')
    def test_article_not_found_exception_caught(
        self, mock_db, mock_Article, mock_AiApiHelper, recap_app
    ):
        """When get_article_by_url_path raises, exception is caught gracefully."""
        from recap.tasks import classify_url

        mock_Article.get_article_by_url_path.side_effect = Exception('DB error')

        with recap_app.app_context():
            result = classify_url('https://example.com/article', 1)

        assert result is None
        mock_AiApiHelper.ClassifyUrl.assert_not_called()


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

        with patch.object(recap_app, 'redis', mock_redis), \
             patch.object(recap_app, 'task_queue', mock_queue):
            with recap_app.app_context():
                maybe_ping_aiapi()

        mock_redis.exists.assert_called_once_with('aiapi:ping:last')
        mock_redis.setex.assert_called_once_with('aiapi:ping:last', 600, '1')
        mock_queue.enqueue.assert_called_once_with('recap.tasks.ping_aiapi')

    def test_no_enqueue_when_key_present(self, recap_app):
        """When the throttle key exists, nothing is enqueued (throttle active)."""
        from recap import maybe_ping_aiapi

        mock_redis = MagicMock()
        mock_redis.exists.return_value = True
        mock_queue = MagicMock()

        with patch.object(recap_app, 'redis', mock_redis), \
             patch.object(recap_app, 'task_queue', mock_queue):
            with recap_app.app_context():
                maybe_ping_aiapi()

        mock_redis.setex.assert_not_called()
        mock_queue.enqueue.assert_not_called()


@pytest.mark.unit
@pytest.mark.recap
class TestSendPasswordResetEmailTask:
    """Tests for send_password_reset_email_task."""

    @patch('recap.tasks.send_password_reset_email')
    @patch('recap.tasks.User')
    def test_looks_up_user_and_sends_email(self, mock_User, mock_send_email, recap_app):
        """Task fetches the user by ID and passes it to send_password_reset_email."""
        from recap.tasks import send_password_reset_email_task

        mock_user = MagicMock()
        mock_User.query.get.return_value = mock_user

        send_password_reset_email_task(42)

        mock_User.query.get.assert_called_once_with(42)
        mock_send_email.assert_called_once_with(mock_user)

    @patch('recap.tasks.send_password_reset_email')
    @patch('recap.tasks.User')
    def test_sends_email_for_correct_user_id(
        self, mock_User, mock_send_email, recap_app
    ):
        """User ID is forwarded correctly to the query."""
        from recap.tasks import send_password_reset_email_task

        mock_User.query.get.return_value = MagicMock(id=99)

        send_password_reset_email_task(99)

        called_with = mock_User.query.get.call_args[0][0]
        assert called_with == 99
