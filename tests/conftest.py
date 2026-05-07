import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Set defaults before importing any app modules — config.py reads these at class definition time
os.environ.setdefault("RECAP_LogLevel", "DEBUG")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("RECAP_REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("RECAP_RQ_QUEUE", "test-queue")
os.environ.setdefault("ARTICLES_PER_PAGE", "10")
os.environ.setdefault("MAIL_SERVER", "localhost")
os.environ.setdefault("MAIL_PORT", "587")
os.environ.setdefault("MAIL_USE_TLS", "1")
os.environ.setdefault("MAIL_USERNAME", "test@test.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_DEFUALT_FROM", "test@test.com")
os.environ.setdefault("TASK_SERVER_NAME", "localhost")
os.environ.setdefault("RECAP_AI_API_URL", "http://localhost:8082/")
os.environ.setdefault("RECAP_POSTGRES_USER", "test")
os.environ.setdefault("RECAP_POSTGRES_PASSWORD", "test")
os.environ.setdefault("RECAP_POSTGRES_HOST", "localhost")
os.environ.setdefault("RECAP_POSTGRES_PORT", "5432")
os.environ.setdefault("RECAP_POSTGRES_DB", "test")

from aiapi import create_app as create_aiapi_app  # noqa: E402
from aiapi.config import AIAPIConfig  # noqa: E402
from recap import create_app as create_recap_app  # noqa: E402
from recap import db as recap_db  # noqa: E402
from recap.config import Config as RecapConfig  # noqa: E402


class TestConfig:
    """Test configuration that overrides the base config."""

    TESTING = True
    WTF_CSRF_ENABLED = False
    RECAP_REDIS_URL = "redis://localhost:6379/1"  # Use a different Redis DB for testing

    # Always use SQLite for tests to avoid affecting the development database
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def recap_app_session():
    """Create a recap app instance for the test session."""
    app = create_recap_app(env="test")

    # Apply all test configuration
    test_config = TestConfig()
    app.config["SQLALCHEMY_DATABASE_URI"] = test_config.SQLALCHEMY_DATABASE_URI
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # Explicitly disable CSRF for tests

    print(f"\nTEST DATABASE URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # Create the database
    with app.app_context():
        # Print SQLAlchemy engine details
        print(f"SQLAlchemy Engine Type: {recap_db.engine}")
        print(f"SQLAlchemy Engine URL: {recap_db.engine.url}")
        print(f"Is SQLite Memory DB: {str(recap_db.engine.url) == 'sqlite:///:memory:'}")
        print(f"Connection Info: {recap_db.engine.pool.status()}")

        recap_db.create_all()

    yield app

    # Clean up at end of session
    with app.app_context():
        recap_db.session.remove()
        recap_db.drop_all()


@pytest.fixture
def recap_app(recap_app_session):
    """Provide the recap app and handle per-test cleanup."""
    app = recap_app_session

    # Setup: create fresh tables for each test
    with app.app_context():
        # Verify connection before each test
        print("\nTest Connection Info:")
        print(f"Current Engine: {recap_db.engine}")
        print(f"Current Database URL: {recap_db.engine.url}")

        recap_db.session.remove()
        recap_db.drop_all()
        recap_db.create_all()

    yield app

    # Cleanup: remove all data after each test
    with app.app_context():
        recap_db.session.remove()
        recap_db.drop_all()


@pytest.fixture
def recap_client(recap_app):
    """A test client for the recap app."""
    return recap_app.test_client()


@pytest.fixture
def recap_runner(recap_app):
    """A test runner for the recap app's Click commands."""
    return recap_app.test_cli_runner()


@pytest.fixture
def test_user(recap_app):
    """Create a test user and clean it up after the test."""
    from recap.models import User

    with recap_app.app_context():
        user = User(username="testuser", email="test@example.com")
        user.set_password("testpass123")
        recap_db.session.add(user)
        recap_db.session.commit()

        yield user

        # Cleanup happens automatically via recap_app fixture


@pytest.fixture
def authenticated_client(recap_client, test_user):
    """Create an authenticated client with the test user."""
    recap_client.post("/auth/login", data={"username": test_user.username, "password": "testpass123"})
    return recap_client


@pytest.fixture
def seeded_user(recap_app):
    """
    A test user pre-loaded with 52 classified articles across 10 categories.

    Use this (instead of test_user) whenever a test needs realistic multi-category
    article data — category filtering, taxonomy work, pagination, UX assertions, etc.

    Yields the User object inside the app context so callers can query the DB directly.
    """
    from datetime import datetime

    from recap.models import Article, User
    from tests.seed_data import SEED_ARTICLES

    with recap_app.app_context():
        user = User(username="seeduser", email="seeduser@example.com")
        user.set_password("seedpass123")
        recap_db.session.add(user)
        recap_db.session.flush()  # get user.id before inserting articles

        for data in SEED_ARTICLES:
            article = Article(
                user_id=user.id,
                url_path=data["url_path"],
                title=data.get("title"),
                summary=data.get("summary"),
                author_name=data.get("author_name"),
                category=data.get("category"),
                key_topics=data.get("key_topics"),
                sub_categories=data.get("sub_categories"),
                created=datetime.fromisoformat(data["created"]),
                classified=datetime.fromisoformat(data["classified"]),
            )
            recap_db.session.add(article)

        recap_db.session.commit()
        yield user
        # cleanup handled by recap_app fixture (drop_all after each test)


@pytest.fixture
def seeded_articles(seeded_user, recap_app):
    """
    All 52 Article objects belonging to seeded_user, ordered by category then created.

    Convenience wrapper — most tests need the articles themselves, not the user.
    """
    import sqlalchemy as sa

    from recap.models import Article

    with recap_app.app_context():
        articles = recap_db.session.scalars(
            sa.select(Article).where(Article.user_id == seeded_user.id).order_by(Article.category, Article.created)
        ).all()
        yield articles


@pytest.fixture
def seeded_authenticated_client(recap_app, seeded_user):
    """
    A test client pre-logged-in as the seeded user (seeduser / seedpass123).

    Use alongside seeded_user when a test needs both realistic article data
    and an authenticated HTTP session (e.g. taxonomy, profile routes).
    """
    client = recap_app.test_client()
    client.post(
        "/auth/login",
        data={
            "username": "seeduser",
            "password": "seedpass123",
        },
    )
    return client


@pytest.fixture
def aiapi_app():
    """Create and configure a new aiapi app instance for each test."""

    class TestConfig:
        TESTING = True
        AI_API_OPENAI = "test-api-key"
        AI_API_LogLevel = "DEBUG"
        AI_API_SECRET_KEY = "test-secret-key"

    app = create_aiapi_app()
    app.config.update(
        {
            "TESTING": True,
            "AI_API_OPENAI": "test-api-key",
            "AI_API_LogLevel": "DEBUG",
            "AI_API_SECRET_KEY": "test-secret-key",
        }
    )
    return app


@pytest.fixture
def aiapi_client(aiapi_app):
    """A test client for the aiapi app."""
    return aiapi_app.test_client()


@pytest.fixture
def auth_headers():
    """Headers with test authentication."""
    return {"Authorization": "Bearer test-token"}
