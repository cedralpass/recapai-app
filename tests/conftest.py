import os
import tempfile
import pytest
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from recap import create_app as create_recap_app
from aiapi import create_app as create_aiapi_app
from recap import db as recap_db
from recap.config import Config as RecapConfig
from aiapi.config import AIAPIConfig

class TestConfig:
    """Test configuration that overrides the base config."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    RECAP_REDIS_URL = 'redis://localhost:6379/1'  # Use a different Redis DB for testing
    
    # Always use SQLite for tests to avoid affecting the development database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

@pytest.fixture(scope='session')
def recap_app_session():
    """Create a recap app instance for the test session."""
    app = create_recap_app(env='test')
    
    # Apply all test configuration
    test_config = TestConfig()
    app.config['SQLALCHEMY_DATABASE_URI'] = test_config.SQLALCHEMY_DATABASE_URI
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Explicitly disable CSRF for tests
    
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
        print(f"\nTest Connection Info:")
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
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        recap_db.session.add(user)
        recap_db.session.commit()
        
        yield user
        
        # Cleanup happens automatically via recap_app fixture

@pytest.fixture
def authenticated_client(recap_client, test_user):
    """Create an authenticated client with the test user."""
    recap_client.post('/auth/login', data={
        'username': test_user.username,
        'password': 'testpass123'
    })
    return recap_client

@pytest.fixture
def aiapi_app():
    """Create and configure a new aiapi app instance for each test."""
    class TestConfig:
        TESTING = True
        AI_API_OPENAI = "test-api-key"
        AI_API_LogLevel = "DEBUG"
        AI_API_SECRET_KEY = "test-secret-key"
        
    app = create_aiapi_app()
    app.config.update({
        'TESTING': True,
        'AI_API_OPENAI': 'test-api-key',
        'AI_API_LogLevel': 'DEBUG',
        'AI_API_SECRET_KEY': 'test-secret-key'
    })
    return app

@pytest.fixture
def aiapi_client(aiapi_app):
    """A test client for the aiapi app."""
    return aiapi_app.test_client()

@pytest.fixture
def auth_headers():
    """Headers with test authentication."""
    return {'Authorization': 'Bearer test-token'}
