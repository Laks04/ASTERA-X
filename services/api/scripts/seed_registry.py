"""Idempotently seed ASTERA's curated NASA source registry."""
from app.db.session import SessionLocal
from app.ingestion.registry import seed_sources


def main() -> None:
    db = SessionLocal()
    try:
        seed_sources(db)
        print("ASTERA source registry is ready.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
