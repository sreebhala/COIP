"""
Post #1.4 fix (applied per mentor direction after the Post #1.3 review):
tests now run against a completely separate, in-memory SQLite database and
never touch the real dev/demo database (coip.db). Previously, tests shared
the same database file as the running app, and pytest's
Base.metadata.drop_all() call would wipe all seeded demo data as a side
effect of running the test suite.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app import models  # noqa: F401
from app.core.database import Base, get_db
from app.main import app
from app.data.seed import seed as seed_demo_data

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


def _override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=test_engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def seed():
    """Seed the isolated test database (never the real dev/demo database).

    Usage in a test: `def test_x(client, seed): seed()`.
    """
    db = TestSessionLocal()
    try:
        seed_demo_data(db_session=db)
    finally:
        db.close()
    yield
