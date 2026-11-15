from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.api.v1 import auth as auth_mod
from app.api.v1 import data as data_mod
from app.db.base import Base
from app.db.session import get_db
from app.ingestion.registry import MOON_CATALOGUE_SLUG, seed_sources
from app.main import app
from app.models import User
from app.models.nasa import DataSource

FIXTURE = Path(__file__).parent.parent / "fixtures/moon_catalogue_sitelevel.txt"
TEXT = FIXTURE.read_text()


@pytest.fixture()
def env():
    """SQLite-backed app: yields (session, client). Separate sessions per request, shared in-memory DB."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    S = sessionmaker(bind=engine, expire_on_commit=False)
    db = S(); seed_sources(db)

    def override():
        d = S()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = override
    auth_mod._hits.clear(); data_mod.ingest_limiter.hits.clear()
    yield db, TestClient(app)
    app.dependency_overrides.clear(); db.close()


@pytest.fixture()
def source(env):
    return env[0].query(DataSource).filter_by(slug=MOON_CATALOGUE_SLUG).one()


def auth_header(env, email: str, role: str = "user") -> dict:
    db, client = env
    reg = client.post("/api/v1/auth/register", json={"email": email, "display_name": "T", "password": "orbit-1234"})
    if reg.status_code == 409:  # already registered in this test: log in instead
        reg = client.post("/api/v1/auth/login", json={"email": email, "password": "orbit-1234"})
    tok = reg.json()["access_token"]
    if role != "user":
        db.query(User).filter_by(email=email).update({"role": role}); db.commit()
    return {"Authorization": f"Bearer {tok}"}
