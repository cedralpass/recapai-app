import pytest
from recap.models import User, Article

@pytest.mark.unit
@pytest.mark.recap
class TestUser:
    def test_password_hashing(self, recap_app):
        """Test password hashing works as expected."""
        with recap_app.app_context():
            u = User(username='test')
            u.set_password('cat')
            assert not u.check_password('dog')
            assert u.check_password('cat')
    
    def test_user_representation(self, recap_app):
        """Test string representation of user."""
        with recap_app.app_context():
            u = User(username='test')
            assert str(u) == '<User test>'

@pytest.mark.unit
@pytest.mark.recap
class TestArticle:
    def test_article_user_relationship(self, recap_app):
        """Test relationship between Article and User."""
        with recap_app.app_context():
            user = User(username='test2', email='test2@example.com')
            article = Article(url_path='http://example.com', user=user)
            assert article.user == user 