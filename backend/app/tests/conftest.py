"""Integration tests use a separate PostgreSQL database and rolled-back transactions."""

import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

TEST_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_URL or not TEST_URL.rsplit("/", 1)[-1].startswith("ars_rms_test"):
    raise RuntimeError("Set TEST_DATABASE_URL to a dedicated ars_rms_test* PostgreSQL database")
os.environ["DATABASE_URL"] = TEST_URL
os.environ["ENVIRONMENT"] = "testing"
os.environ.setdefault("SECRET_KEY", "integration-test-secret-only-32-characters")

from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.identity import User  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture(scope="session")
def test_engine():
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(TEST_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def db(test_engine):
    with test_engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        seed(session, development=True)
        admin = session.scalar(select(User).where(User.email == "admin@example.org"))
        admin.force_password_change = False
        session.commit()
        yield session
        session.close()
        transaction.rollback()


@pytest.fixture
def client(db):
    def override():
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def logged_in(client):
    result = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.org", "password": "ChangeMe!2026"}
    )
    assert result.status_code == 200, result.text
    client.headers["X-CSRF-Token"] = client.cookies.get("csrf_token")
    return client


@pytest.fixture
def clinical_client(client, db):
    from app.core.security import password_hasher
    from app.models.identity import Permission
    from app.seed_care import PERMISSIONS

    admin = db.scalar(select(User).where(User.email == "admin@example.org"))
    user = User(
        email="care@example.org",
        full_name="Synthetic Care Professional",
        password_hash=password_hasher.hash("SyntheticCare!2026"),
        facility_id=admin.facility_id,
        force_password_change=False,
        permissions=list(db.scalars(select(Permission).where(Permission.code.in_(PERMISSIONS)))),
    )
    db.add(user)
    db.commit()
    result = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "SyntheticCare!2026"}
    )
    assert result.status_code == 200, result.text
    client.headers["X-CSRF-Token"] = client.cookies.get("csrf_token")
    return client
