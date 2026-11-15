import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import archive, auth, data, health, verification
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="ASTERA — a source-aware archive and learning API for the legacy of space exploration hardware.",
    docs_url="/docs",
    redoc_url="/redoc",
)
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(archive.router, prefix="/api/v1", tags=["mission-and-artifact-archive"])
app.include_router(data.router, prefix="/api/v1", tags=["data-sources-and-ingestion"])
app.include_router(verification.router, prefix="/api/v1", tags=["human-verification"])


@app.get("/", tags=["service"])
def root():
    return {"name": settings.app_name, "version": app.version, "docs": "/docs", "health": "/api/v1/health"}
