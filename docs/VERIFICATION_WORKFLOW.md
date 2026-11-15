# Verification workflow

Machines extract; people verify. Nothing in the code path from ingestion to `verified` is automatic.

States: `extracted` (no flags) → `needs_review` (any flag) → `verified` | `rejected` | `conflicting_evidence`; a reviewer can send a record back to `needs_review`.
Roles: `user` (default), `reviewer`, `admin`. Roles are changed only on the server: `python scripts/set_role.py person@example.com reviewer`.

| Endpoint | Who | Does |
|---|---|---|
| `GET /api/v1/verification/queue?flag=&section=&review_status=` | reviewer, admin | Lists records to review |
| `GET /api/v1/verification/records/{id}` | reviewer, admin | Record, `source_page_url` (PDF `#page=N`), original text, audit events, other records with the same mission/name (evidence comparison), linked artifact |
| `POST /api/v1/verification/records/{id}/review` | reviewer, admin | `action`: approve / reject / mark_conflicting / return_to_review; mandatory `note`; optional `normalized_object_name`, `normalized_latitude` + `normalized_longitude`, `discard_location`, and `promote` (approve only) |

Rules: printed values are never modified; every action writes a `verification_events` row (actor, before, after, note) and sets `reviewed_by/at`;
a record with impossible printed coordinates cannot be approved unless the reviewer supplies corrected normalized coordinates or sets `discard_location`;
`promote` creates mission, artifact, location and source rows in the same transaction (a failed promotion rolls back the review);
promotion never invents a lifecycle reason; one record can be promoted once.

Meaning of `verified`: a human compared the extracted record with the source page. With one source the artifact badge is `human_reviewed_single_source`. It does not mean independently confirmed. LROC, ALSJ and NSSDCA cross-checks would raise it to `human_reviewed_multiple_sources`.
AI tools may be used to help a reviewer read a record, but there is no API path for an AI to set `verified`.

## Reviewer checklist
1. Open `source_page_url`; confirm the printed line matches `raw_line`.
2. For `layout_inferred_association`: confirm which name the coordinates belong to on the page image.
3. For `invalid_coordinate_needs_review`: decide between correcting (note why) and discarding the location.
4. Check related records for conflicts. Write a note that another reviewer could follow.
