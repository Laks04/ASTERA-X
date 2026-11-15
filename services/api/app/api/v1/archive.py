from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Artifact, CelestialObject, Mission
from app.schemas.archive import (ArtifactBrief, ArtifactDetail, ArtifactSourceOut, ImageOut, LocationOut, MissionBrief,
                                 MissionOut, Page)

router = APIRouter()
ARTIFACT_SORTS = {"name": Artifact.name, "created_at": Artifact.created_at, "lifecycle_status": Artifact.lifecycle_status,
                  "hardware_category": Artifact.hardware_category, "deployment_date": Artifact.deployment_date}
MISSION_SORTS = {"name": Mission.name, "launch_date": Mission.launch_date, "created_at": Mission.created_at}


def _order(sorts: dict, sort: str):
    col = sorts.get(sort.lstrip("-"))
    if col is None:
        raise HTTPException(422, f"sort must be one of {sorted(sorts)} (prefix '-' for descending)")
    return col.desc() if sort.startswith("-") else col.asc()


def badge(a: Artifact) -> str:
    if a.verification_status == "verified":
        return "human_reviewed_single_source" if len(a.sources) <= 1 else "human_reviewed_multiple_sources"
    return {"rejected": "rejected", "conflicting_evidence": "conflicting_evidence"}.get(a.verification_status, "unverified")


def brief(a: Artifact) -> ArtifactBrief:
    return ArtifactBrief(
        id=a.id, slug=a.slug, name=a.name, hardware_category=a.hardware_category, lifecycle_status=a.lifecycle_status,
        verification_status=a.verification_status, verification_badge=badge(a), mission=MissionBrief.model_validate(a.mission),
        destination=a.destination, has_location=a.location is not None and a.location.latitude is not None,
        location_precision=a.location.location_precision if a.location else None)


def detail(a: Artifact) -> ArtifactDetail:
    b = brief(a)
    return ArtifactDetail(
        **b.model_dump(), alt_names=a.alt_names or [], purpose=a.purpose, instrument_info=a.instrument_info,
        deployment_date=a.deployment_date, operational_history=a.operational_history, scientific_contribution=a.scientific_contribution,
        historical_significance=a.historical_significance, left_behind_reason=a.left_behind_reason, legacy=a.legacy,
        location=LocationOut.model_validate(a.location) if a.location else None,
        sources=[ArtifactSourceOut.model_validate(s) for s in a.sources], images=[ImageOut.model_validate(i) for i in a.images],
        timeline=[e for e in a.mission.events])


def _artifact_query():
    return select(Artifact).options(selectinload(Artifact.mission).selectinload(Mission.destination), selectinload(Artifact.mission).selectinload(Mission.events),
                                    selectinload(Artifact.destination), selectinload(Artifact.location), selectinload(Artifact.sources),
                                    selectinload(Artifact.images))


