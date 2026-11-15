import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import admin_user
from app.core.ratelimit import RateLimiter
from app.db.session import get_db
from app.domain.promotion import page_url
from app.ingestion.service import ADAPTERS, run_moon_catalogue
from app.models import User
from app.models.nasa import CatalogueRecord, DataSource, IngestionJob
from app.schemas.archive import IngestionIn, JobOut, Page, RecordOut, SourceOut

log = logging.getLogger("astera.data")
router = APIRouter()
ingest_limiter = RateLimiter(limit=5, window=60)
RECORD_SORTS = {"page": CatalogueRecord.source_page, "name": CatalogueRecord.object_name, "section": CatalogueRecord.section, "ingested_at": CatalogueRecord.ingested_at}


def record_out(r: CatalogueRecord) -> RecordOut:
    o = RecordOut.model_validate(r)
    o.source_page_url = page_url(r)
    return o


@router.get("/sources", response_model=Page[SourceOut])
def list_sources(category: str | None = None, challenge_listing_status: str | None = None, q: str | None = Query(None, max_length=100),
                 limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    stmt = select(DataSource)
    if category: stmt = stmt.where(DataSource.category == category)
    if challenge_listing_status: stmt = stmt.where(DataSource.challenge_listing_status == challenge_listing_status)
    if q: stmt = stmt.where(DataSource.name.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    return Page(total=total, limit=limit, offset=offset, items=db.scalars(stmt.order_by(DataSource.id).limit(limit).offset(offset)).all())


@router.get("/sources/{source_id}", response_model=SourceOut)
def get_source(source_id: int, db: Session = Depends(get_db)):
    s = db.get(DataSource, source_id)
    if not s: raise HTTPException(404, "Source not found")
    return s


@router.get("/sources/{source_id}/jobs", response_model=Page[JobOut])
def source_jobs(source_id: int, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    if not db.get(DataSource, source_id): raise HTTPException(404, "Source not found")
    stmt = select(IngestionJob).where(IngestionJob.data_source_id == source_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    return Page(total=total, limit=limit, offset=offset, items=db.scalars(stmt.order_by(IngestionJob.id.desc()).limit(limit).offset(offset)).all())


@router.get("/catalogue-records", response_model=Page[RecordOut])
def list_records(
    section: str | None = None, location_status: str | None = None, review_status: str | None = None, equipment_category: str | None = None,
    flag: str | None = Query(None, max_length=60), source_id: int | None = None, q: str | None = Query(None, max_length=100),
    sort: str = "page", limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db),
):
    stmt = select(CatalogueRecord)
    if section: stmt = stmt.where(CatalogueRecord.section == section)
    if location_status: stmt = stmt.where(CatalogueRecord.location_status == location_status)
    if review_status: stmt = stmt.where(CatalogueRecord.review_status == review_status)
    if equipment_category: stmt = stmt.where(CatalogueRecord.equipment_category == equipment_category)
    if source_id: stmt = stmt.where(CatalogueRecord.data_source_id == source_id)
    if flag: stmt = stmt.where(cast(CatalogueRecord.flags, String).like(f'%"{flag}"%'))
    if q: stmt = stmt.where(or_(CatalogueRecord.object_name.ilike(f"%{q}%"), CatalogueRecord.section.ilike(f"%{q}%")))
    col = RECORD_SORTS.get(sort.lstrip("-"))
    if col is None: raise HTTPException(422, f"sort must be one of {sorted(RECORD_SORTS)}")
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(col.desc() if sort.startswith("-") else col.asc(), CatalogueRecord.id).limit(limit).offset(offset)).all()
    return Page(total=total, limit=limit, offset=offset, items=[record_out(r) for r in rows])


@router.get("/catalogue-records/{record_id}", response_model=RecordOut)
def get_record(record_id: int, db: Session = Depends(get_db)):
    r = db.get(CatalogueRecord, record_id)
    if not r: raise HTTPException(404, "Record not found")
    return record_out(r)


@router.get("/ingestion/jobs", response_model=Page[JobOut])
def list_jobs(status: str | None = None, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    stmt = select(IngestionJob)
    if status: stmt = stmt.where(IngestionJob.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    return Page(total=total, limit=limit, offset=offset, items=db.scalars(stmt.order_by(IngestionJob.id.desc()).limit(limit).offset(offset)).all())


@router.get("/ingestion/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    j = db.get(IngestionJob, job_id)
    if not j: raise HTTPException(404, "Job not found")
    return j


@router.post("/ingestion/jobs", response_model=JobOut, status_code=201, dependencies=[Depends(ingest_limiter)])
def start_job(body: IngestionIn, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    """Admin only. Downloads only from the URL stored in the source registry; callers cannot supply URLs or paths."""
    src = db.scalar(select(DataSource).where(DataSource.slug == body.source_slug))
    if not src: raise HTTPException(404, "Unknown source")
    if src.slug not in ADAPTERS: raise HTTPException(422, f"No ingestion adapter is implemented for '{src.slug}'")
    if not src.is_active: raise HTTPException(409, "Source is inactive")
    prev = None
    if body.retry_of_job_id is not None:
        prev = db.get(IngestionJob, body.retry_of_job_id)
        if not prev or prev.data_source_id != src.id: raise HTTPException(404, "Job to retry not found for this source")
        if prev.status == "succeeded": raise HTTPException(409, "Only failed or partial jobs can be retried")
    log.info("ingestion started source=%s user=%s retry_of=%s", src.slug, user.id, body.retry_of_job_id)
    return run_moon_catalogue(db, src, user_id=user.id, retry_of=prev)
