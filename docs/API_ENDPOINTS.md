# API endpoints (`/api/v1`; interactive docs at `/docs`, schema at `/openapi.json`)

Public reads: `GET /missions`, `/missions/{id}`, `/missions/{id}/artifacts`, `/artifacts`, `/artifacts/{id}` (includes mission, location, sources, images, timeline),
`/artifacts/{id}/sources|images|location`, `/catalogue-records`, `/catalogue-records/{id}`, `/sources`, `/sources/{id}`, `/sources/{id}/jobs`, `/ingestion/jobs`, `/ingestion/jobs/{id}`, `/health`.
Auth: `POST /auth/register|login`, `GET /auth/me` (returns `role`).
Reviewer/admin: `GET /verification/queue`, `GET /verification/records/{id}`, `POST /verification/records/{id}/review`.
Admin only: `POST /ingestion/jobs` (`{"source_slug": "...", "retry_of_job_id": null}`).

Lists return `{total, limit, offset, items}`; `limit` 1 to 100 (200 for records), `offset` ≥ 0, `sort` whitelisted (prefix `-` = descending; 422 otherwise).
Artifact filters: `destination` (moon, mars), `mission_id`, `hardware_category`, `lifecycle_status`, `verification_status`, `has_location`, `q`. Records: `section`, `location_status`, `review_status`, `equipment_category`, `flag`, `source_id`, `q`.
Errors: 401 unauthenticated, 403 wrong role, 404 not found, 409 conflict (e.g. approving impossible coordinates, double promotion), 422 validation, 429 rate limit.
