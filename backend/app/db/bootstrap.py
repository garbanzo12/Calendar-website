import logging

from sqlalchemy import text

from app.core.config import settings
from app.db.database import Base, engine, set_pgvector_enabled

logger = logging.getLogger("api")


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMP"))
        conn.execute(text("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS embedding JSONB"))
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_chat_messages_user_created_at
                ON chat_messages (user_id, created_at DESC)
                """
            )
        )

    pgvector_enabled = False
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(
                text(
                    f"""
                    ALTER TABLE chat_messages
                    ADD COLUMN IF NOT EXISTS embedding_vector vector({settings.embedding_dimensions})
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_chat_messages_embedding_vector
                    ON chat_messages
                    USING ivfflat (embedding_vector vector_cosine_ops)
                    WITH (lists = 100)
                    """
                )
            )
            pgvector_enabled = True
    except Exception as exc:
        logger.warning(f"[DB] pgvector unavailable, using JSON fallback: {exc}")

    set_pgvector_enabled(pgvector_enabled)
    logger.info(f"[DB] initialized pgvector_enabled={pgvector_enabled}")
