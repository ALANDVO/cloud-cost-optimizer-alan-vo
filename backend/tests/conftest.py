# Pytest configuration and fixtures
import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Use a file-based SQLite database for testing to share across connections
TEST_DB_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ["JWT_SECRET"] = "test-secret"
    os.environ["DEMO_MODE"] = "true"
    os.environ["DATABASE_URL"] = TEST_DB_URL
    os.environ["GCP_PROJECT_ID"] = "test-project"
    os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription"
    yield
    # Cleanup
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    from backend.app.models.analysis import Base as AnalysisBase
    from backend.app.models.user import Base as UserBase
    AnalysisBase.metadata.create_all(bind=engine)
    UserBase.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_db_engine):
    """Create a new database session for each test."""
    SessionLocal = sessionmaker(bind=test_db_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(test_db_engine, db_session):
    """Create test client with overridden database dependency."""
    from backend.app.main import create_app
    from backend.app.core.database import get_db_session
    import backend.app.core.database as db_module

    # Override the engine in the database module to use our test engine
    db_module.engine = test_db_engine
    db_module.SessionLocal = sessionmaker(bind=test_db_engine, autocommit=False, autoflush=False)

    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db_session] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def demo_user(db_session):
    """Create a demo user for testing."""
    from backend.app.models.user import User
    user = User(
        sub="demo-user",
        email="demo@localhost",
        name="Demo User",
        roles="viewer,operator,admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user