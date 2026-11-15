# NSSDCA / NASA mission-resource retrieval

The NSSDCA and the NASA mission pages supplied in the challenge Resources list are seeded in `app.ingestion.registry`. The seed records the project owner's manual listing confirmation date (2026-11-15) and the official challenge Resources URL in the review note. The Moon catalogue PDF is separately marked `not_listed_verified`; supplemental sources not present in the supplied list remain `listing_unknown`.

## Retrieve source snapshots

From `services/api` after configuring the database and installing `requirements.txt`:

```bash
python scripts/inspect_challenge_mission_sources.py
```

The adapter only permits HTTPS pages on `nssdc.gsfc.nasa.gov` and `science.nasa.gov`. It saves HTML title, description, extracted page text, final URL, retrieval timestamp, response status and SHA-256 to `data/nasa_resource_snapshots/`. It rejects non-HTML responses and off-domain redirects.

These snapshots are **source evidence, not normalized mission or artifact records**. The adapter deliberately does not infer dates, status, coordinates or instrument facts. A later normalization step must map supported values into Mission/Artifact rows and send them to the human verification queue before publication. Failed requests are written to `report.json` with an error and can be retried by running the script again.
