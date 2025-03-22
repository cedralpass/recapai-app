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
        print("\nTest Configuration:")
        print(f"TESTING: {recap_app.config['TESTING']}")
        print(f"WTF_CSRF_ENABLED: {recap_app.config.get('WTF_CSRF_ENABLED')}")
        print(f"SECRET_KEY: {recap_app.config.get('SECRET_KEY')}")
        
        with recap_app.app_context():
            # Get registration form to get CSRF token
            response = recap_client.get('/auth/register')
            assert response.status_code == 200
            
            # Register new user
            # Register new user
            data = {
                'username': 'newuser',
                'email': 'new@example.com',
                'password': 'testpass123',
                'password2': 'testpass123',
                'submit': 'Register'
            }
            print('\nSubmitting registration with data:', data)
            response = recap_client.post('/auth/register', data=data, follow_redirects=True)
            print('Response status:', response.status_code)
            
            # Print response data for debugging
            response_text = response.data.decode()
            print('\nResponse data preview (first 500 chars):', response_text[:500])
            
            # Check if we're still on the registration form
            if '<form action="" method="post">' in response_text:
                print('\nStill on registration form - form validation may have failed')
                if 'error' in response_text.lower():
                    print('Found error message in response')
            
            assert response.status_code == 200
            assert b'Congratulations, you are now a registered user!' in response.data
            
            # Verify user was created
            user = User.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.check_password('testpass123')
            
            # Try to login with new user
            response = recap_client.post('/auth/login', data={
                'username': 'newuser',
                'password': 'testpass123',
                'remember_me': False
            }, follow_redirects=True)
            assert response.status_code == 200
            assert b'Invalid username or password' not in response.data

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