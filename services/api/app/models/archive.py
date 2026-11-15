from datetime import date

from sqlalchemy import JSON, Boolean, CheckConstraint, Date, Float, ForeignKey as FK, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.lifecycle import LIFECYCLE_STATUSES, VERIFICATION_STATUSES


def _in(col: str, values) -> str:
    return f"{col} IN ({', '.join(repr(v) for v in values)})"


class Mission(Base, TimestampMixin):
    __tablename__ = "missions"
    __table_args__ = (
        CheckConstraint(_in("lifecycle_status", LIFECYCLE_STATUSES), name="ck_mission_lifecycle"),
        CheckConstraint(_in("verification_status", VERIFICATION_STATUSES), name="ck_mission_verification"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    agency_id: Mapped[int | None] = mapped_column(FK("agencies.id"), index=True)
    destination_id: Mapped[int | None] = mapped_column(FK("celestial_objects.id"), index=True)
    mission_type: Mapped[str | None] = mapped_column(String(60))
    launch_date: Mapped[date | None] = mapped_column(Date)
    arrival_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    objective: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    lifecycle_status: Mapped[str] = mapped_column(String(40), default="unknown_or_unverified", index=True)
    status_verified_on: Mapped[date | None] = mapped_column(Date)
    status_note: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    is_demo_content: Mapped[bool] = mapped_column(Boolean, default=False)
    destination: Mapped["CelestialObject | None"] = relationship(foreign_keys=[destination_id])
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="mission", cascade="all, delete-orphan")
    events: Mapped[list["MissionEvent"]] = relationship(back_populates="mission", order_by="MissionEvent.event_date", cascade="all, delete-orphan")
    sources: Mapped[list["MissionSource"]] = relationship(back_populates="mission", cascade="all, delete-orphan")


class MissionSource(Base):
    __tablename__ = "mission_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(FK("missions.id", ondelete="CASCADE"), index=True)
    data_source_id: Mapped[int] = mapped_column(FK("data_sources.id"), index=True)
    url: Mapped[str | None] = mapped_column(String(1000))
    note: Mapped[str | None] = mapped_column(Text)
    mission: Mapped[Mission] = relationship(back_populates="sources")


class MissionEvent(Base):
    __tablename__ = "mission_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(FK("missions.id", ondelete="CASCADE"), index=True)
    phase: Mapped[str] = mapped_column(String(30))  # conception..legacy
    event_date: Mapped[date | None] = mapped_column(Date)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    is_last_documented: Mapped[bool] = mapped_column(Boolean, default=False)
    source_id: Mapped[int | None] = mapped_column(FK("data_sources.id"))
    mission: Mapped[Mission] = relationship(back_populates="events")


class Artifact(Base, TimestampMixin):
    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint("mission_id", "slug", name="uq_artifact_mission_slug"),
        CheckConstraint(_in("lifecycle_status", LIFECYCLE_STATUSES), name="ck_artifact_lifecycle"),
        CheckConstraint(_in("verification_status", VERIFICATION_STATUSES), name="ck_artifact_verification"),
        Index("ix_artifact_filters", "destination_id", "lifecycle_status", "hardware_category"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(FK("missions.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(200), index=True)
    alt_names: Mapped[list] = mapped_column(JSON, default=list)
    destination_id: Mapped[int | None] = mapped_column(FK("celestial_objects.id"))
    hardware_category: Mapped[str | None] = mapped_column(String(60))
    purpose: Mapped[str | None] = mapped_column(Text)
    instrument_info: Mapped[str | None] = mapped_column(Text)
    deployment_date: Mapped[date | None] = mapped_column(Date)
    operational_history: Mapped[str | None] = mapped_column(Text)
    scientific_contribution: Mapped[str | None] = mapped_column(Text)
    historical_significance: Mapped[str | None] = mapped_column(Text)
    lifecycle_status: Mapped[str] = mapped_column(String(40), default="unknown_or_unverified")
    left_behind_reason: Mapped[str | None] = mapped_column(Text)
    legacy: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    catalogue_record_id: Mapped[int | None] = mapped_column(FK("catalogue_records.id"), unique=True)
    destination: Mapped["CelestialObject | None"] = relationship(foreign_keys=[destination_id])
    mission: Mapped[Mission] = relationship(back_populates="artifacts")
    location: Mapped["ArtifactLocation | None"] = relationship(back_populates="artifact", uselist=False, cascade="all, delete-orphan")
    sources: Mapped[list["ArtifactSource"]] = relationship(back_populates="artifact", cascade="all, delete-orphan")
    images: Mapped[list["ArtifactImage"]] = relationship(back_populates="artifact", cascade="all, delete-orphan")


class ArtifactLocation(Base, TimestampMixin):
    __tablename__ = "artifact_locations"
    __table_args__ = (
        CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="ck_loc_lat"),
        CheckConstraint("longitude IS NULL OR (longitude >= -180 AND longitude <= 360)", name="ck_loc_lon"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    artifact_id: Mapped[int] = mapped_column(FK("artifacts.id", ondelete="CASCADE"), unique=True)
    latitude: Mapped[float | None] = mapped_column(Float)   # normalized, used for display
    longitude: Mapped[float | None] = mapped_column(Float)
    coordinate_system: Mapped[str] = mapped_column(String(120), default="not stated in source")
    location_precision: Mapped[str] = mapped_column(String(40), default="as_printed")  # as_printed|approximate|region_only
    original_printed: Mapped[str | None] = mapped_column(String(300))
    printed_latitude: Mapped[float | None] = mapped_column(Float)
    printed_longitude: Mapped[float | None] = mapped_column(Float)
    data_source_id: Mapped[int | None] = mapped_column(FK("data_sources.id"))
    source_page: Mapped[int | None] = mapped_column(Integer)
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    review_notes: Mapped[str | None] = mapped_column(Text)
    artifact: Mapped[Artifact] = relationship(back_populates="location")


class ArtifactSource(Base):
    __tablename__ = "artifact_sources"
    __table_args__ = (
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_artsrc_conf"),
        Index("ix_artsrc_artifact", "artifact_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    artifact_id: Mapped[int] = mapped_column(FK("artifacts.id", ondelete="CASCADE"))
    data_source_id: Mapped[int] = mapped_column(FK("data_sources.id"), index=True)
    catalogue_record_id: Mapped[int | None] = mapped_column(FK("catalogue_records.id"))
    document_title: Mapped[str | None] = mapped_column(String(300))
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    evidence_description: Mapped[str | None] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String(40), default="catalogue_entry")
    confidence: Mapped[float | None] = mapped_column(Float)
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    artifact: Mapped[Artifact] = relationship(back_populates="sources")


class ArtifactImage(Base, TimestampMixin):
    __tablename__ = "artifact_images"
    id: Mapped[int] = mapped_column(primary_key=True)
    artifact_id: Mapped[int] = mapped_column(FK("artifacts.id", ondelete="CASCADE"), index=True)
    image_url: Mapped[str | None] = mapped_column(String(1000))
    storage_ref: Mapped[str | None] = mapped_column(String(500))
    title: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    creator: Mapped[str | None] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    license_info: Mapped[str | None] = mapped_column(Text)
    depicts_artifact: Mapped[bool | None] = mapped_column(Boolean)  # NULL = not yet established
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    artifact: Mapped[Artifact] = relationship(back_populates="images")
