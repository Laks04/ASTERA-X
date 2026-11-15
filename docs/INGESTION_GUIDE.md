# Ingestion guide

## Moon catalogue (implemented)
Pipeline: `app/ingestion/pdf.py` (download, validate, extract) → `moon_catalogue.py` (parse, flag, store) → `service.py` (job orchestration).

```bash
cd services/api
alembic upgrade head
python scripts/ingest_moon_catalogue.py                    # download the registered NASA URL
python scripts/ingest_moon_catalogue.py --pdf ./catalogue.pdf   # locally supplied PDF
python scripts/ingest_moon_catalogue.py --retry 3          # re-run a failed/partial job from its stored input
```
Output is a report: checksum, rows parsed/created/skipped/failed, flagged count, flags by code, rows by section. Exit code 1 if the job failed.
The same run is available as `POST /api/v1/ingestion/jobs` (admin only, 5 per minute); it downloads only the URL stored in the registry.

Safeguards: HTTPS and `nasa.gov` hosts only; content type and `%PDF` header checked; 30 MB / 200 page limits; network errors retried with backoff,
wrong files are not retried; input that does not look like the catalogue (fewer than 20 rows or 3 sections) fails the job and stores nothing;
a row that fails to store is logged and the job becomes `partial`; re-running is idempotent; a PDF with a different checksum creates a new, separate set of records (old ones are kept).

## Review flags
`invalid_coordinate_needs_review`, `missing_coordinates`, `layout_inferred_association`, `region_only`, `ambiguous_equipment_name`,
`duplicate_in_source`, `conflicting_entry`, `uncertain_mission_attribution`. Any flag puts the record in the review queue (`needs_review`).
`parsing_confidence` is the confidence that the structured fields faithfully reflect the printed text (0.95 normal, 0.9 with a source typo noted, 0.5 layout-inferred, 0.3 no object name). It says nothing about whether NASA's coordinates are right.

## Known scope limits
Only site-level rows are ingested (83 rows from the test excerpt). Per-item crew-equipment lines, and entries with no printed location text (e.g. some subsatellites), are not captured yet.
The parser has been run on a real PDF generated from the excerpt, **not on NASA's PDF** (the build environment could not reach nasa.gov). Layout differences in `pdftotext` output for the real file are the main risk: run the script, read the report, and check the flagged rows against the PDF.

## Adapter roadmap (nothing below is implemented; no endpoint has been tested)
Each adapter will follow the same shape: fetch → validate → parse → normalize with provenance → dedupe → store → log → report, with timeouts, retries and a registry-bound URL.

| Adapter | Given URL | Known | Still to establish before coding | Test plan |
|---|---|---|---|---|
| LROC | lroc.im-ldi.com/images | Image catalogue site | Whether there is a documented query/metadata API; image license; rate limits | Recorded HTML/JSON fixtures; a human decides whether an image resolves hardware (`depicts_artifact`) |
| ALSJ / AFJ | nasa.gov/history/alsj-and-afj/ | HTML journal pages | Page structure per mission; reuse terms; how to cite page + timestamp | Fixture pages; assert citations keep URL and anchor |
| PDS Geosciences Apollo (ALSEP) | pds-geosciences.wustl.edu/missions/apollo/ | PDS archive tree | Which volumes hold which experiments; label (.lbl) formats; file sizes (never bulk download) | Parse small real label/data files; unit test unit/time handling; charts only from parsed data |
| HiRISE PDS + ODE REST | hirise-pds.lpl.arizona.edu/PDS/, oderest.rsl.wustl.edu/live2/ | Archive and a REST base URL | Query parameters, response schema, thumbnail availability, rate limits | Contract tests on recorded responses; resolution check before any "shows rover" claim |
| NSSDCA Master Catalog | nssdc.gsfc.nasa.gov/nmc/ | Web catalogue | Whether pages are machine-readable; field mapping to missions; usage terms | Fixture pages; cross-check launch dates/IDs against missions and raise `conflicting_evidence` on disagreement |

Rate limits, licences and attribution text must be read from each provider and written into `data_sources` (`license_note`, `attribution`) before an adapter is marked active.
