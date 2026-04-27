from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
_pgvector_enabled = False


def set_pgvector_enabled(value: bool) -> None:
    global _pgvector_enabled
    _pgvector_enabled = value


def is_pgvector_enabled() -> bool:
    return _pgvector_enabled


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
