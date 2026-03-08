import pytest
from recap.models import User, Article
from recap import db


@pytest.mark.integration
@pytest.mark.recap
class TestPostArticleApi:
    def test_returns_401_without_auth_header(self, recap_client):
        """Request with no Authorization header returns 401."""
        response = recap_client.post(
            '/api/v1/articles',
            json={'url': 'https://example.com/article'},
        )
        assert response.status_code == 401

    def test_returns_401_with_invalid_token(self, recap_client):
        """Request with a token that matches no user returns 401."""
        response = recap_client.post(
            '/api/v1/articles',
            json={'url': 'https://example.com/article'},
            headers={'Authorization': 'Bearer notarealtoken'},
        )
        assert response.status_code == 401

    def test_returns_400_when_url_missing(self, recap_client, test_user, recap_app):
        """Request with a valid token but no url field returns 400."""
        with recap_app.app_context():
            token = test_user.get_or_create_api_token()

        response = recap_client.post(
            '/api/v1/articles',
            json={},
            headers={'Authorization': f'Bearer {token}'},
        )
        assert response.status_code == 400
        assert b'url' in response.data

    def test_returns_400_when_body_is_not_json(self, recap_client, test_user, recap_app):
        """Non-JSON request body returns 400."""
        with recap_app.app_context():
            token = test_user.get_or_create_api_token()

        response = recap_client.post(
            '/api/v1/articles',
            data='not json',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'text/plain',
            },
        )
        assert response.status_code == 400

    def test_returns_201_and_queues_job(self, recap_client, test_user, recap_app, mocker):
        """Valid request creates an article and returns 201 with article_id."""
        mock_job = mocker.MagicMock()
        mock_job.id = 'test-job-abc'
        mocker.patch.object(recap_app.task_queue, 'enqueue', return_value=mock_job)

        with recap_app.app_context():
            token = test_user.get_or_create_api_token()

        response = recap_client.post(
            '/api/v1/articles',
            json={'url': 'https://example.com/test-article'},
            headers={'Authorization': f'Bearer {token}'},
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'queued'
        assert 'article_id' in data

    def test_creates_article_record_in_db(self, recap_client, test_user, recap_app, mocker):
        """Valid request persists an Article row linked to the token owner."""
        mock_job = mocker.MagicMock()
        mock_job.id = 'test-job-xyz'
        mocker.patch.object(recap_app.task_queue, 'enqueue', return_value=mock_job)

        url = 'https://example.com/db-article'
        with recap_app.app_context():
            token = test_user.get_or_create_api_token()
            user_id = test_user.id

        recap_client.post(
            '/api/v1/articles',
            json={'url': url},
            headers={'Authorization': f'Bearer {token}'},
        )

        with recap_app.app_context():
            article = Article.get_article_by_url_path(url, user_id)
            assert article is not None
            assert article.url_path == url
            assert article.user_id == user_id

    def test_enqueues_classify_url_task(self, recap_client, test_user, recap_app, mocker):
        """Valid request enqueues the recap.tasks.classify_url RQ task."""
        mock_job = mocker.MagicMock()
        mock_job.id = 'test-job-enqueue'
        mock_enqueue = mocker.patch.object(
            recap_app.task_queue, 'enqueue', return_value=mock_job
        )

        url = 'https://example.com/enqueue-article'
        with recap_app.app_context():
            token = test_user.get_or_create_api_token()
            user_id = test_user.id

        recap_client.post(
            '/api/v1/articles',
            json={'url': url},
            headers={'Authorization': f'Bearer {token}'},
        )

        mock_enqueue.assert_called_once()
        call_kwargs = mock_enqueue.call_args
        # First positional arg is the task name
        assert call_kwargs[0][0] == 'recap.tasks.classify_url'
