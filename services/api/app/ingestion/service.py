"""Orchestrates one ingestion run: obtain the document, record the job, load, retry."""
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.ingestion import moon_catalogue as mc
from app.ingestion import pdf
from app.models.nasa import DataSource, IngestionJob

ADAPTERS = {"nasa-history-moon-catalogue"}  # slugs that have a working adapter


def _failed_job(db: Session, source: DataSource, err: str, user_id, retry_of_id, url) -> IngestionJob:
    now = datetime.now(timezone.utc)
    job = IngestionJob(data_source_id=source.id, started_at=now, finished_at=now, status="failed", error=err,
                       source_url=url, triggered_by_id=user_id, retry_of_id=retry_of_id, log=[f"job failed: {err}"], report={})
    db.add(job); db.commit()
    return job


def run_moon_catalogue(db: Session, source: DataSource, *, user_id: int | None = None, retry_of: IngestionJob | None = None,
                       pdf_path: str | None = None, fetch=pdf.download) -> IngestionJob:
    """Ingest from a local PDF, from the stored input of a previous job (retry), or by downloading the registered URL."""
    url = source.official_url
    try:
        if retry_of is not None and retry_of.input_text:
            text, sha, extractor = retry_of.input_text, retry_of.document_sha256, "stored input of earlier job"
        else:
            if pdf_path:
                data = Path(pdf_path).read_bytes(); pdf.validate_pdf(data)
            else:
                data, _ = fetch(url)
            sha = pdf.sha256(data)
            text, extractor = pdf.extract_pages(data)
    except Exception as e:
        return _failed_job(db, source, f"{type(e).__name__}: {e}", user_id, retry_of.id if retry_of else None, url)
    return mc.load(db, source, text, document_sha256=sha, source_url=url, document_title="Catalogue of Manmade Material on the Moon",
                   extractor=extractor, triggered_by_id=user_id, retry_of_id=retry_of.id if retry_of else None)
