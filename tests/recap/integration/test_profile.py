"""Integration tests for recap/profile — user, edit_profile, organize_taxonomy, apply_taxonomy."""
import pytest
from unittest.mock import patch
from recap.models import User, Article
from recap import db


@pytest.mark.integration
@pytest.mark.recap
class TestUserProfileRoute:
    def test_user_profile_returns_200(self, authenticated_client, recap_app, test_user):
        """GET /user/<username> returns 200 for an existing user."""
        with recap_app.app_context():
            username = test_user.username

        response = authenticated_client.get(f'/user/{username}')
        assert response.status_code == 200

    def test_user_profile_shows_username(self, authenticated_client, recap_app, test_user):
        """The profile page renders the user's username."""
        with recap_app.app_context():
            username = test_user.username

        response = authenticated_client.get(f'/user/{username}')
        assert username.encode() in response.data

    def test_user_profile_with_articles(self, authenticated_client, recap_app, test_user):
        """Articles owned by the user are visible on their profile page."""
        with recap_app.app_context():
            db.session.add(Article(
                url_path='https://example.com/profile-article',
                user_id=test_user.id,
            ))
            db.session.commit()
            username = test_user.username

        response = authenticated_client.get(f'/user/{username}')
        assert response.status_code == 200
        assert b'profile-article' in response.data

    def test_user_profile_404_for_unknown_user(self, authenticated_client):
        """GET /user/<nonexistent> returns 404."""
        response = authenticated_client.get('/user/nobody-exists-xyz')
        assert response.status_code == 404

    def test_user_profile_requires_login(self, recap_client, recap_app, test_user):
        """Unauthenticated GET redirects to login."""
        with recap_app.app_context():
            username = test_user.username

        response = recap_client.get(f'/user/{username}')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.integration
