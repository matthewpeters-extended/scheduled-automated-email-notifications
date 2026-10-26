import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.limiter import limiter
from app.main import app
from app.models import User
from app.security import hash_password

# The /login rate limit is for real-world abuse prevention; it would otherwise
# fire mid-suite since slowapi keys by client IP and the test client always
# looks like the same IP.
limiter.enabled = False

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session, tmp_path, monkeypatch):
    from app.config import settings

    # Each test gets its own outbox file so MockMailer writes don't leak
    # between tests or touch the real one in the project root.
    monkeypatch.setattr(settings, "mock_outbox_path", str(tmp_path / "outbox.jsonl"))

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def second_client(client):
    """A separate TestClient instance with its own cookie jar, for tests
    that need two independent logged-in sessions at once (e.g. checking
    that one user can't touch another user's data). Shares the same app and
    dependency overrides that `client` already set up."""
    with TestClient(app) as test_client:
        yield test_client


def _make_user(db_session, name, email, password):
    user = User(name=name, email=email, password=hash_password(password))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def login(client, email, password):
    response = client.post("/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


@pytest.fixture()
def user(db_session):
    return _make_user(db_session, "Nina", "nina@test-suite.dev", "nina12345")


@pytest.fixture()
def other_user(db_session):
    return _make_user(db_session, "Omar", "omar@test-suite.dev", "omar12345")
