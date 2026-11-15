import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.ingestion import moon_catalogue as mc
from app.models import Artifact, ArtifactLocation, Mission
from app.models.nasa import CatalogueRecord, DataSource, VerificationEvent
from tests.conftest import TEXT, auth_header

V = "/api/v1"


@pytest.fixture()
def loaded(env, source):
    db, client = env
    mc.load(db, source, TEXT, document_sha256="c" * 64, source_url=source.official_url, document_title="Catalogue")
    return db, client


def rec_id(db, name, section=None):
    q = select(CatalogueRecord.id).where(CatalogueRecord.object_name == name)
    if section: q = q.where(CatalogueRecord.section == section)
    return db.scalars(q).first()


def review(client, h, rid, **body):
    return client.post(f"{V}/verification/records/{rid}/review", json=body, headers=h)


# ---------- authentication and permissions ----------

def test_verification_endpoints_require_authentication(loaded):
    db, client = loaded
    rid = rec_id(db, "Ranger 9")
    assert client.get(f"{V}/verification/queue").status_code == 401
    assert client.get(f"{V}/verification/records/{rid}").status_code == 401
    assert client.post(f"{V}/verification/records/{rid}/review", json={"action": "approve", "note": "ok"}).status_code == 401


def test_plain_users_are_forbidden_and_reviewers_allowed(loaded):
    db, client = loaded
    user, rev = auth_header(loaded, "u@x.com"), auth_header(loaded, "r@x.com", "reviewer")
    rid = rec_id(db, "Surveyor 4")
    assert client.get(f"{V}/verification/queue", headers=user).status_code == 403
    assert review(client, user, rid, action="approve", note="fine").status_code == 403
    assert client.get(f"{V}/verification/queue", headers=rev).status_code == 200


def test_ingestion_start_is_admin_only_and_registry_bound(loaded):
    db, client = loaded
    rev, adm = auth_header(loaded, "r@x.com", "reviewer"), auth_header(loaded, "a@x.com", "admin")
    body = {"source_slug": "nasa-history-moon-catalogue"}
    assert client.post(f"{V}/ingestion/jobs", json=body).status_code == 401
    assert client.post(f"{V}/ingestion/jobs", json=body, headers=rev).status_code == 403
    assert client.post(f"{V}/ingestion/jobs", json={"source_slug": "lroc-images"}, headers=adm).status_code == 422  # no adapter
    assert client.post(f"{V}/ingestion/jobs", json={"source_slug": "nope"}, headers=adm).status_code == 404
    # extra fields such as a caller-supplied URL are ignored by the schema and cannot redirect the download
    r = client.post(f"{V}/ingestion/jobs", json={**body, "url": "https://evil.example/x.pdf"}, headers=adm)
    assert r.status_code == 201 and r.json()["status"] in ("failed", "succeeded", "partial")


def test_ingestion_rate_limited(loaded):
    _, client = loaded
    adm = auth_header(loaded, "a@x.com", "admin")
    codes = [client.post(f"{V}/ingestion/jobs", json={"source_slug": "lroc-images"}, headers=adm).status_code for _ in range(7)]
    assert 429 in codes


# ---------- verification workflow ----------

def test_review_preserves_printed_values_and_writes_audit_trail(loaded):
    db, client = loaded
    h = auth_header(loaded, "r@x.com", "reviewer"); rid = rec_id(db, "Surveyor 3")
    before = client.get(f"{V}/catalogue-records/{rid}").json()
    r = review(client, h, rid, action="approve", note="Checked page 1 of the PDF", normalized_object_name="Surveyor 3 lander")
    assert r.status_code == 200
    d = r.json()
    assert d["review_status"] == "verified" and d["reviewed_by_id"] and d["reviewed_at"] and d["normalized_object_name"] == "Surveyor 3 lander"
    for k in ("raw_line", "raw_location", "latitude_deg_n", "longitude_deg_e", "object_name", "flags"):
        assert d[k] == before[k]
    ev = d["events"]
    assert len(ev) == 1 and ev[0]["action"] == "approve" and ev[0]["before"]["review_status"] == "extracted" and ev[0]["after"]["review_status"] == "verified"
    assert d["source_page_url"].endswith("#page=1")


