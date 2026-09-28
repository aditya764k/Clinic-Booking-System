"""
Pytest configuration and shared fixtures for the Clinic Booking System test suite.

Test database: SQLite in-memory — no Docker or Postgres required.
The ``authenticated_client(role=...)`` fixture is the canonical way for
ANY future test module to get a TestClient with cookies already set for
a user of the requested role.

Import from this file in any future test module:
    from tests.conftest import authenticated_client  # (available as fixture automatically)
"""
import os
import pytest
from typing import Generator

# ── Point to a test-only SQLite DB before anything imports app modules ────────
# These must be set BEFORE any app module is imported.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-ci-only"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRE_MINUTES"] = "60"
os.environ["JWT_REFRESH_EXPIRE_DAYS"] = "7"
os.environ["GOOGLE_CLIENT_ID"] = "test-google-client-id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test-google-client-secret"
os.environ["COOKIE_SECURE"] = "false"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:3000"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["GEMINI_MODEL"] = "gemini-1.5-flash"
os.environ["GEMINI_TIMEOUT_SECONDS"] = "12"

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db

# ── In-memory SQLite engine ───────────────────────────────────────────────────
# StaticPool ensures the same in-memory DB is used across all connections.
# connect_args check_same_thread=False is required for SQLite + multiple threads.
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Enable foreign key enforcement in SQLite (off by default)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Create all tables before each test, drop after."""
    # Import all models so Base.metadata is populated
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Yield a database session for direct DB inspection in tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(setup_database) -> Generator[TestClient, None, None]:
    """TestClient with the get_db dependency overridden to use SQLite."""

    def _override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def authenticated_client(client: TestClient):
    """Factory fixture that returns a TestClient with auth cookies set.

    Usage in tests::

        def test_something(authenticated_client):
            ac = authenticated_client(role="doctor")
            response = ac.get("/some/protected/endpoint")
            assert response.status_code == 200

    Future modules can import this fixture from ``tests.conftest`` automatically
    (pytest discovers conftest.py fixtures without an explicit import).

    The fixture:
    1. Registers a user with the given role using a deterministic email.
    2. The registration auto-logins (per our design), so cookies are set.
    3. Returns the same ``client`` instance with cookies attached.
    """
    _counter = {"n": 0}

    def _factory(role: str = "patient") -> TestClient:
        _counter["n"] += 1
        n = _counter["n"]
        email = f"testuser_{role}_{n}@clinic-test.com"
        password = "Str0ngPass!"
        full_name = f"Test {role.capitalize()} {n}"

        resp = client.post(
            "/auth/register",
            json={"email": email, "password": password, "role": role, "full_name": full_name},
        )
        assert resp.status_code == 201, f"authenticated_client factory failed: {resp.text}"
        # Cookies are set on the client jar by TestClient automatically
        return client

    return _factory
