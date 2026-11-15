from datetime import date, datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    total: int
    limit: int
    offset: int
    items: list[T]


class SourceOut(BaseModel):
    id: int; slug: str; name: str; agency: str; category: str; description: str | None; official_url: str
    dataset_identifier: str | None; data_format: str | None; access_method: str | None; retrieval_method: str | None
    attribution: str | None; license_note: str | None
    challenge_listing_status: str; listing_checked_at: datetime | None
    integration_status: str; last_retrieved_at: datetime | None; last_ingested_at: datetime | None; verified_at: datetime | None
    is_active: bool; review_notes: str | None
    model_config = {"from_attributes": True}


class JobOut(BaseModel):
    id: int; data_source_id: int; retry_of_id: int | None; status: str; source_url: str | None; document_sha256: str | None
    started_at: datetime; finished_at: datetime | None
    records_seen: int; records_created: int; records_skipped_existing: int; records_flagged: int; records_failed: int
    error: str | None; report: dict; log: list
    model_config = {"from_attributes": True}


class RecordOut(BaseModel):
    id: int; data_source_id: int; job_id: int | None; source_url: str | None; source_page_url: str | None = None
    document_title: str | None; document_sha256: str; source_page: int; destination: str; section: str
    object_name: str | None; equipment_category: str | None; raw_line: str; raw_location: str | None
    latitude_deg_n: float | None; longitude_deg_e: float | None; location_status: str
    flags: list; validation_notes: list; parsing_confidence: float; extraction_method: str; occurrence: int
    ingested_at: datetime; review_status: str
    normalized_object_name: str | None; normalized_latitude: float | None; normalized_longitude: float | None
    review_note: str | None; reviewed_by_id: int | None; reviewed_at: datetime | None
    model_config = {"from_attributes": True}


class VerificationEventOut(BaseModel):
    id: int; actor_id: int | None; action: str; before: dict; after: dict; note: str | None; created_at: datetime
    model_config = {"from_attributes": True}


class RecordDetail(RecordOut):
    events: list[VerificationEventOut] = []
    related_records: list[RecordOut] = []
    artifact_id: int | None = None


class PromoteIn(BaseModel):
    mission_name: str | None = Field(None, max_length=200)
    hardware_category: str | None = Field(None, max_length=60)
    lifecycle_status: str | None = None
    left_behind_reason: str | None = Field(None, max_length=2000)


class ReviewIn(BaseModel):
    action: Literal["approve", "reject", "mark_conflicting", "return_to_review"]
    note: str = Field(min_length=3, max_length=2000)
    normalized_object_name: str | None = Field(None, max_length=300)
    normalized_latitude: float | None = Field(None, ge=-90, le=90)
    normalized_longitude: float | None = Field(None, ge=-180, le=360)
    discard_location: bool = False
    promote: PromoteIn | None = None

    @model_validator(mode="after")
    def _pair(self):
        if (self.normalized_latitude is None) != (self.normalized_longitude is None):
            raise ValueError("normalized_latitude and normalized_longitude must be given together")
        if self.promote and self.action != "approve":
            raise ValueError("promote is only allowed with action=approve")
        return self


class IngestionIn(BaseModel):
    source_slug: str = Field(max_length=80)
    retry_of_job_id: int | None = None


class IdName(BaseModel):
    id: int; name: str
    slug: str | None = None
    model_config = {"from_attributes": True}


class MissionBrief(BaseModel):
    id: int; slug: str; name: str; lifecycle_status: str; verification_status: str
    destination: IdName | None = None; launch_date: date | None = None
    model_config = {"from_attributes": True}


class MissionOut(MissionBrief):
    mission_type: str | None; arrival_date: date | None; end_date: date | None; objective: str | None; description: str | None
    status_verified_on: date | None; status_note: str | None; is_demo_content: bool
    artifact_count: int = 0


class LocationOut(BaseModel):
    latitude: float | None; longitude: float | None; coordinate_system: str; location_precision: str
    original_printed: str | None; printed_latitude: float | None; printed_longitude: float | None
    data_source_id: int | None; source_page: int | None; verification_status: str; review_notes: str | None
    model_config = {"from_attributes": True}


class ArtifactSourceOut(BaseModel):
    id: int; data_source_id: int; catalogue_record_id: int | None; document_title: str | None; source_page: int | None
    source_url: str | None; evidence_description: str | None; evidence_type: str; confidence: float | None; verification_status: str
    model_config = {"from_attributes": True}


class ImageOut(BaseModel):
    id: int; image_url: str | None; storage_ref: str | None; title: str | None; description: str | None; creator: str | None
    source_url: str | None; license_info: str | None; depicts_artifact: bool | None; verification_status: str
    model_config = {"from_attributes": True}


class EventOut(BaseModel):
    id: int; phase: str; event_date: date | None; title: str; description: str | None; is_last_documented: bool
    model_config = {"from_attributes": True}


class ArtifactBrief(BaseModel):
    id: int; slug: str; name: str; hardware_category: str | None; lifecycle_status: str; verification_status: str
    verification_badge: str; mission: MissionBrief; destination: IdName | None = None
    has_location: bool = False; location_precision: str | None = None


class ArtifactDetail(ArtifactBrief):
    alt_names: list; purpose: str | None; instrument_info: str | None; deployment_date: date | None
    operational_history: str | None; scientific_contribution: str | None; historical_significance: str | None
    left_behind_reason: str | None; legacy: str | None
    location: LocationOut | None = None
    sources: list[ArtifactSourceOut] = []
    images: list[ImageOut] = []
    timeline: list[EventOut] = []