def test_queue_lists_flagged_records_and_filters_by_flag(loaded):
    db, client = loaded
    h = auth_header(loaded, "r@x.com", "reviewer")
    q = client.get(f"{V}/verification/queue", headers=h, params={"flag": "layout_inferred_association"}).json()
    assert q["total"] == 2 and {i["object_name"] for i in q["items"]} == {"Luna 13", "Luna 20 descent stage"}
    q2 = client.get(f"{V}/verification/queue", headers=h, params={"flag": "invalid_coordinate_needs_review"}).json()
    assert [i["object_name"] for i in q2["items"]] == ["Ranger 9"]


def test_invalid_coordinates_cannot_be_approved_without_a_correction_or_explicit_discard(loaded):
    db, client = loaded
    h = auth_header(loaded, "r@x.com", "reviewer"); rid = rec_id(db, "Ranger 9")
    assert review(client, h, rid, action="approve", note="looks fine").status_code == 409
    assert review(client, h, rid, action="approve", note="x", normalized_latitude=12.0).status_code == 422  # pair required
    assert review(client, h, rid, action="approve", note="x", normalized_latitude=100, normalized_longitude=1).status_code == 422
    ok = review(client, h, rid, action="approve", note="Corrected after checking the page image", normalized_latitude=12.828, normalized_longitude=-2.387)
    d = ok.json()
    assert ok.status_code == 200 and d["normalized_latitude"] == 12.828 and d["latitude_deg_n"] == 112.828 and d["location_status"] == "invalid_coordinate_needs_review"
    rid2 = rec_id(db, "Surveyor 2")  # discard path on another record
    assert review(client, h, rid, action="reject", note="changed my mind", discard_location=True).json()["normalized_latitude"] is None
    assert [e["action"] for e in client.get(f"{V}/verification/records/{rid}", headers=h).json()["events"]] == ["approve", "reject"]


def test_reject_conflict_and_return_to_review_transitions(loaded):
    db, client = loaded
    h = auth_header(loaded, "r@x.com", "reviewer"); rid = rec_id(db, "Luna 13")
    assert review(client, h, rid, action="mark_conflicting", note="PDF page shows a different order").json()["review_status"] == "conflicting_evidence"
    assert review(client, h, rid, action="return_to_review", note="asking a colleague").json()["review_status"] == "needs_review"
    assert review(client, h, rid, action="reject", note="not attributable").json()["review_status"] == "rejected"
    assert review(client, h, rid, action="approve", note="").status_code == 422  # note is mandatory
    assert review(client, h, rid, action="verified", note="not an action").status_code == 422


def test_no_unauthenticated_path_can_mark_records_verified(loaded):
    db, client = loaded
    assert db.scalar(select(func.count()).select_from(CatalogueRecord).where(CatalogueRecord.review_status == "verified")) == 0
    assert db.scalar(select(func.count()).select_from(VerificationEvent)) == 0


# ---------- promotion to artifacts, archive API, relationships, provenance ----------

def promote_one(loaded, name="Central Station", section="Apollo 14", **extra):
    db, client = loaded
    h = auth_header(loaded, "r@x.com", "reviewer")
    return h, review(client, h, rec_id(db, name, section), action="approve", note="Verified against catalogue page", promote=extra or {})


