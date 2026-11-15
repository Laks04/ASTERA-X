# Phase 2 test report (2026-11-14)

Environment: Python 3.12, FastAPI 0.115, SQLAlchemy 2.0.57, Alembic 1.14.1, pgvector 0.3.6, pytest 8.4.2; embedded **PostgreSQL 16.2 + pgvector 0.6.2** via `pgserver` 0.1.4; poppler `pdftotext`.
Commands: `cd services/api && pytest -q -p no:logging` (all), `pytest -m pg` (Postgres only).

## Result: 59 passed, 0 failed
| File | Tests | Runs on | Covers |
|---|---|---|---|
| test_catalogue.py | 11 | SQLite-free (pure) | Ranger 9 invalid latitude kept as printed + flagged; Luna 10/13/19/20 layout inference; unknown/impact/region/missing; categories; duplicate and conflict flags; stray-space typo; unsectioned entries |
| test_ingestion.py | 12 | SQLite | Provenance on every record; idempotency; new checksum = new set; duplicates kept; non-catalogue input fails cleanly; partial job; report; URL allow-list; content-type/header validation; retry vs no-retry on download; **real generated PDF through pdftotext** + parser + idempotency; failed download logged; retry from stored input |
| test_lifecycle.py | 8 | pure | All lifecycle validation rules |
| test_archive_and_verification.py | 18 | SQLite | 401/403/allow for verification and ingestion; admin-only + registry-bound ingestion; rate limit; audit trail and preserved printed values; queue filters; invalid-coordinate approval rules; state transitions; promotion (mission, artifact, location, source, provenance); double promotion and rollback; conservative lifecycle; filters/search/sort/pagination; mission relationships; registry never shows `listed_verified`; DB CHECK constraints; OpenAPI lists every required route |
| test_auth.py | 3 | SQLite | Phase 1 auth preserved |
| test_postgres.py | 7 | **PostgreSQL 16.2** | Empty DB → head (vector extension, `vector` column type, single head); **no model/migration drift**; no `create_all` in migrations; downgrade to base and re-upgrade; upgrade on populated DB keeps data; CHECK constraints + pgvector nearest-neighbour; ingestion + review + promotion + filtering through the API on Postgres (JSON-as-text flag filter) |

Also run by hand: the CLI (`alembic upgrade head`, `scripts/ingest_moon_catalogue.py --pdf`) against Postgres: 83 rows created, 22 flagged; second run created 0; a missing file exits 1 with a failed job.

## Could not run / not run
- **Anything against NASA's live servers or the real catalogue PDF.** The environment could not reach nasa.gov from the shell, so the full-PDF run is outstanding (no test is marked `network`; none exist). The parser was exercised on a real PDF *generated from a 83-row excerpt*, not on NASA's file.
- Postgres via Docker / a managed service; only the embedded server was used.
- Downgrade-to-previous-revision (only one revision exists).
- Frontend, Expo, end-to-end, accessibility and performance tests (not in Phase 2 scope; web/mobile not touched).
- Auth gaps from Phase 1 remain (password reset, email verification, token revocation).

## Findings fixed during testing
- The embedding column type exposed no pgvector operators in the ORM → added `app/domain/vectors.py`.
- Fixture page numbers: Apollo 13's S-IVB row is on page 6 in the real PDF; the excerpt had page 5 (fixed). Other page numbers were re-checked against the fetched text.
