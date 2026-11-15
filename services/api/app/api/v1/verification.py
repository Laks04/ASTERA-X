import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session

from app.api.deps import reviewer_user
from app.api.v1.data import record_out
from app.db.session import get_db
from app.domain.promotion import promote
from app.models import Artifact, User
from app.models.nasa import CatalogueRecord, VerificationEvent
from app.schemas.archive import Page, RecordDetail, RecordOut, ReviewIn, VerificationEventOut

log = logging.getLogger("astera.verification")
router = APIRouter()
NEW_STATUS = {"approve": "verified", "reject": "rejected", "mark_conflicting": "conflicting_evidence", "return_to_review": "needs_review"}
TRACKED = ("review_status", "normalized_object_name", "normalized_latitude", "normalized_longitude", "review_note")


def _snap(r: CatalogueRecord) -> dict:
    return {k: getattr(r, k) for k in TRACKED}


@router.get("/verification/queue", response_model=Page[RecordOut])
def queue(review_status: str = "needs_review", flag: str | None = Query(None, max_length=60), section: str | None = None,
          limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), _: User = Depends(reviewer_user), db: Session = Depends(get_db)):
    stmt = select(CatalogueRecord).where(CatalogueRecord.review_status == review_status)
    if flag: stmt = stmt.where(cast(CatalogueRecord.flags, String).like(f'%"{flag}"%'))
    if section: stmt = stmt.where(CatalogueRecord.section == section)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(CatalogueRecord.source_page, CatalogueRecord.id).limit(limit).offset(offset)).all()
    return Page(total=total, limit=limit, offset=offset, items=[record_out(r) for r in rows])


@router.get("/verification/records/{record_id}", response_model=RecordDetail)
def review_detail(record_id: int, _: User = Depends(reviewer_user), db: Session = Depends(get_db)):
    r = db.get(CatalogueRecord, record_id)
    if not r: raise HTTPException(404, "Record not found")
    events = db.scalars(select(VerificationEvent).where(VerificationEvent.record_id == r.id).order_by(VerificationEvent.id)).all()
    related = db.scalars(select(CatalogueRecord).where(CatalogueRecord.id != r.id, CatalogueRecord.section == r.section,
                                                       CatalogueRecord.object_name == r.object_name)).all() if r.object_name else []
    art_id = db.scalar(select(Artifact.id).where(Artifact.catalogue_record_id == r.id))
    return RecordDetail(**record_out(r).model_dump(), events=[VerificationEventOut.model_validate(e) for e in events],
                        related_records=[record_out(x) for x in related], artifact_id=art_id)


@router.post("/verification/records/{record_id}/review", response_model=RecordDetail)
def review(record_id: int, body: ReviewIn, user: User = Depends(reviewer_user), db: Session = Depends(get_db)):
    """Human review only: there is no machine path that sets 'verified'. Printed values are never modified."""
    r = db.get(CatalogueRecord, record_id)
    if not r: raise HTTPException(404, "Record not found")
    if body.action == "approve" and r.location_status == "invalid_coordinate_needs_review":
        if not body.discard_location and body.normalized_latitude is None:
            raise HTTPException(409, "This record has impossible printed coordinates. Supply corrected normalized coordinates, or set discard_location=true.")
    before = _snap(r)
    if body.normalized_object_name is not None: r.normalized_object_name = body.normalized_object_name
    if body.discard_location:
        r.normalized_latitude = r.normalized_longitude = None
    elif body.normalized_latitude is not None:
        r.normalized_latitude, r.normalized_longitude = body.normalized_latitude, body.normalized_longitude
    r.review_status, r.review_note = NEW_STATUS[body.action], body.note
    r.reviewed_by_id, r.reviewed_at = user.id, datetime.now(timezone.utc)
    artifact_id = None
    try:
        if body.promote:
            p = body.promote
            artifact_id = promote(db, r, mission_name=p.mission_name, hardware_category=p.hardware_category, lifecycle_status=p.lifecycle_status,
                                  left_behind_reason=p.left_behind_reason, discard_location=body.discard_location).id
        db.add(VerificationEvent(record_id=r.id, actor_id=user.id, action=body.action, before=before, after=_snap(r) | ({"artifact_id": artifact_id} if artifact_id else {}), note=body.note))
        db.commit()
    except HTTPException:
        db.rollback(); raise
    log.info("record %s -> %s by user %s", r.id, r.review_status, user.id)
    return review_detail(record_id, user, db)