def test_promotion_creates_mission_artifact_location_source_with_provenance(loaded):
    db, client = loaded
    h, r = promote_one(loaded)
    assert r.status_code == 200 and r.json()["artifact_id"]
    a = client.get(f"{V}/artifacts/{r.json()['artifact_id']}").json()
    assert a["name"] == "Central Station" and a["mission"]["name"] == "Apollo 14" and a["destination"]["slug"] == "moon"
    assert a["hardware_category"] == "central_station" and a["lifecycle_status"] == "unknown_or_unverified"  # never assumed
    assert a["left_behind_reason"] is None
    assert a["verification_badge"] == "human_reviewed_single_source"
    loc = a["location"]
    assert (loc["latitude"], loc["longitude"]) == (-3.64398, -17.47748) and loc["printed_latitude"] == -3.64398
    assert loc["coordinate_system"] == "not stated in source" and loc["original_printed"].startswith("-3.64398")
    (s,) = a["sources"]
    assert s["source_page"] == 6 and s["source_url"].endswith("#page=6") and "Central Station" in s["evidence_description"] and s["evidence_type"] == "catalogue_entry"
    assert a["mission"]["verification_status"] == "unverified"  # mission-level facts are not established by this catalogue
    assert client.get(f"{V}/artifacts/{a['id']}/location").json()["latitude"] == -3.64398
    assert len(client.get(f"{V}/artifacts/{a['id']}/sources").json()) == 1 and client.get(f"{V}/artifacts/{a['id']}/images").json() == []


def test_promotion_twice_conflicts_and_failed_promotion_rolls_back_review(loaded):
    db, client = loaded
    h, r = promote_one(loaded)
    rid = rec_id(db, "Central Station", "Apollo 14")
    again = review(client, h, rid, action="approve", note="again", promote={})
    assert again.status_code == 409
    bad = review(client, h, rec_id(db, "Surveyor 5"), action="approve", note="x", promote={"lifecycle_status": "abandoned"})
    assert bad.status_code == 422
    assert client.get(f"{V}/catalogue-records/{rec_id(db, 'Surveyor 5')}").json()["review_status"] == "extracted"
    bad2 = review(client, h, rec_id(db, "Surveyor 5"), action="approve", note="x", promote={"left_behind_reason": "because"})
    assert bad2.status_code == 422  # reason with unknown status
    assert db.scalar(select(func.count()).select_from(VerificationEvent)) == 1


def test_lifecycle_only_set_from_source_text_or_reviewer(loaded):
    db, client = loaded
    h, r = promote_one(loaded, "Lunar Orbiter 4", "U.S. Material (Non-Apollo)")
    a = client.get(f"{V}/artifacts/{r.json()['artifact_id']}").json()
    assert a["lifecycle_status"] == "crashed_or_impacted" and a["location"] is None  # catalogue prints "Crashed", no coordinates
    h2, r2 = promote_one(loaded, "Surveyor 1", "U.S. Material (Non-Apollo)", lifecycle_status="mission_completed_hardware_left_behind", left_behind_reason="Documented in the cited catalogue entry")
    assert r2.json()["artifact_id"]


def test_archive_filters_search_sorting_and_pagination(loaded):
    db, client = loaded
    h = auth_header(loaded, "r@x.com", "reviewer")
    for name, sec in [("Central Station", "Apollo 12"), ("Central Station", "Apollo 14"), ("Central Station", "Apollo 15"), ("LM Descent Stage (plaque attached)", "Apollo 12")]:
        assert review(client, h, rec_id(db, name, sec), action="approve", note="checked", promote={}).status_code == 200
    p = client.get(f"{V}/artifacts", params={"limit": 2}).json()
    assert p["total"] == 4 and len(p["items"]) == 2 and p["limit"] == 2
    assert len(client.get(f"{V}/artifacts", params={"limit": 2, "offset": 2}).json()["items"]) == 2
    assert client.get(f"{V}/artifacts", params={"destination": "moon"}).json()["total"] == 4
    assert client.get(f"{V}/artifacts", params={"destination": "mars"}).json()["total"] == 0
    assert client.get(f"{V}/artifacts", params={"hardware_category": "central_station"}).json()["total"] == 3
    assert client.get(f"{V}/artifacts", params={"q": "descent"}).json()["total"] == 1
    assert client.get(f"{V}/artifacts", params={"lifecycle_status": "crashed_or_impacted"}).json()["total"] == 0
    assert client.get(f"{V}/artifacts", params={"has_location": True}).json()["total"] == 4
    names = [i["mission"]["name"] for i in client.get(f"{V}/artifacts", params={"sort": "-name", "limit": 100}).json()["items"]]
    assert len(names) == 4
    assert client.get(f"{V}/artifacts", params={"sort": "bogus"}).status_code == 422
    assert client.get(f"{V}/artifacts", params={"limit": 1000}).status_code == 422
    m = client.get(f"{V}/missions", params={"destination": "moon"}).json()
    assert m["total"] == 3 and {i["name"]: i["artifact_count"] for i in m["items"]} == {"Apollo 12": 2, "Apollo 14": 1, "Apollo 15": 1}
    mid = next(i["id"] for i in m["items"] if i["name"] == "Apollo 12")
    assert client.get(f"{V}/missions/{mid}").json()["artifact_count"] == 2
    assert {a["name"] for a in client.get(f"{V}/missions/{mid}/artifacts").json()["items"]} == {"Central Station", "LM Descent Stage (plaque attached)"}
    assert client.get(f"{V}/missions/9999").status_code == 404 and client.get(f"{V}/artifacts/9999").status_code == 404


