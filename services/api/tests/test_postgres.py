"""Tests that need a real PostgreSQL with pgvector. They start a throwaway server through the `pgserver` package;
they are SKIPPED (not passed) if it is unavailable. Run: pytest -m pg"""
import itertools
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401
from app.api.v1 import auth as auth_mod
from app.api.v1 import data as data_mod
from app.db.base import Base
from app.domain.vectors import cosine_distance
from app.db.session import get_db
from app.ingestion import moon_catalogue as mc
from app.ingestion.registry import MOON_CATALOGUE_SLUG, seed_sources
from app.main import app
from app.models import Artifact, KnowledgeChunk, KnowledgeDocument, User
from app.models.nasa import DataSource
from tests.conftest import TEXT
from tests.pg_harness import pg_url

pytestmark = pytest.mark.pg
API_DIR = Path(__file__).resolve().parent.parent
_n = itertools.count(1)


def alembic(url: str, *args: str) -> subprocess.CompletedProcess:
    r = subprocess.run([sys.executable, "-m", "alembic", *args], cwd=API_DIR, env={**os.environ, "ASTERA_MIGRATION_URL": url}, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-1500:]
    return r


@pytest.fixture()
def url():
    u = pg_url(f"t{next(_n)}")
    if u is None:
        pytest.skip("pgserver not installed")
    return u


@pytest.fixture()
def engine(url):
    e = create_engine(url)
    yield e
    e.dispose()


def tables(e):
    return set(sa.inspect(e).get_table_names())


def test_empty_database_to_head_creates_schema_and_pgvector(url, engine):
    alembic(url, "upgrade", "head")
    t = tables(engine)
    assert {"users", "data_sources", "catalogue_records", "ingestion_jobs", "verification_events", "missions", "artifacts",
            "artifact_locations", "artifact_sources", "artifact_images", "knowledge_chunks", "alembic_version"} <= t
    with engine.connect() as c:
        assert c.execute(text("select extversion from pg_extension where extname='vector'")).scalar()
        # the embedding column really is a pgvector column, not JSON
        assert c.execute(text("select udt_name from information_schema.columns where table_name='knowledge_chunks' and column_name='embedding'")).scalar() == "vector"
    heads = alembic(url, "heads").stdout
    assert len(re.findall(r"\(head\)", heads)) == 1


def test_no_schema_drift_between_models_and_migrations(url, engine):
    alembic(url, "upgrade", "head")
    with engine.connect() as c:
        diff = compare_metadata(MigrationContext.configure(c, opts={"compare_type": True}), Base.metadata)
    assert diff == [], f"models differ from migrations: {diff}"


def test_migrations_do_not_use_create_all():
    src = "".join(p.read_text() for p in (API_DIR / "alembic/versions").glob("*.py"))
    assert "create_all" not in src and "metadata.create" not in src


def test_downgrade_to_base_and_reupgrade(url, engine):
    alembic(url, "upgrade", "head")
    alembic(url, "downgrade", "base")
    assert tables(engine) - {"alembic_version"} == set()   # downgrade is destructive: documented in POSTGRES_SETUP.md
    alembic(url, "upgrade", "head")
    assert "catalogue_records" in tables(engine)


def test_upgrade_on_populated_database_preserves_data(url, engine):
    alembic(url, "upgrade", "head")
    S = sessionmaker(bind=engine)
    with S() as db:
        seed_sources(db)
        db.add(User(email="a@b.c", display_name="A", password_hash="x")); db.commit()
    alembic(url, "upgrade", "head")  # idempotent at head
    with S() as db:
        assert db.query(DataSource).count() == 20 and db.query(User).one().role == "user"


def test_check_constraints_and_pgvector_on_postgres(url, engine):
    alembic(url, "upgrade", "head")
    S = sessionmaker(bind=engine)
    with S() as db:
        seed_sources(db)
        s = db.query(DataSource).filter_by(slug="lroc-images").one()
        s.challenge_listing_status = "listed_verified"
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        doc = KnowledgeDocument(title="d"); db.add(doc); db.flush()
        vecs = [[1.0] + [0.0] * 383, [0.0, 1.0] + [0.0] * 382]
        for i, v in enumerate(vecs):
            db.add(KnowledgeChunk(document_id=doc.id, position=i, text=f"c{i}", embedding=v))
        db.commit()
        nearest = db.scalars(select(KnowledgeChunk).order_by(cosine_distance([0.9, 0.1] + [0.0] * 382)).limit(1)).one()
        assert nearest.text == "c0"


@pytest.fixture()
def pg_client(url, engine):
    alembic(url, "upgrade", "head")
    S = sessionmaker(bind=engine, expire_on_commit=False)
    db = S(); seed_sources(db)
    def override():
        d = S()
        try: yield d
        finally: d.close()
    app.dependency_overrides[get_db] = override
    auth_mod._hits.clear(); data_mod.ingest_limiter.hits.clear()
    yield db, TestClient(app)
    app.dependency_overrides.clear(); db.close()


def test_ingestion_review_promotion_and_api_filters_on_postgres(pg_client):
    db, client = pg_client
    src = db.query(DataSource).filter_by(slug=MOON_CATALOGUE_SLUG).one()
    job = mc.load(db, src, TEXT, document_sha256="d" * 64, source_url=src.official_url)
    assert job.status == "succeeded" and mc.load(db, src, TEXT, document_sha256="d" * 64).records_created == 0
    tok = client.post("/api/v1/auth/register", json={"email": "r@x.com", "display_name": "R", "password": "orbit-1234"}).json()["access_token"]
    db.query(User).update({"role": "reviewer"}); db.commit()
    h = {"Authorization": f"Bearer {tok}"}
    q = client.get("/api/v1/verification/queue", headers=h, params={"flag": "layout_inferred_association"}).json()   # JSON-as-text LIKE on PG
    assert q["total"] == 2
    rid = next(i["id"] for i in client.get("/api/v1/catalogue-records", params={"q": "Central Station", "section": "Apollo 15"}).json()["items"])
    r = client.post(f"/api/v1/verification/records/{rid}/review", headers=h, json={"action": "approve", "note": "checked", "promote": {}})
    assert r.status_code == 200
    arts = client.get("/api/v1/artifacts", params={"destination": "moon", "has_location": True, "sort": "-name"}).json()
    assert arts["total"] == 1 and arts["items"][0]["mission"]["name"] == "Apollo 15"
    assert db.query(Artifact).count() == 1
