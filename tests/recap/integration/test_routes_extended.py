"""Integration tests for recap/routes.py — index, show, add_article, delete, reclassify."""
import pytest
from recap.models import User, Article
from recap import db


@pytest.mark.integration
@pytest.mark.recap
class TestIndexRoute:
    def test_unauthenticated_index_loads(self, recap_client):
        """Unauthenticated GET / returns 200."""
        response = recap_client.get('/')
        assert response.status_code == 200

    def test_authenticated_index_shows_articles(self, authenticated_client, recap_app, test_user):
        """Authenticated GET / renders articles for the logged-in user."""
        with recap_app.app_context():
            db.session.add(Article(url_path='https://example.com/my-article', user_id=test_user.id))
            db.session.commit()

        response = authenticated_client.get('/')
        assert response.status_code == 200
        assert b'my-article' in response.data

    def test_category_filter_limits_results(self, authenticated_client, recap_app, test_user):
        """GET /?category=Tech returns only Tech articles."""
        with recap_app.app_context():
            db.session.add(Article(
                url_path='https://example.com/tech', user_id=test_user.id, category='Tech',
            ))
            db.session.add(Article(
                url_path='https://example.com/science', user_id=test_user.id, category='Science',
            ))
            db.session.commit()

        response = authenticated_client.get('/?category=Tech')
        assert response.status_code == 200
        assert b'tech' in response.data
        assert b'science' not in response.data

    def test_index_also_accessible_via_slash_index(self, recap_client):
        """GET /index is the same route as /."""
        response = recap_client.get('/index')
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.recap
class TestShowRoute:
    def _create_article(self, recap_app, user_id, **kwargs):
        with recap_app.app_context():
            article = Article(
                url_path=kwargs.get('url_path', 'https://example.com/show-test'),
                title=kwargs.get('title', 'Show Test Title'),
                summary=kwargs.get('summary', 'A summary.'),
                author_name=kwargs.get('author_name', 'Author'),
                category=kwargs.get('category', 'Tech'),
                key_topics='["topic1"]',
                sub_categories='["sub1"]',
                user_id=user_id,
            )
            db.session.add(article)
            db.session.commit()
            return article.id

    def test_show_html_returns_200(self, authenticated_client, recap_app, test_user):
        """GET /<id>/show renders the article page."""
        article_id = self._create_article(recap_app, test_user.id)
        response = authenticated_client.get(f'/{article_id}/show')
        assert response.status_code == 200

    def test_show_json_returns_article_fields(self, authenticated_client, recap_app, test_user):
        """GET /<id>/show with JSON Content-Type returns article as JSON."""
        article_id = self._create_article(
            recap_app, test_user.id,
            url_path='https://example.com/json-article',
            title='JSON Title',
        )
        response = authenticated_client.get(
            f'/{article_id}/show',
            headers={'Content-Type': 'application/json'},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['url_path'] == 'https://example.com/json-article'
        assert data['title'] == 'JSON Title'
        assert 'id' in data
        assert 'summary' in data

    def test_show_requires_login(self, recap_client, recap_app, test_user):
        """GET /<id>/show redirects unauthenticated users to login."""
        article_id = self._create_article(recap_app, test_user.id)
        response = recap_client.get(f'/{article_id}/show')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.integration
@pytest.mark.recap
class TestAddArticleRoute:
    def test_get_shows_form(self, authenticated_client):
        """GET /add_article renders the add article form."""
        response = authenticated_client.get('/add_article')
        assert response.status_code == 200

    def test_post_creates_article_and_redirects(
        self, authenticated_client, recap_app, test_user, mocker
    ):
        """POST /add_article creates an article and redirects to index."""
        mock_job = mocker.MagicMock()
        mock_job.id = 'job-add-article-test'
        mocker.patch.object(recap_app.task_queue, 'enqueue', return_value=mock_job)

        response = authenticated_client.post(
            '/add_article',
            data={'url_path': 'https://example.com/add-test'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'being classified' in response.data

    def test_post_persists_article_to_db(
        self, authenticated_client, recap_app, test_user, mocker
    ):
        """POST /add_article saves the article row linked to the current user."""
        mock_job = mocker.MagicMock()
        mock_job.id = 'job-persist-test'
        mocker.patch.object(recap_app.task_queue, 'enqueue', return_value=mock_job)

        url = 'https://example.com/persist-test'
        authenticated_client.post('/add_article', data={'url_path': url})

        with recap_app.app_context():
            article = Article.get_article_by_url_path(url, test_user.id)
            assert article is not None
            assert article.user_id == test_user.id

    def test_get_requires_login(self, recap_client):
        """GET /add_article redirects unauthenticated users to login."""
        response = recap_client.get('/add_article')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.integration
@pytest.mark.recap
class TestDeleteRoute:
    def test_delete_removes_article(self, authenticated_client, recap_app, test_user):
        """GET /<id>/delete removes the article and redirects to index."""
        with recap_app.app_context():
            article = Article(url_path='https://example.com/to-delete', user_id=test_user.id)
            db.session.add(article)
            db.session.commit()
            article_id = article.id

        response = authenticated_client.get(f'/{article_id}/delete', follow_redirects=True)
        assert response.status_code == 200

        with recap_app.app_context():
            gone = Article.get_article_by_url_path('https://example.com/to-delete', test_user.id)
            assert gone is None

    def test_delete_requires_login(self, recap_client):
        """DELETE without login redirects to login."""
        response = recap_client.get('/999/delete')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.integration
@pytest.mark.recap
class TestReclassifyRoute:
    def test_reclassify_enqueues_job_and_redirects(
        self, authenticated_client, recap_app, test_user, mocker
    ):
        """GET /<id>/reclassify enqueues classify_url job and redirects to index."""
        with recap_app.app_context():
            article = Article(
                url_path='https://example.com/reclassify-me', user_id=test_user.id
            )
            db.session.add(article)
            db.session.commit()
            article_id = article.id

        mock_job = mocker.MagicMock()
        mock_job.id = 'job-reclassify'
        mock_job.get_status.return_value = 'queued'
        mock_enqueue = mocker.patch.object(
            recap_app.task_queue, 'enqueue', return_value=mock_job
        )

        response = authenticated_client.get(f'/{article_id}/reclassify', follow_redirects=True)
        assert response.status_code == 200
        mock_enqueue.assert_called_once()
        assert mock_enqueue.call_args[0][0] == 'recap.tasks.classify_url'


@pytest.mark.integration
@pytest.mark.recap
class TestCssRoute:
    def test_css_get_returns_200(self, recap_client):
        """GET /css returns 200."""
        response = recap_client.get('/css')
        assert response.status_code == 200

    def test_css_get_with_json_content_type_returns_json(self, recap_client):
        """GET /css with Content-Type: application/json returns JSON body."""
        response = recap_client.get('/css', headers={'Content-Type': 'application/json'})
        assert response.status_code == 200
        assert response.get_json() == 'css'


@pytest.mark.integration
@pytest.mark.recap
class TestJobRoute:
    def test_job_enqueues_example_task(self, authenticated_client, recap_app, mocker):
        """GET /job enqueues the example task and returns job id in body."""
        mock_job = mocker.MagicMock()
        mock_job.id = 'example-job-id'
        mock_job.get_status.return_value = 'queued'
        mocker.patch.object(recap_app.task_queue, 'enqueue', return_value=mock_job)

        response = authenticated_client.get('/job')
        assert response.status_code == 200
        assert b'example-job-id' in response.data

    def test_job_requires_login(self, recap_client):
        """Unauthenticated GET /job redirects to login."""
        response = recap_client.get('/job')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.integration
@pytest.mark.recap
class TestJobShowRoute:
    def test_job_show_returns_status_json(self, authenticated_client, recap_app, mocker):
        """GET /job/<id>/show returns job id, status, and description as JSON."""
        mock_job = mocker.MagicMock()
        mock_job.id = 'show-job-id'
        mock_job.get_status.return_value = 'finished'
        mock_job.description = 'example task'
        mock_job.meta = {}
        mocker.patch.object(recap_app.task_queue, 'fetch_job', return_value=mock_job)

        response = authenticated_client.get('/job/show-job-id/show')
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == 'show-job-id'
        assert data['status'] == 'finished'
        assert data['description'] == 'example task'

    def test_job_show_requires_login(self, recap_client):
        """Unauthenticated GET redirects to login."""
        response = recap_client.get('/job/some-id/show')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']
