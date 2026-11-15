"""Turns a human-approved catalogue record into Mission / Artifact / Location / Source rows."""
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.lifecycle import LifecycleError, LifecycleInput, validate_lifecycle
from app.models import Artifact, ArtifactLocation, ArtifactSource, CelestialObject, Mission
from app.models.nasa import CatalogueRecord


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "unnamed"


def page_url(rec: CatalogueRecord) -> str | None:
    return f"{rec.source_url}#page={rec.source_page}" if rec.source_url else None


def effective_coordinates(rec: CatalogueRecord, discard: bool = False) -> tuple[float | None, float | None]:
    if discard:
        return None, None
    if rec.normalized_latitude is not None and rec.normalized_longitude is not None:
        return rec.normalized_latitude, rec.normalized_longitude
    if rec.location_status == "coordinates_stated":
        return rec.latitude_deg_n, rec.longitude_deg_e
    return None, None


def promote(db: Session, rec: CatalogueRecord, *, mission_name: str | None, hardware_category: str | None,
            lifecycle_status: str | None, left_behind_reason: str | None, discard_location: bool) -> Artifact:
    if db.scalar(select(Artifact.id).where(Artifact.catalogue_record_id == rec.id)):
        raise HTTPException(409, "This record has already been promoted to an artifact.")
    name = rec.normalized_object_name or rec.object_name
    if not name:
        raise HTTPException(422, "Record has no object name; set normalized_object_name before promoting.")
    moon = db.scalar(select(CelestialObject).where(CelestialObject.slug == rec.destination.lower()))
    if not moon:
        moon = CelestialObject(slug=rec.destination.lower(), name=rec.destination, kind="moon")
        db.add(moon); db.flush()
    m_name = mission_name or (rec.section if rec.section.startswith("Apollo ") else name)
    mission = db.scalar(select(Mission).where(Mission.slug == slugify(m_name)))
    if not mission:
        mission = Mission(slug=slugify(m_name), name=m_name, destination_id=moon.id)
        db.add(mission); db.flush()
    status = lifecycle_status or ("crashed_or_impacted" if rec.location_status == "impact_noted" and (rec.raw_location or "").lower() == "crashed" else "unknown_or_unverified")
    lat, lon = effective_coordinates(rec, discard_location)
    try:
        validate_lifecycle(LifecycleInput(status=status, left_behind_reason=left_behind_reason, has_surface_location=False,
                                          has_supporting_source=True, verification_status="verified", mission_status=mission.lifecycle_status))
    except LifecycleError as e:
        raise HTTPException(422, str(e))
    art = Artifact(mission_id=mission.id, slug=slugify(name), name=name, destination_id=moon.id,
                   hardware_category=hardware_category or rec.equipment_category, lifecycle_status=status,
                   left_behind_reason=left_behind_reason, verification_status="verified", catalogue_record_id=rec.id)
    db.add(art); db.flush()
    if lat is not None:
        corrected = (lat, lon) != (rec.latitude_deg_n, rec.longitude_deg_e)
        db.add(ArtifactLocation(
            artifact_id=art.id, latitude=lat, longitude=lon, original_printed=rec.raw_location,
            printed_latitude=rec.latitude_deg_n, printed_longitude=rec.longitude_deg_e, data_source_id=rec.data_source_id,
            source_page=rec.source_page, verification_status="verified",
            review_notes="Coordinates corrected by a reviewer; printed values preserved." if corrected else "Coordinates as printed in the catalogue."))
    db.add(ArtifactSource(
        artifact_id=art.id, data_source_id=rec.data_source_id, catalogue_record_id=rec.id, document_title=rec.document_title,
        source_page=rec.source_page, source_url=page_url(rec), evidence_type="catalogue_entry", confidence=rec.parsing_confidence,
        evidence_description=f"Catalogue line (page {rec.source_page}): {rec.raw_line}", verification_status="verified"))
    db.flush()
    return art
