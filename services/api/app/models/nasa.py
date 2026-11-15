from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey as FK, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

LISTING_STATUSES = ("listed_verified", "listed_unverified", "not_listed_verified", "listing_unknown")
REVIEW_STATUSES = ("extracted", "needs_review", "verified", "rejected", "conflicting_evidence")
JOB_STATUSES = ("running", "succeeded", "partial", "failed")


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} IN ({', '.join(repr(v) for v in values)})"


class DataSource(Base, TimestampMixin):
    """Registry of every dataset/resource ASTERA uses or investigates."""
    __tablename__ = "data_sources"
    __table_args__ = (
        CheckConstraint(_in("challenge_listing_status", LISTING_STATUSES), name="ck_source_listing_status"),
        # A listing may only be called verified if somebody recorded when the official page was checked.
        CheckConstraint("challenge_listing_status NOT IN ('listed_verified','not_listed_verified') OR listing_checked_at IS NOT NULL",
                        name="ck_source_listing_checked"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(300))
    agency: Mapped[str] = mapped_column(String(80), default="NASA")
    category: Mapped[str] = mapped_column(String(60), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    official_url: Mapped[str] = mapped_column(String(1000))
    dataset_identifier: Mapped[str | None] = mapped_column(String(200))
    access_method: Mapped[str | None] = mapped_column(String(200))
    data_format: Mapped[str | None] = mapped_column(String(100))
    retrieval_method: Mapped[str | None] = mapped_column(Text)
    attribution: Mapped[str | None] = mapped_column(Text)
    license_note: Mapped[str | None] = mapped_column(Text)
    challenge_listing_status: Mapped[str] = mapped_column(String(30), default="listing_unknown", server_default="listing_unknown")
    listing_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    integration_status: Mapped[str] = mapped_column(String(30), default="not_started", server_default="not_started")
    last_retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # last successful ingestion
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (CheckConstraint(_in("status", JOB_STATUSES), name="ck_job_status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    data_source_id: Mapped[int] = mapped_column(FK("data_sources.id"), index=True)
    retry_of_id: Mapped[int | None] = mapped_column(FK("ingestion_jobs.id"))
    triggered_by_id: Mapped[int | None] = mapped_column(FK("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    source_url: Mapped[str | None] = mapped_column(String(1000))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    input_text: Mapped[str | None] = mapped_column(Text)  # extracted page text, kept so failed jobs can be retried offline
    records_seen: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_skipped_existing: Mapped[int] = mapped_column(Integer, default=0)
    records_flagged: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    log: Mapped[list] = mapped_column(JSON, default=list)


class CatalogueRecord(Base, TimestampMixin):
    """One row of the NASA History 'Catalogue of Manmade Material on the Moon', with provenance.

    Printed values (raw_line, raw_location, latitude_deg_n, longitude_deg_e) are never edited.
    Human corrections go in the normalized_* columns and every change is written to verification_events.
    """
    __tablename__ = "catalogue_records"
    __table_args__ = (
        UniqueConstraint("data_source_id", "document_sha256", "content_hash", "occurrence", name="uq_record_identity"),
        CheckConstraint(_in("review_status", REVIEW_STATUSES), name="ck_record_review_status"),
        Index("ix_record_queue", "review_status", "section"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    data_source_id: Mapped[int] = mapped_column(FK("data_sources.id"), index=True)
    job_id: Mapped[int | None] = mapped_column(FK("ingestion_jobs.id"), index=True)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    document_title: Mapped[str | None] = mapped_column(String(300))
    document_sha256: Mapped[str] = mapped_column(String(64))
    source_page: Mapped[int] = mapped_column(Integer)
    destination: Mapped[str] = mapped_column(String(20), default="Moon", index=True)
    section: Mapped[str] = mapped_column(String(80), index=True)
    object_name: Mapped[str | None] = mapped_column(String(300), index=True)
    equipment_category: Mapped[str | None] = mapped_column(String(60), index=True)
    raw_line: Mapped[str] = mapped_column(Text)
    raw_location: Mapped[str | None] = mapped_column(String(300))
    latitude_deg_n: Mapped[float | None] = mapped_column(Float)   # as printed
    longitude_deg_e: Mapped[float | None] = mapped_column(Float)  # as printed
    location_status: Mapped[str] = mapped_column(String(40), index=True)
    flags: Mapped[list] = mapped_column(JSON, default=list)
    validation_notes: Mapped[list] = mapped_column(JSON, default=list)
    parsing_confidence: Mapped[float] = mapped_column(Float, default=0.95)
    extraction_method: Mapped[str] = mapped_column(String(80))
    content_hash: Mapped[str] = mapped_column(String(64))
    occurrence: Mapped[int] = mapped_column(Integer, default=1)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    review_status: Mapped[str] = mapped_column(String(30), default="extracted")
    normalized_object_name: Mapped[str | None] = mapped_column(String(300))
    normalized_latitude: Mapped[float | None] = mapped_column(Float)
    normalized_longitude: Mapped[float | None] = mapped_column(Float)
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by_id: Mapped[int | None] = mapped_column(FK("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VerificationEvent(Base):
    """Append-only audit trail of human review actions."""
    __tablename__ = "verification_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(FK("catalogue_records.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[int | None] = mapped_column(FK("users.id"))
    action: Mapped[str] = mapped_column(String(30))
    before: Mapped[dict] = mapped_column(JSON, default=dict)
    after: Mapped[dict] = mapped_column(JSON, default=dict)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