def test_artifact_without_location_returns_404_for_location(loaded):
    db, client = loaded
    h, r = promote_one(loaded, "Surveyor 4", "U.S. Material (Non-Apollo)")
    aid = r.json()["artifact_id"]
    assert client.get(f"{V}/artifacts/{aid}/location").status_code == 404
    assert client.get(f"{V}/artifacts/{aid}").json()["location"] is None


# ---------- source registry ----------

def test_registry_records_the_owner_supplied_official_challenge_listing(loaded):
    db, client = loaded
    items = client.get(f"{V}/sources").json()["items"]
    assert len(items) == 20
    assert sum(s["challenge_listing_status"] == "listed_verified" for s in items) == 14
    assert all(s["review_notes"] for s in items)
    moon = next(s for s in items if s["slug"] == "nasa-history-moon-catalogue")
    assert client.get(f"{V}/sources/{moon['id']}").json()["official_url"].endswith("moon.pdf")
    assert client.get(f"{V}/sources/{moon['id']}/jobs").json()["total"] == 1
    assert client.get(f"{V}/sources", params={"challenge_listing_status": "listed_verified"}).json()["total"] == 14
    assert moon["challenge_listing_status"] == "not_listed_verified"
    assert client.get(f"{V}/sources/999").status_code == 404


def test_database_refuses_verified_listing_without_a_check_date(env):
    db, _ = env
    s = db.query(DataSource).filter_by(slug="lroc-images").one()
    s.challenge_listing_status = "listed_verified"
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    s.challenge_listing_status = "bogus"
    with pytest.raises(IntegrityError):
        db.commit()


def test_database_constraints_on_artifacts(loaded):
    db, _ = loaded
    h, r = promote_one(loaded)
    a = db.get(Artifact, r.json()["artifact_id"])
    db.add(Artifact(mission_id=a.mission_id, slug=a.slug, name="dup")); 
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    a = db.get(Artifact, a.id); a.lifecycle_status = "abandoned"
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_openapi_documents_all_required_routes(env):
    _, client = env
    paths = client.get("/openapi.json").json()["paths"]
    required = ["/api/v1/missions", "/api/v1/missions/{mission_id}", "/api/v1/missions/{mission_id}/artifacts", "/api/v1/artifacts",
                "/api/v1/artifacts/{artifact_id}", "/api/v1/artifacts/{artifact_id}/sources", "/api/v1/artifacts/{artifact_id}/images",
                "/api/v1/artifacts/{artifact_id}/location", "/api/v1/catalogue-records", "/api/v1/catalogue-records/{record_id}",
                "/api/v1/sources", "/api/v1/sources/{source_id}", "/api/v1/sources/{source_id}/jobs", "/api/v1/ingestion/jobs",
                "/api/v1/ingestion/jobs/{job_id}", "/api/v1/verification/queue", "/api/v1/verification/records/{record_id}",
                "/api/v1/verification/records/{record_id}/review"]
    assert [p for p in required if p not in paths] == []
