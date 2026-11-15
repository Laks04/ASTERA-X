from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/live")
def live():
    """Process liveness; does not depend on the database."""
    return {"status": "ok", "service": "astera-api"}


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Readiness check used by the web client and Docker Compose."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "up"}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail={"status": "degraded", "database": "down"})
