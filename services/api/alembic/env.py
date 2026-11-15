import os

from alembic import context
from sqlalchemy import create_engine

from app.core.config import settings
from app.db.base import Base
from app import models  # noqa: F401

target_metadata = Base.metadata


def run_migrations_online():
    # ASTERA_MIGRATION_URL lets tests and the setup docs target a specific database.
    engine = create_engine(os.environ.get("ASTERA_MIGRATION_URL") or settings.database_url)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
