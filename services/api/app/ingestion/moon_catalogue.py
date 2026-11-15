"""Parser + loader for the NASA History Office 'Catalogue of Manmade Material on the Moon'.

Input is page-delimited text (`=== PAGE n ===`), produced by app.ingestion.pdf from the official PDF.
Only site-level rows are extracted (landing sites, stages, stations, reflectors, spacecraft with a printed
location / UNKNOWN / impact note / region). Per-item crew-equipment inventory lines are NOT ingested.
Printed values are never altered. Anything uncertain gets an explicit flag and goes to the review queue.
"""
import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nasa import CatalogueRecord, DataSource, IngestionJob

PARSER = "regex-line-parser v2"
PAGE_RE = re.compile(r"^=== PAGE (\d+) ===$")
NUM = r"(-?\s?\d+(?:\.\d+)?)"
COORD_RE = re.compile(NUM + r"\s*˚?\s*N\s*,\s*" + NUM + r"\s*˚?\s*E")
SECTION_RE = re.compile(r"^(U\.S\. Material \((?:Non-Apollo|Apollo)\)|Soviet Material|Chinese Material|Indian Material|Japanese Material|ESA Material)$")
APOLLO_RE = re.compile(r"^(Apollo \d+)\b")
STATUS_WORDS = [("UNKNOWN", "unknown_in_source"), ("Crashed", "impact_noted"), ("crash not confirmed", "impact_noted")]
REGION_WORDS = ("South Pole", "Lunar Far Side")

# Category comes only from words in the printed name; no outside knowledge is applied.
CATEGORY_PATTERNS = [
    ("landing_site", r"landing site"), ("descent_stage", r"descent stage"), ("ascent_stage", r"ascent stage"),
    ("central_station", r"central station"), ("retroreflector", r"reflector"), ("launch_vehicle_stage", r"S-IVB|centaur"),
    ("rover", r"lunokhod|roving vehicle"), ("lander", r"lander"), ("orbiter", r"orbiter"),
    ("subsatellite", r"subsatellite"), ("probe", r"probe"),
]
BLOCKING_FLAGS = {
    "invalid_coordinate_needs_review", "missing_coordinates", "layout_inferred_association", "region_only",
    "ambiguous_equipment_name", "duplicate_in_source", "conflicting_entry", "uncertain_mission_attribution",
}


@dataclass
class Parsed:
    section: str
    page: int
    object_name: str | None
    raw_line: str
    raw_location: str | None
    lat: float | None = None
    lon: float | None = None
    status: str = "none_listed"
    notes: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    category: str | None = None
    confidence: float = 0.95
    occurrence: int = 1

    def flag(self, code: str, note: str | None = None) -> None:
        if code not in self.flags:
            self.flags.append(code)
        if note:
            self.notes.append(note)


def _f(x: str) -> float:
    return float(x.replace(" ", ""))


def _validate(p: Parsed) -> None:
    if p.lat is None or p.lon is None:
        return
    if not -90 <= p.lat <= 90:
        p.status = "invalid_coordinate_needs_review"
        p.flag("invalid_coordinate_needs_review", f"Latitude {p.lat} is outside -90..90; stored as printed, not corrected.")
    if not -180 <= p.lon <= 360:
        p.status = "invalid_coordinate_needs_review"
        p.flag("invalid_coordinate_needs_review", f"Longitude {p.lon} is outside the plausible range; stored as printed.")
    if re.search(r"-\s\d", p.raw_location or ""):
        p.notes.append("Source has a stray space after a minus sign; read as a negative number. Raw text preserved.")
        p.confidence = min(p.confidence, 0.9)


def classify(name: str | None) -> str | None:
    for cat, pat in CATEGORY_PATTERNS:
        if name and re.search(pat, name, re.I):
            return cat
    return None