@router.get("/missions", response_model=Page[MissionOut])
def list_missions(destination: str | None = None, lifecycle_status: str | None = None, q: str | None = Query(None, max_length=100),
                  sort: str = "name", limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    stmt = select(Mission).options(selectinload(Mission.destination))
    if destination:
        stmt = stmt.join(CelestialObject, Mission.destination_id == CelestialObject.id).where(CelestialObject.slug == destination)
    if lifecycle_status:
        stmt = stmt.where(Mission.lifecycle_status == lifecycle_status)
    if q:
        stmt = stmt.where(Mission.name.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(_order(MISSION_SORTS, sort), Mission.id).limit(limit).offset(offset)).all()
    counts = dict(db.execute(select(Artifact.mission_id, func.count()).where(Artifact.mission_id.in_([m.id for m in rows])).group_by(Artifact.mission_id)).all()) if rows else {}
    items = [MissionOut(**MissionBrief.model_validate(m).model_dump(), mission_type=m.mission_type, arrival_date=m.arrival_date, end_date=m.end_date,
                        objective=m.objective, description=m.description, status_verified_on=m.status_verified_on, status_note=m.status_note,
                        is_demo_content=m.is_demo_content, artifact_count=counts.get(m.id, 0)) for m in rows]
    return Page(total=total, limit=limit, offset=offset, items=items)


def _mission_or_404(db: Session, mission_id: int) -> Mission:
    m = db.scalar(select(Mission).options(selectinload(Mission.destination)).where(Mission.id == mission_id))
    if not m:
        raise HTTPException(404, "Mission not found")
    return m


@router.get("/missions/{mission_id}", response_model=MissionOut)
def get_mission(mission_id: int, db: Session = Depends(get_db)):
    m = _mission_or_404(db, mission_id)
    n = db.scalar(select(func.count()).select_from(Artifact).where(Artifact.mission_id == m.id))
    return MissionOut(**MissionBrief.model_validate(m).model_dump(), mission_type=m.mission_type, arrival_date=m.arrival_date, end_date=m.end_date,
                      objective=m.objective, description=m.description, status_verified_on=m.status_verified_on, status_note=m.status_note,
                      is_demo_content=m.is_demo_content, artifact_count=n)


@router.get("/missions/{mission_id}/artifacts", response_model=Page[ArtifactBrief])
def mission_artifacts(mission_id: int, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    _mission_or_404(db, mission_id)
    stmt = _artifact_query().where(Artifact.mission_id == mission_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Artifact.name).limit(limit).offset(offset)).all()
    return Page(total=total, limit=limit, offset=offset, items=[brief(a) for a in rows])


@router.get("/artifacts", response_model=Page[ArtifactBrief])
def list_artifacts(
    destination: str | None = Query(None, description="celestial object slug, e.g. moon or mars"), mission_id: int | None = None,
    hardware_category: str | None = None, lifecycle_status: str | None = None, verification_status: str | None = None,
    has_location: bool | None = None, q: str | None = Query(None, max_length=100), sort: str = "name",
    limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db),
):
    stmt = _artifact_query()
    if destination:
        stmt = stmt.join(CelestialObject, Artifact.destination_id == CelestialObject.id).where(CelestialObject.slug == destination)
    if mission_id is not None:
        stmt = stmt.where(Artifact.mission_id == mission_id)
    if hardware_category:
        stmt = stmt.where(Artifact.hardware_category == hardware_category)
    if lifecycle_status:
        stmt = stmt.where(Artifact.lifecycle_status == lifecycle_status)
    if verification_status:
        stmt = stmt.where(Artifact.verification_status == verification_status)
    if has_location is not None:
        from app.models import ArtifactLocation
        sub = select(ArtifactLocation.artifact_id).where(ArtifactLocation.latitude.is_not(None))
        stmt = stmt.where(Artifact.id.in_(sub) if has_location else Artifact.id.not_in(sub))
    if q:
        stmt = stmt.where(or_(Artifact.name.ilike(f"%{q}%"), Artifact.slug.ilike(f"%{q}%")))
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.order_by(_order(ARTIFACT_SORTS, sort), Artifact.id).limit(limit).offset(offset)).all()
    return Page(total=total, limit=limit, offset=offset, items=[brief(a) for a in rows])


def _artifact_or_404(db: Session, artifact_id: int) -> Artifact:
    a = db.scalar(_artifact_query().where(Artifact.id == artifact_id))
    if not a:
        raise HTTPException(404, "Artifact not found")
    return a


@router.get("/artifacts/{artifact_id}", response_model=ArtifactDetail)
def get_artifact(artifact_id: int, db: Session = Depends(get_db)):
    return detail(_artifact_or_404(db, artifact_id))


@router.get("/artifacts/{artifact_id}/sources", response_model=list[ArtifactSourceOut])
def artifact_sources(artifact_id: int, db: Session = Depends(get_db)):
    return _artifact_or_404(db, artifact_id).sources


@router.get("/artifacts/{artifact_id}/images", response_model=list[ImageOut])
def artifact_images(artifact_id: int, db: Session = Depends(get_db)):
    return _artifact_or_404(db, artifact_id).images


@router.get("/artifacts/{artifact_id}/location", response_model=LocationOut)
def artifact_location(artifact_id: int, db: Session = Depends(get_db)):
    a = _artifact_or_404(db, artifact_id)
    if not a.location:
        raise HTTPException(404, "No sourced location is recorded for this artifact")
    return a.location
