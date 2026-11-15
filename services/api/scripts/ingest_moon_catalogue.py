"""Ingest the NASA History 'Catalogue of Manmade Material on the Moon'.

  python scripts/ingest_moon_catalogue.py                      # download the registered NASA URL (needs network + pdftotext or pypdf)
  python scripts/ingest_moon_catalogue.py --pdf path/to.pdf    # use a locally supplied PDF
  python scripts/ingest_moon_catalogue.py --retry JOB_ID       # re-run a failed/partial job from its stored input
Prints a report; exit code 1 if the job failed.
"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.ingestion.moon_catalogue import render_report  # noqa: E402
from app.ingestion.registry import MOON_CATALOGUE_SLUG, seed_sources  # noqa: E402
from app.ingestion.service import run_moon_catalogue  # noqa: E402
from app.models.nasa import DataSource, IngestionJob  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--pdf"); ap.add_argument("--retry", type=int)
    a = ap.parse_args()
    db = SessionLocal(); seed_sources(db)
    src = db.scalar(select(DataSource).where(DataSource.slug == MOON_CATALOGUE_SLUG))
    prev = db.get(IngestionJob, a.retry) if a.retry else None
    job = run_moon_catalogue(db, src, retry_of=prev, pdf_path=a.pdf)
    print(render_report(job))
    sys.exit(0 if job.status in ("succeeded", "partial") else 1)