@pytest.mark.recap
class TestEditProfileRoute:
    def test_get_prepopulates_form_with_current_values(
        self, authenticated_client, recap_app, test_user
    ):
        """GET /edit_profile renders form pre-filled with the current user's data."""
        with recap_app.app_context():
            username = test_user.username
            email = test_user.email

        response = authenticated_client.get('/edit_profile')
        assert response.status_code == 200
        assert username.encode() in response.data
        assert email.encode() in response.data

    def test_post_updates_username(self, authenticated_client, recap_app, test_user):
        """POST /edit_profile with a new username persists the change."""
        with recap_app.app_context():
            user_id = test_user.id

        response = authenticated_client.post(
            '/edit_profile',
            data={
                'username': 'updateduser',
                'email': 'test@example.com',
                'phone': '1234567890',
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'Your changes have been saved' in response.data

        with recap_app.app_context():
            user = db.session.get(User, user_id)
            assert user.username == 'updateduser'

    def test_post_duplicate_username_shows_error(
        self, authenticated_client, recap_app, test_user
    ):
        """POST with an already-taken username shows a validation error."""
        with recap_app.app_context():
            other = User(username='takenuser', email='taken@example.com')
            other.set_password('pass')
            db.session.add(other)
            db.session.commit()

        response = authenticated_client.post(
            '/edit_profile',
            data={
                'username': 'takenuser',
                'email': 'test@example.com',
                'phone': '1234567890',
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'different username' in response.data

    def test_edit_profile_requires_login(self, recap_client):
        """Unauthenticated GET redirects to login."""
        response = recap_client.get('/edit_profile')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.integration
@pytest.mark.recap
class TestOrganizeTaxonomyRoute:
    @patch('recap.profile.AiApiHelper')
    def test_organize_taxonomy_returns_200(
        self, mock_ai, authenticated_client, recap_app, test_user
    ):
        """GET /organize_taxonomy returns 200 when AI responds successfully."""
        mock_ai.PerformTask.return_value = {
            'description': 'Consolidated some overlapping categories.',
            'mappings': [
                {'old_category': 'Tech', 'new_category': 'Technology'},
            ],
        }

        with recap_app.app_context():
            db.session.add(Article(
                url_path='https://a.com/1', user_id=test_user.id, category='Tech',
            ))
            db.session.commit()

        response = authenticated_client.get('/organize_taxonomy')
        assert response.status_code == 200

    @patch('recap.profile.AiApiHelper')
    def test_organize_taxonomy_shows_ai_description(
        self, mock_ai, authenticated_client, recap_app, test_user
    ):
        """The AI-generated description appears in the rendered page."""
        mock_ai.PerformTask.return_value = {
            'description': 'Merged Tech and Software into Technology.',
            'mappings': [
                {'old_category': 'Tech', 'new_category': 'Technology'},
                {'old_category': 'Software', 'new_category': 'Technology'},
            ],
        }

        with recap_app.app_context():
            db.session.add(Article(
                url_path='https://a.com/2', user_id=test_user.id, category='Tech',
            ))
            db.session.commit()

        response = authenticated_client.get('/organize_taxonomy')
        assert b'Merged Tech and Software into Technology.' in response.data

    @patch('recap.profile.AiApiHelper')
    def test_organize_taxonomy_stores_mapping_in_session(
        self, mock_ai, authenticated_client, recap_app, test_user
    ):
        """After the AI call, the category mapping is stored in the session."""
        mock_ai.PerformTask.return_value = {
            'description': 'Some changes.',
            'mappings': [{'old_category': 'Tech', 'new_category': 'Technology'}],
        }

        with recap_app.app_context():
            db.session.add(Article(
                url_path='https://a.com/3', user_id=test_user.id, category='Tech',
            ))
            db.session.commit()

        authenticated_client.get('/organize_taxonomy')

        with authenticated_client.session_transaction() as sess:
            assert 'category_mapping' in sess
            assert sess['category_mapping'] == {'Tech': 'Technology'}

    def test_organize_taxonomy_requires_login(self, recap_client):
        """Unauthenticated GET redirects to login."""
        response = recap_client.get('/organize_taxonomy')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.integration
@pytest.mark.recap
class TestApplyTaxonomyRoute:
    def test_apply_taxonomy_updates_article_categories(
        self, authenticated_client, recap_app, test_user
    ):
        """POST /apply_taxonomy remaps article categories per the session mapping."""
        with recap_app.app_context():
            article = Article(
                url_path='https://a.com/remap', user_id=test_user.id, category='Tech',
            )
            db.session.add(article)
            db.session.commit()
            article_id = article.id

        with authenticated_client.session_transaction() as sess:
            sess['category_mapping'] = {'Tech': 'Technology'}

        response = authenticated_client.post('/apply_taxonomy', follow_redirects=True)
        assert response.status_code == 200
        assert b'updated successfully' in response.data

        with recap_app.app_context():
            updated = db.session.get(Article, article_id)
            assert updated.category == 'Technology'

    def test_apply_taxonomy_clears_session_mapping(
        self, authenticated_client, recap_app, test_user
    ):
        """After applying, category_mapping is removed from the session."""
        with recap_app.app_context():
            db.session.add(Article(
                url_path='https://a.com/clear', user_id=test_user.id, category='Tech',
            ))
            db.session.commit()

        with authenticated_client.session_transaction() as sess:
            sess['category_mapping'] = {'Tech': 'Technology'}

        authenticated_client.post('/apply_taxonomy', follow_redirects=True)

        with authenticated_client.session_transaction() as sess:
            assert 'category_mapping' not in sess

    def test_apply_taxonomy_without_session_redirects(
        self, authenticated_client
    ):
        """POST without a session mapping redirects to organize_taxonomy."""
        response = authenticated_client.post('/apply_taxonomy', follow_redirects=False)
        assert response.status_code == 302
        assert 'organize_taxonomy' in response.headers['Location']

    def test_apply_taxonomy_requires_login(self, recap_client):
        """Unauthenticated POST redirects to login."""
        response = recap_client.post('/apply_taxonomy')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.unit
@pytest.mark.recap
class TestCreateCategoryMapping:
    def test_converts_list_to_dict(self, recap_app):
        """create_category_mapping converts the AI mappings list to a dict."""
        from recap.profile import create_category_mapping

        mappings = [
            {'old_category': 'Tech', 'new_category': 'Technology'},
            {'old_category': 'AI', 'new_category': 'Artificial Intelligence'},
        ]
        result = create_category_mapping(mappings)
        assert result == {
            'Tech': 'Technology',
            'AI': 'Artificial Intelligence',
        }

    def test_returns_empty_dict_for_empty_list(self, recap_app):
        """create_category_mapping returns {} for an empty mappings list."""
        from recap.profile import create_category_mapping
        assert create_category_mapping([]) == {}