def parse_catalogue(text: str) -> list[Parsed]:
    out: list[Parsed] = []
    page, section = 1, "Unsectioned"
    pending: list[Parsed] = []  # name-only lines awaiting a coordinate line (layout quirk in the Soviet section)

    def flush_pending() -> None:
        for q in pending:
            q.notes.append("No location printed for this entry in the catalogue.")
            out.append(q)
        pending.clear()

    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        m = PAGE_RE.match(s)
        if m:
            page = int(m.group(1)); continue
        if SECTION_RE.match(s):
            flush_pending(); section = s; continue
        am = APOLLO_RE.match(s)
        if am and ("Landing Location" in s or s == am.group(1)):
            flush_pending(); section = am.group(1)
            if "Landing Location" not in s:
                continue
            loc = s.split("Landing Location", 1)[1].lstrip(" :-")
            p = Parsed(section, page, f"{section} landing site", s, loc)
            c = COORD_RE.search(loc)
            if c:
                p.lat, p.lon, p.status = _f(c.group(1)), _f(c.group(2)), "coordinates_stated"
            _validate(p); out.append(p); continue
        c = COORD_RE.search(s)
        if c:
            name = s[: c.start()].strip(" -:") or None
            loc = s[c.start():]
            if name is None:
                if pending:
                    p = pending.pop()
                    p.raw_line, p.raw_location = f"{p.raw_line} / {s}", loc
                    p.flag("layout_inferred_association",
                           "Coordinates were on the line after the name in the extracted text; the association is inferred from layout. Verify against the PDF page.")
                    p.confidence = 0.5
                    if pending:
                        p.notes.append("Preceded by other unlabelled names: " + ", ".join(q.object_name or "?" for q in pending))
                else:
                    p = Parsed(section, page, None, s, loc)
                    p.flag("uncertain_mission_attribution", "Coordinates with no object name in extracted text.")
                    p.confidence = 0.3
                p.lat, p.lon, p.status = _f(c.group(1)), _f(c.group(2)), "coordinates_stated"
                _validate(p); flush_pending(); out.append(p); continue
            flush_pending()
            p = Parsed(section, page, re.sub(r"\s*\[\d+\]$", "", name), s, loc, _f(c.group(1)), _f(c.group(2)), "coordinates_stated")
            p.object_name = re.sub(r"\s*\(see [^)]*\)", "", p.object_name or "").strip() or None
            _validate(p); out.append(p); continue
        hit = next(((w, st) for w, st in STATUS_WORDS if s.endswith(w)), None)
        if hit and len(s) < 120:
            flush_pending()
            name = re.sub(r"\s*\[\d+\]\s*$", "", s[: -len(hit[0])].strip())
            out.append(Parsed(section, page, name, s, hit[0], status=hit[1]))
            continue
        reg = next((w for w in REGION_WORDS if w in s and len(s) < 80), None)
        if reg and "Experiment" not in s:
            flush_pending()
            name = s.split(reg)[0].strip(" (")
            p = Parsed(section, page, name or None, s, reg, status="region_only")
            p.flag("region_only", "Only a region is printed, not coordinates.")
            out.append(p); continue
        if section == "Soviet Material" and re.fullmatch(r"Luna \d+[A-Za-z ]*|Lunokhod \d", s):
            pending.append(Parsed(section, page, s, s, None))
    flush_pending()
    _postprocess(out)
    return out


def _postprocess(recs: list[Parsed]) -> None:
    seen: Counter = Counter()
    by_key: dict[tuple, list[Parsed]] = {}
    for p in recs:
        p.category = classify(p.object_name)
        if p.lat is None and p.status != "invalid_coordinate_needs_review":
            p.flag("missing_coordinates", f"No coordinates printed (status: {p.status}).")
        if p.object_name is None or len(p.object_name) < 3:
            p.flag("ambiguous_equipment_name", "Object name missing or too short to identify the equipment.")
        if p.section == "Unsectioned":
            p.flag("uncertain_mission_attribution", "Entry appears before any mission section header.")
        key = (p.section, p.object_name, p.raw_line)
        seen[key] += 1
        p.occurrence = seen[key]
        if p.occurrence > 1:
            p.flag("duplicate_in_source", "Identical entry printed more than once; every occurrence is kept as evidence.")
        by_key.setdefault((p.section, p.object_name), []).append(p)
    for group in by_key.values():
        coords = {(g.lat, g.lon) for g in group if g.lat is not None}
        if len(coords) > 1:
            for g in group:
                g.flag("conflicting_entry", "Same mission/object appears with different coordinates; compare all occurrences.")


def _hash(p: Parsed) -> str:
    return hashlib.sha256(f"{p.section}|{p.object_name}|{p.raw_line}".encode()).hexdigest()


def validate_format(parsed: list[Parsed]) -> None:
    sections = {p.section for p in parsed}
    if len(parsed) < 20 or len(sections) < 3:
        raise ValueError(f"Input does not look like the Moon catalogue: {len(parsed)} rows in {len(sections)} sections (expected at least 20 rows and 3 sections).")


