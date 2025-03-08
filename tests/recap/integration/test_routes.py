import pytest
from flask_login import current_user
from recap.models import User
from recap import db

@pytest.mark.integration
@pytest.mark.recap
class TestAuth:
    def test_login_page(self, recap_client):
        """Test that login page loads correctly."""
        response = recap_client.get('/auth/login')
        assert response.status_code == 200
        assert b'Sign In' in response.data

    def test_register_and_login(self, recap_client, recap_app):
        """Test user registration and login flow."""
        # Register new user
        response = recap_client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'testpass123',
            'password2': 'testpass123'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Try to login with new user
        response = recap_client.post('/auth/login', data={
            'username': 'newuser',
            'password': 'testpass123',
            'remember_me': False
        }, follow_redirects=True)
        assert response.status_code == 200
        with recap_app.test_request_context():
            user = User.query.filter_by(username='newuser').first()
            assert user is not None

@pytest.mark.integration
@pytest.mark.recap
class TestArticles:
    def test_add_article(self, authenticated_client):
        """Test adding a new article."""
        response = authenticated_client.post('/', data={
            'url_path': 'http://example.com/article'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Your article is being classified' in response.data 