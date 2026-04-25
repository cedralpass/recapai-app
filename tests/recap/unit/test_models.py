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


@pytest.mark.unit
@pytest.mark.recap
class TestArticleMethods:
    def test_article_repr(self, recap_app):
        """Article.__repr__ returns the url_path."""
        with recap_app.app_context():
            article = Article(url_path='https://example.com/post')
            assert repr(article) == '<Article https://example.com/post>'

    def test_get_article_by_url_path_returns_article(self, recap_app):
        """get_article_by_url_path finds a matching article for the user."""
        from recap import db
        with recap_app.app_context():
            user = User(username='artuser', email='artuser@example.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()

            article = Article(url_path='https://example.com/found', user_id=user.id)
            db.session.add(article)
            db.session.commit()

            result = Article.get_article_by_url_path('https://example.com/found', user.id)
            assert result is not None
            assert result.url_path == 'https://example.com/found'

    def test_get_article_by_url_path_returns_none_when_not_found(self, recap_app):
        """get_article_by_url_path returns None when no article matches."""
        from recap import db
        with recap_app.app_context():
            user = User(username='artuser2', email='artuser2@example.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()

            result = Article.get_article_by_url_path('https://example.com/missing', user.id)
            assert result is None

    def test_get_article_by_url_path_scoped_to_user(self, recap_app):
        """get_article_by_url_path does not return another user's article."""
        from recap import db
        with recap_app.app_context():
            u1 = User(username='owner1', email='owner1@example.com')
            u2 = User(username='owner2', email='owner2@example.com')
            u1.set_password('pass')
            u2.set_password('pass')
            db.session.add_all([u1, u2])
            db.session.commit()

            article = Article(url_path='https://example.com/private', user_id=u1.id)
            db.session.add(article)
            db.session.commit()

            result = Article.get_article_by_url_path('https://example.com/private', u2.id)
            assert result is None

    def test_get_sub_categories_json_returns_none_when_null(self, recap_app):
        """get_sub_categories_json returns None when sub_categories is unset."""
        with recap_app.app_context():
            article = Article(url_path='https://example.com/nosub')
            assert article.get_sub_categories_json() is None

    def test_get_sub_categories_json_parses_stored_json(self, recap_app):
        """get_sub_categories_json deserialises stored JSON correctly."""
        import json
        with recap_app.app_context():
            article = Article(
                url_path='https://example.com/withsub',
                sub_categories=json.dumps(['Backend', 'DevOps']),
            )
            result = article.get_sub_categories_json()
            assert result == ['Backend', 'DevOps']

    def test_get_key_topics_json_returns_none_when_null(self, recap_app):
        """get_key_topics_json returns None when key_topics is unset."""
        with recap_app.app_context():
            article = Article(url_path='https://example.com/notopics')
            assert article.get_key_topics_json() is None

    def test_get_key_topics_json_parses_stored_json(self, recap_app):
        """get_key_topics_json deserialises stored JSON correctly."""
        import json
        with recap_app.app_context():
            article = Article(
                url_path='https://example.com/withtopics',
                key_topics=json.dumps(['Python', 'Flask']),
            )
            result = article.get_key_topics_json()
            assert result == ['Python', 'Flask']


@pytest.mark.unit
@pytest.mark.recap
class TestUserGetArticles:
    def test_returns_articles_for_user(self, recap_app):
        """get_articles returns all articles belonging to the user."""
        from recap import db
        with recap_app.app_context():
            user = User(username='paguser', email='paguser@example.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()

            for i in range(3):
                db.session.add(Article(url_path=f'https://example.com/{i}', user_id=user.id))
            db.session.commit()

            paginator = user.get_articles(page=1, per_page=10)
            assert len(paginator.items) == 3

    def test_pagination_limits_per_page(self, recap_app):
        """get_articles respects per_page and exposes next page info."""
        from recap import db
        with recap_app.app_context():
            user = User(username='paguser2', email='paguser2@example.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()

            for i in range(5):
                db.session.add(Article(url_path=f'https://example.com/p/{i}', user_id=user.id))
            db.session.commit()

            paginator = user.get_articles(page=1, per_page=2)
            assert len(paginator.items) == 2
            assert paginator.has_next is True

    def test_category_filter(self, recap_app):
        """get_articles filters by category when provided."""
        from recap import db
        with recap_app.app_context():
            user = User(username='catuser', email='catuser@example.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()

            db.session.add(Article(url_path='https://a.com/1', user_id=user.id, category='Tech'))
            db.session.add(Article(url_path='https://a.com/2', user_id=user.id, category='Tech'))
            db.session.add(Article(url_path='https://a.com/3', user_id=user.id, category='Science'))
            db.session.commit()

            paginator = user.get_articles(page=1, per_page=10, category='Tech')
            assert len(paginator.items) == 2
            assert all(a.category == 'Tech' for a in paginator.items)

    def test_returns_newest_first(self, recap_app):
        """get_articles returns articles ordered by descending id."""
        from recap import db
        with recap_app.app_context():
            user = User(username='orderuser', email='orderuser@example.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()

            a1 = Article(url_path='https://first.com', user_id=user.id)
            a2 = Article(url_path='https://second.com', user_id=user.id)
            db.session.add_all([a1, a2])
            db.session.commit()

            paginator = user.get_articles(page=1, per_page=10)
            ids = [a.id for a in paginator.items]
            assert ids == sorted(ids, reverse=True)


@pytest.mark.unit
@pytest.mark.recap
class TestUserGetCategories:
    def test_returns_categories_with_counts(self, recap_app):
        """get_categories returns category groupings ordered by count descending."""
        from recap import db
        with recap_app.app_context():
            user = User(username='catcount', email='catcount@example.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()

            for _ in range(3):
                db.session.add(Article(url_path=f'https://t.com/{_}', user_id=user.id, category='Tech'))
            db.session.add(Article(url_path='https://s.com/1', user_id=user.id, category='Science'))
            db.session.commit()

            groupings = user.get_categories()
            categories = [g.category for g in groupings]
            assert 'Tech' in categories
            assert 'Science' in categories
            # Tech has more articles, should appear first
            assert categories[0] == 'Tech'

    def test_empty_when_user_has_no_articles(self, recap_app):
        """get_categories returns an empty list when the user has no articles."""
        from recap import db
        with recap_app.app_context():
            user = User(username='noarts', email='noarts@example.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()

            groupings = user.get_categories()
            assert groupings == []


@pytest.mark.unit
@pytest.mark.recap
class TestUserResetPasswordToken:
    def test_generates_a_token(self, recap_app):
        """get_reset_password_token returns a non-empty string."""
        from recap import db
        with recap_app.app_context():
            user = User(username='resetuser', email='resetuser@example.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()

            token = user.get_reset_password_token()
            assert token is not None
            assert len(token) > 0

    def test_verify_returns_correct_user(self, recap_app):
        """verify_reset_password_token returns the same user who generated the token."""
        from recap import db
        with recap_app.app_context():
            user = User(username='resetuser2', email='resetuser2@example.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()

            token = user.get_reset_password_token()
            found = User.verify_reset_password_token(token)
            assert found is not None
            assert found.id == user.id

    def test_verify_returns_none_for_invalid_token(self, recap_app):
        """verify_reset_password_token returns None for a garbage token."""
        with recap_app.app_context():
            result = User.verify_reset_password_token('not-a-valid-token')
            assert result is None

    def test_verify_returns_none_for_expired_token(self, recap_app):
        """verify_reset_password_token returns None for an already-expired token."""
        from recap import db
        with recap_app.app_context():
            user = User(username='resetuser3', email='resetuser3@example.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()

            # expires_in=-1 creates a token that is immediately expired
            token = user.get_reset_password_token(expires_in=-1)
            result = User.verify_reset_password_token(token)
            assert result is None 