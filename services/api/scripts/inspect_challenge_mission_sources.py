"""Fetch registered challenge-listed NASA mission pages into provenance snapshots.

Run from services/api: python scripts/inspect_challenge_mission_sources.py
This does not create verified mission/artifact records; it creates reviewable source snapshots.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.db.session import SessionLocal
from app.ingestion.registry import seed_sources
from app.models.nasa import DataSource
from app.integrations.nasa.nssdca import fetch_mission_page

OUT = Path(__file__).resolve().parents[1] / "data" / "nasa_resource_snapshots"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        seed_sources(db)
        sources = db.scalars(select(DataSource).where(DataSource.challenge_listing_status == "listed_verified").order_by(DataSource.slug)).all()
        report = []
        for source in sources:
            row = {"slug": source.slug, "name": source.name, "url": source.official_url}
            try:
                snapshot = fetch_mission_page(source.official_url)
                payload = snapshot.__dict__
                path = OUT / f"{source.slug}.json"
                path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
                row.update({"status": "snapshot_saved", "snapshot": str(path.relative_to(OUT.parent)), "sha256": snapshot.sha256, "title": snapshot.page_title})
            except Exception as exc:
                row.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
            report.append(row)
            print(json.dumps(row, ensure_ascii=False))
        (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return 0 if all(r["status"] == "snapshot_saved" for r in report) else 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
