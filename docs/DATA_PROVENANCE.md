# Data provenance

Every `catalogue_records` row keeps: data source, ingestion job, source URL, document title, **document SHA-256**, **page number**, destination, section,
the **original line** (`raw_line`, never edited) and printed location, parsed printed values, review flags, validation notes, parsing confidence,
extraction method (extractor + parser version), content hash and occurrence number, ingestion time.
Human corrections live in separate `normalized_*` columns; each review writes an immutable `verification_events` row (who, when, before/after, note).

Artifacts inherit provenance through `artifact_sources` (data source, document title, page, URL with `#page=N`, the catalogue line as evidence, confidence, verification status) and `artifact_locations` (original printed text + printed numbers beside the display coordinates).
Duplicates are kept as separate occurrences and flagged; they are never deleted. A changed PDF (new checksum) adds a new record set and leaves the old one.
Provenance statements stay accurate to what exists: all current records come from one catalogue; "verified" means human-reviewed against that single page, not independently confirmed.
Not built yet: cross-source verification, image provenance, user-facing source pages in the web app.
AI-generated text is never stored as a NASA-authored fact; artifact narrative fields (`purpose`, `legacy`, etc.) are empty until sourced.
