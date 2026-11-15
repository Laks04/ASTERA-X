import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import auth as auth_mod
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app import models  # noqa: F401


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    auth_mod._hits.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_register_login_me(client):
    body = {"email": "a@b.com", "display_name": "Ada", "password": "orbit-1234"}
    tok = client.post("/api/v1/auth/register", json=body).json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200 and me.json()["display_name"] == "Ada"
    assert client.post("/api/v1/auth/register", json=body).status_code == 409
    bad = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "wrong-pass"})
    assert bad.status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "orbit-1234"}).status_code == 200


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401
