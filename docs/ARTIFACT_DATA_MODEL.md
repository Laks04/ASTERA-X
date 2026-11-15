# Artifact data model

Source of truth: `services/api/app/models/` and migration `alembic/versions/0001_initial_schema.py`.

```
data_sources 1─* ingestion_jobs 1─* catalogue_records 1─* verification_events
      │                                   │ (promotion, human approval only)
      │                                   ▼
celestial_objects 1─* missions 1─* artifacts 1─0..1 artifact_locations
                          │            ├─* artifact_sources ──► data_sources, catalogue_records
                          │            └─* artifact_images
                          ├─* mission_events
                          └─* mission_sources ──► data_sources
```

| Table | Purpose | Key constraints |
|---|---|---|
| `data_sources` | Registry of datasets | `challenge_listing_status` CHECK in the four allowed values; `listed_verified`/`not_listed_verified` require `listing_checked_at` |
| `ingestion_jobs` | One row per run (also failed ones) | status in running/succeeded/partial/failed; stores `document_sha256`, `input_text` (for retry), counts, `report`, `log`, `retry_of_id` |
| `catalogue_records` | One catalogue row, machine-extracted | unique `(data_source_id, document_sha256, content_hash, occurrence)`; `review_status` CHECK |
| `verification_events` | Append-only audit trail | FK to record (cascade), actor, before/after JSON, note |
| `missions` | Mission facts | lifecycle and verification CHECKs; `is_demo_content` flag |
| `artifacts` | One piece of hardware | unique `(mission_id, slug)`; lifecycle CHECK; `catalogue_record_id` unique |
| `artifact_locations` | Sourced position | lat -90..90, lon -180..360 CHECK; printed and normalized values kept apart |
| `artifact_sources` | Evidence for an artifact (many per artifact) | confidence 0..1 CHECK; page, URL, evidence type |
| `artifact_images` | Images | `depicts_artifact` is NULL until a human establishes it |

## Printed vs normalized
`catalogue_records.raw_line`, `raw_location`, `latitude_deg_n`, `longitude_deg_e` are what the PDF said and are never edited.
Reviewer corrections go to `normalized_*`. `artifact_locations` carries `printed_*` and the display `latitude/longitude` side by side.
`coordinate_system` defaults to "not stated in source": the catalogue does not specify one and ASTERA does not assume one.

## Lifecycle rules (`app/domain/lifecycle.py`)
Statuses: `operational`, `still_travelling`, `mission_completed_hardware_left_behind`, `decommissioned_or_dormant`, `lost_contact_or_failed`, `crashed_or_impacted`, `unknown_or_unverified`.
Rules enforced at promotion: active artifacts cannot carry a left-behind reason; a reason needs a supporting source and a compatible status;
`still_travelling` cannot have a surface location; a verified status needs a source; an artifact cannot be "left behind" while its mission is operational/still travelling.
Defaults are conservative: promotion sets `unknown_or_unverified`, except `crashed_or_impacted` when the catalogue itself prints "Crashed". Reasons are never auto-filled.
Mission status and artifact status are separate columns.

## Equipment categories
Derived only from words in the printed name (`descent_stage`, `ascent_stage`, `central_station`, `retroreflector`, `launch_vehicle_stage`, `rover`, `lander`, `orbiter`, `subsatellite`, `probe`, `landing_site`). "Surveyor 1" gets no category because the line does not say what it is.

## Not yet modelled / not yet populated
Mars records, mission timelines (table exists, no content), images (table exists, none ingested), scientific observations, instruments.