def load(db: Session, source: DataSource, text: str, *, document_sha256: str, source_url: str | None = None,
         document_title: str | None = None, extractor: str = "page-delimited text input",
         triggered_by_id: int | None = None, retry_of_id: int | None = None) -> IngestionJob:
    now = datetime.now(timezone.utc)
    job = IngestionJob(data_source_id=source.id, started_at=now, document_sha256=document_sha256, source_url=source_url,
                       input_text=text, triggered_by_id=triggered_by_id, retry_of_id=retry_of_id, log=[], report={})
    db.add(job); db.flush()
    try:
        parsed = parse_catalogue(text)
        validate_format(parsed)
        job.records_seen = len(parsed)
        method = f"{extractor} + {PARSER}"
        flag_counts: Counter = Counter()
        for p in parsed:
            h = _hash(p)
            exists = db.scalar(select(CatalogueRecord.id).where(
                CatalogueRecord.data_source_id == source.id, CatalogueRecord.document_sha256 == document_sha256,
                CatalogueRecord.content_hash == h, CatalogueRecord.occurrence == p.occurrence))
            if exists:
                job.records_skipped_existing += 1; continue
            blocking = bool(set(p.flags) & BLOCKING_FLAGS)
            try:
                with db.begin_nested():
                    db.add(CatalogueRecord(
                        data_source_id=source.id, job_id=job.id, source_url=source_url, document_title=document_title or source.name,
                        document_sha256=document_sha256, source_page=p.page, destination="Moon", section=p.section,
                        object_name=p.object_name, equipment_category=p.category, raw_line=p.raw_line, raw_location=p.raw_location,
                        latitude_deg_n=p.lat, longitude_deg_e=p.lon, location_status=p.status, flags=p.flags,
                        validation_notes=p.notes, parsing_confidence=p.confidence, extraction_method=method,
                        content_hash=h, occurrence=p.occurrence, ingested_at=now,
                        review_status="needs_review" if blocking else "extracted"))
                    db.flush()
                job.records_created += 1
                job.records_flagged += int(blocking)
                flag_counts.update(p.flags)
            except Exception as e:  # one bad row must not lose the rest of the run
                job.records_failed += 1
                job.log.append(f"row failed ({p.section} / {p.object_name}, page {p.page}): {e!r}")
        job.status = "succeeded" if job.records_failed == 0 else "partial"
        job.report = {
            "document_sha256": document_sha256, "source_url": source_url, "extractor": extractor, "parser": PARSER,
            "pages": sorted({p.page for p in parsed}), "rows_parsed": len(parsed), "created": job.records_created,
            "skipped_existing": job.records_skipped_existing, "failed": job.records_failed, "flagged_for_review": job.records_flagged,
            "flags": dict(flag_counts), "by_section": dict(Counter(p.section for p in parsed)),
            "by_location_status": dict(Counter(p.status for p in parsed)),
            "not_ingested": "Per-item crew-equipment inventory lines and rows with no printed location text.",
        }
        source.last_retrieved_at = now
        if job.status == "succeeded":
            source.last_ingested_at = now
        source.integration_status = "partial"
        job.log.append(f"parsed {len(parsed)} rows; created {job.records_created}; skipped {job.records_skipped_existing}; flagged {job.records_flagged}")
    except Exception as e:
        job.status, job.error = "failed", f"{type(e).__name__}: {e}"
        job.log.append(f"job failed: {job.error}")
    finally:
        job.finished_at = datetime.now(timezone.utc)
    db.commit()
    return job


def render_report(job: IngestionJob) -> str:
    r = job.report or {}
    lines = [f"Ingestion job {job.id}: {job.status}", f"  document sha256: {job.document_sha256}", f"  source: {job.source_url}"]
    if job.error:
        lines.append(f"  error: {job.error}")
    for k in ("rows_parsed", "created", "skipped_existing", "failed", "flagged_for_review"):
        if k in r:
            lines.append(f"  {k}: {r[k]}")
    if r.get("flags"):
        lines.append("  flags: " + ", ".join(f"{k}={v}" for k, v in sorted(r["flags"].items())))
    if r.get("by_section"):
        lines.append("  rows by section: " + ", ".join(f"{k}={v}" for k, v in r["by_section"].items()))
    lines += [f"  log: {l}" for l in job.log]
    return "\n".join(lines)
