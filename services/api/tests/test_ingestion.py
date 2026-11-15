import hashlib
import io
from pathlib import Path

import pytest
from fpdf import FPDF
from sqlalchemy import func, select

from app.ingestion import moon_catalogue as mc
from app.ingestion import pdf as pdfmod
from app.ingestion.service import run_moon_catalogue
from app.models.nasa import CatalogueRecord, IngestionJob
from tests.conftest import TEXT

SHA = hashlib.sha256(TEXT.encode()).hexdigest()
DEJAVU = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def make_pdf(text: str) -> bytes:
    """Build a real multi-page PDF from page-delimited text (one PDF page per marker)."""
    pdf = FPDF(); pdf.add_font("dv", fname=str(DEJAVU)); pdf.set_font("dv", size=9)
    for chunk in text.split("=== PAGE ")[1:]:
        pdf.add_page()
        for line in chunk.split("\n")[1:]:
            pdf.cell(0, 4, line, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def count(db):
    return db.scalar(select(func.count()).select_from(CatalogueRecord))


def test_load_stores_provenance_for_every_record(env, source):
    db, _ = env
    job = mc.load(db, source, TEXT, document_sha256=SHA, source_url=source.official_url, document_title="Catalogue")
    assert job.status == "succeeded" and job.records_created > 60 and job.records_failed == 0
    r = db.scalars(select(CatalogueRecord).where(CatalogueRecord.object_name == "Surveyor 3")).one()
    assert (r.document_sha256, r.source_url, r.source_page, r.document_title) == (SHA, source.official_url, 1, "Catalogue")
    assert r.raw_line and r.extraction_method.endswith(mc.PARSER) and r.ingested_at and r.job_id == job.id
    assert r.review_status == "extracted"
    ranger9 = db.scalars(select(CatalogueRecord).where(CatalogueRecord.object_name == "Ranger 9")).one()
    assert ranger9.review_status == "needs_review" and ranger9.latitude_deg_n == 112.828


def test_ingestion_is_idempotent(env, source):
    db, _ = env
    j1 = mc.load(db, source, TEXT, document_sha256=SHA)
    n = count(db)
    j2 = mc.load(db, source, TEXT, document_sha256=SHA)
    assert j2.records_created == 0 and j2.records_skipped_existing == j1.records_created and count(db) == n
    assert source.last_ingested_at is not None and source.integration_status == "partial"


def test_new_document_checksum_creates_a_separate_versioned_set_and_keeps_old(env, source):
    db, _ = env
    mc.load(db, source, TEXT, document_sha256=SHA); n = count(db)
    mc.load(db, source, TEXT, document_sha256="f" * 64)
    assert count(db) == 2 * n


def test_duplicates_kept_as_evidence_and_idempotent(env, source):
    db, _ = env
    line = "Surveyor 1 -2.474 ˚ N, -43.339 ˚ E"
    text = TEXT.replace(line, line + "\n" + line, 1)
    j = mc.load(db, source, text, document_sha256="a" * 64)
    rows = db.scalars(select(CatalogueRecord).where(CatalogueRecord.object_name == "Surveyor 1").order_by(CatalogueRecord.occurrence)).all()
    assert [r.occurrence for r in rows] == [1, 2] and "duplicate_in_source" in rows[1].flags and rows[1].review_status == "needs_review"
    assert mc.load(db, source, text, document_sha256="a" * 64).records_created == 0
    assert j.report["flags"]["duplicate_in_source"] == 1


def test_non_catalogue_input_fails_cleanly_and_stores_nothing(env, source):
    db, _ = env
    job = mc.load(db, source, "=== PAGE 1 ===\nHello world\nnothing here\n", document_sha256="b" * 64)
    assert job.status == "failed" and "does not look like" in job.error and count(db) == 0 and source.last_ingested_at is None


def test_one_bad_row_makes_job_partial_not_lost(env, source, monkeypatch):
    db, _ = env
    orig = mc._hash
    monkeypatch.setattr(mc, "_hash", lambda p: None if p.object_name == "Surveyor 2" else orig(p))  # NOT NULL violation
    job = mc.load(db, source, TEXT, document_sha256=SHA)
    assert job.status == "partial" and job.records_failed == 1 and job.records_created > 60
    assert any("Surveyor 2" in l for l in job.log) and source.last_ingested_at is None


def test_report_contents(env, source):
    db, _ = env
    job = mc.load(db, source, TEXT, document_sha256=SHA, source_url=source.official_url)
    rep = job.report
    assert rep["flags"]["invalid_coordinate_needs_review"] == 1 and rep["flags"]["layout_inferred_association"] == 2
    assert rep["by_section"]["Apollo 14"] >= 5 and "Per-item" in rep["not_ingested"]
    assert "Ingestion job" in mc.render_report(job)


# ---- service: download validation, failure handling, retry ----

def test_download_rejects_non_nasa_hosts_and_http():
    for url in ("https://example.com/x.pdf", "http://www.nasa.gov/x.pdf", "https://nasa.gov.evil.com/x.pdf"):
        with pytest.raises(pdfmod.PdfError):
            pdfmod.assert_allowed_url(url)
    pdfmod.assert_allowed_url("https://www.nasa.gov/wp-content/uploads/x.pdf")


def test_validate_pdf_rejects_wrong_type_and_header():
    with pytest.raises(pdfmod.PdfError): pdfmod.validate_pdf(b"%PDF-1.4", "text/html")
    with pytest.raises(pdfmod.PdfError): pdfmod.validate_pdf(b"<html>", "application/pdf")
    pdfmod.validate_pdf(b"%PDF-1.4 ...", "application/pdf")


class _Resp(io.BytesIO):
    def __init__(self, data, ctype): super().__init__(data); self.headers = {"Content-Type": ctype}
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_download_does_not_retry_a_wrong_file_but_retries_network_errors(monkeypatch):
    monkeypatch.setattr(pdfmod.time, "sleep", lambda s: None)
    calls = {"n": 0}
    def html(req, timeout): calls["n"] += 1; return _Resp(b"<html>", "text/html")
    with pytest.raises(pdfmod.PdfError): pdfmod.download("https://www.nasa.gov/a.pdf", opener=html)
    assert calls["n"] == 1
    flaky = {"n": 0}
    def sometimes(req, timeout):
        flaky["n"] += 1
        if flaky["n"] < 3: raise OSError("boom")
        return _Resp(b"%PDF-1.4 x", "application/pdf")
    data, _ = pdfmod.download("https://www.nasa.gov/a.pdf", opener=sometimes)
    assert flaky["n"] == 3 and data.startswith(b"%PDF")


@pytest.mark.skipif(not DEJAVU.exists(), reason="DejaVu font needed to build the test PDF")
def test_real_pdf_end_to_end_through_pdftotext_and_parser(env, source, tmp_path):
    """A real generated PDF (not NASA's) exercises download-free extraction, checksum, page numbers and parsing."""
    db, _ = env
    data = make_pdf(TEXT); p = tmp_path / "c.pdf"; p.write_bytes(data)
    job = run_moon_catalogue(db, source, pdf_path=str(p))
    assert job.status == "succeeded" and job.document_sha256 == hashlib.sha256(data).hexdigest()
    r = db.scalars(select(CatalogueRecord).where(CatalogueRecord.object_name == "Surveyor 7")).one()
    assert (r.latitude_deg_n, r.longitude_deg_e, r.source_page) == (-40.98, -11.509, 1)
    assert db.scalars(select(CatalogueRecord).where(CatalogueRecord.object_name == "Ranger 9")).one().location_status == "invalid_coordinate_needs_review"
    assert "pdftotext" in job.report["extractor"] or job.report["extractor"] == "pypdf"
    again = run_moon_catalogue(db, source, pdf_path=str(p))
    assert again.records_created == 0


def test_download_failure_is_logged_and_retry_uses_stored_input(env, source, monkeypatch):
    db, _ = env
    def boom(url): raise pdfmod.PdfError("network down")
    failed = run_moon_catalogue(db, source, fetch=boom)
    assert failed.status == "failed" and "network down" in failed.error and count(db) == 0
    # a job that failed *after* extraction keeps its input, so a retry needs no network
    bad = mc.load(db, source, TEXT, document_sha256=SHA)
    bad.status = "partial"; db.commit()
    retry = run_moon_catalogue(db, source, retry_of=bad, fetch=boom)
    assert retry.retry_of_id == bad.id and retry.status == "succeeded" and retry.records_created == 0  # all already stored
    assert db.scalar(select(func.count()).select_from(IngestionJob)) == 3
