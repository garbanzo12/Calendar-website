from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_task_google_event_id_column() -> None:
    """Backfill the tasks schema for environments created before this column existed."""
    inspector = inspect(engine)
    task_columns = {column["name"] for column in inspector.get_columns("tasks")}
    if "google_event_id" in task_columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE tasks ADD COLUMN google_event_id VARCHAR(255)"))
