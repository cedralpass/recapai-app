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
class TestUserApiToken:
    def test_api_token_starts_as_none(self, recap_app):
        """New user has no api_token by default."""
        with recap_app.app_context():
            u = User(username='tokentest', email='tokentest@example.com')
            assert u.api_token is None

    def test_get_or_create_api_token_generates_token(self, recap_app):
        """get_or_create_api_token creates and persists a token."""
        from recap import db
        with recap_app.app_context():
            u = User(username='tokentest2', email='tokentest2@example.com')
            u.set_password('pass')
            db.session.add(u)
            db.session.commit()

            token = u.get_or_create_api_token()
            assert token is not None
            assert len(token) > 16
            # persisted to DB
            assert u.api_token == token

    def test_get_or_create_api_token_is_idempotent(self, recap_app):
        """Calling get_or_create_api_token twice returns the same token."""
        from recap import db
        with recap_app.app_context():
            u = User(username='tokentest3', email='tokentest3@example.com')
            u.set_password('pass')
            db.session.add(u)
            db.session.commit()

            token1 = u.get_or_create_api_token()
            token2 = u.get_or_create_api_token()
            assert token1 == token2

    def test_api_token_is_unique_across_users(self, recap_app):
        """Two different users get different api_tokens."""
        from recap import db
        with recap_app.app_context():
            u1 = User(username='tokenuser1', email='tu1@example.com')
            u1.set_password('pass')
            u2 = User(username='tokenuser2', email='tu2@example.com')
            u2.set_password('pass')
            db.session.add_all([u1, u2])
            db.session.commit()

            assert u1.get_or_create_api_token() != u2.get_or_create_api_token()


@pytest.mark.unit
@pytest.mark.recap
class TestArticle:
    def test_article_user_relationship(self, recap_app):
        """Test relationship between Article and User."""
        with recap_app.app_context():
            user = User(username='test2', email='test2@example.com')
            article = Article(url_path='http://example.com', user=user)
            assert article.user == user 