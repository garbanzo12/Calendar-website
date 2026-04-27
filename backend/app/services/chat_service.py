import logging
import math
import time
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import is_pgvector_enabled
from app.db.models import ChatMessage, User
from app.db.schemas import ChatResponse, TaskCreate
from app.services.openai_service import OpenAIService
from app.services.task_service import TaskService

logger = logging.getLogger("api")


class ChatService:
    @staticmethod
    async def get_history(db: Session, user: User, limit: int = 50) -> list[ChatMessage]:
        records = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == user.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(records))

    @staticmethod
    async def clear_history(db: Session, user: User) -> None:
        deleted = db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete()
        db.commit()
        logger.info(f"[CHAT MEMORY] user_id={user.id} cleared_messages={deleted}")

    @staticmethod
    async def process_message(db: Session, user: User, message: str) -> ChatResponse:
        started_at = time.perf_counter()
        trimmed_message = message.strip()
        if not trimmed_message:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Message cannot be empty",
            )

        user_embedding, _ = await ChatService._get_embedding_for_text(
            db=db,
            user_id=user.id,
            role="user",
            text=trimmed_message,
        )

        recent_messages = ChatService._get_recent_messages(db, user.id, settings.chat_recent_messages)
        relevant_messages, retrieval_strategy = ChatService._get_relevant_messages(
            db=db,
            user_id=user.id,
            query_embedding=user_embedding,
            limit=settings.chat_relevant_messages,
            excluded_ids={message.id for message in recent_messages},
        )
        logger.info(
            f"[CONTEXT] user_id={user.id} retrieved={len(relevant_messages)} "
            f"recent={len(recent_messages)} strategy={retrieval_strategy}"
        )

        user_msg = ChatService._save_message(
            db=db,
            user_id=user.id,
            role="user",
            content=trimmed_message,
            embedding=user_embedding,
        )

        task = None
        parsed_title = None
        parsed_date = None

        try:
            prompt = ChatService._build_prompt(
                user_message=trimmed_message,
                relevant_messages=relevant_messages,
                recent_messages=recent_messages,
            )
            ai_payload, usage = await OpenAIService.generate_chat_payload(prompt)
            logger.info(
                f"[AI RESPONSE] user_id={user.id} duration={usage.get('duration_ms', 0)}ms "
                f"tokens={usage.get('total_tokens', 'unknown')}"
            )

            assistant_message = ChatService._extract_reply(ai_payload)
            task_payload = (ai_payload.get("task") or {}) if isinstance(ai_payload, dict) else {}

            if task_payload.get("should_create"):
                parsed_title = (task_payload.get("title") or "").strip() or None
                parsed_date = ChatService._parse_task_datetime(task_payload.get("start_iso"))
                if not parsed_title or not parsed_date:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="I need a clearer title and date before I can schedule that task.",
                    )

                task = await TaskService.create_task(
                    db,
                    user,
                    TaskCreate(
                        title=parsed_title[:255],
                        description=task_payload.get("description") or trimmed_message,
                        date=parsed_date,
                    ),
                )

            assistant_embedding, _ = await ChatService._get_embedding_for_text(
                db=db,
                user_id=user.id,
                role="assistant",
                text=assistant_message,
            )
            assistant_msg = ChatService._save_message(
                db=db,
                user_id=user.id,
                role="assistant",
                content=assistant_message,
                embedding=assistant_embedding,
            )

            total_duration_ms = int((time.perf_counter() - started_at) * 1000)
            logger.info(f"[CHAT RESPONSE] user_id={user.id} completed in {total_duration_ms}ms")

            return ChatResponse(
                parsed_title=parsed_title,
                parsed_date=parsed_date,
                task=task,
                message=assistant_message,
                messages=[user_msg, assistant_msg],
            )

        except HTTPException as exc:
            if user_msg is not None:
                await ChatService._save_error_message(db, user.id, exc.detail)

            total_duration_ms = int((time.perf_counter() - started_at) * 1000)
            logger.info(f"[CHAT RESPONSE] user_id={user.id} completed in {total_duration_ms}ms (error)")
            raise

    @staticmethod
    async def _save_error_message(db: Session, user_id: int, content: str) -> None:
        if not isinstance(content, str) or not content.strip():
            return
        try:
            embedding, _ = await ChatService._get_embedding_for_text(
                db=db,
                user_id=user_id,
                role="assistant",
                text=content,
            )
            ChatService._save_message(
                db=db,
                user_id=user_id,
                role="assistant",
                content=content,
                embedding=embedding,
            )
        except Exception:
            logger.exception(f"[CHAT ERROR] user_id={user_id} failed to persist assistant error message")

    @staticmethod
    async def _get_embedding_for_text(
        db: Session,
        user_id: int,
        role: str,
        text: str,
    ) -> tuple[list[float], bool]:
        start_time = time.perf_counter()

        cached_message = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.user_id == user_id,
                ChatMessage.role == role,
                ChatMessage.content == text,
                ChatMessage.embedding.isnot(None),
            )
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        if cached_message and isinstance(cached_message.embedding, list):
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(f"[EMBEDDING] user_id={user_id} role={role} cache_hit=true duration={duration_ms}ms")
            return cached_message.embedding, True

        embedding = await OpenAIService.get_embedding(text)
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"[EMBEDDING] user_id={user_id} role={role} generated in {duration_ms}ms")
        return embedding, False

    @staticmethod
    def _get_recent_messages(db: Session, user_id: int, limit: int) -> list[ChatMessage]:
        records = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(records))

    @staticmethod
    def _get_relevant_messages(
        db: Session,
        user_id: int,
        query_embedding: list[float],
        limit: int,
        excluded_ids: set[int],
    ) -> tuple[list[ChatMessage], str]:
        if is_pgvector_enabled():
            messages = ChatService._get_relevant_messages_pgvector(
                db=db,
                user_id=user_id,
                query_embedding=query_embedding,
                limit=limit,
                excluded_ids=excluded_ids,
            )
            return messages, "pgvector"

        messages = ChatService._get_relevant_messages_fallback(
            db=db,
            user_id=user_id,
            query_embedding=query_embedding,
            limit=limit,
            excluded_ids=excluded_ids,
        )
        return messages, "json-cosine"

    @staticmethod
    def _get_relevant_messages_pgvector(
        db: Session,
        user_id: int,
        query_embedding: list[float],
        limit: int,
        excluded_ids: set[int],
    ) -> list[ChatMessage]:
        vector_literal = ChatService._vector_literal(query_embedding)
        raw_limit = max(limit + len(excluded_ids), limit)
        rows = db.execute(
            text(
                """
                SELECT id
                FROM chat_messages
                WHERE user_id = :user_id
                  AND embedding_vector IS NOT NULL
                ORDER BY embedding_vector <=> CAST(:embedding AS vector), created_at DESC
                LIMIT :limit
                """
            ),
            {
                "user_id": user_id,
                "embedding": vector_literal,
                "limit": raw_limit,
            },
        ).fetchall()

        ordered_ids = [row[0] for row in rows if row[0] not in excluded_ids][:limit]
        if not ordered_ids:
            return []

        records = db.query(ChatMessage).filter(ChatMessage.id.in_(ordered_ids)).all()
        record_map = {record.id: record for record in records}
        return [record_map[message_id] for message_id in ordered_ids if message_id in record_map]

    @staticmethod
    def _get_relevant_messages_fallback(
        db: Session,
        user_id: int,
        query_embedding: list[float],
        limit: int,
        excluded_ids: set[int],
    ) -> list[ChatMessage]:
        candidates = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == user_id, ChatMessage.embedding.isnot(None))
            .order_by(ChatMessage.created_at.desc())
            .limit(settings.chat_retrieval_scan_limit)
            .all()
        )

        scored: list[tuple[float, ChatMessage]] = []
        for candidate in candidates:
            if candidate.id in excluded_ids or not isinstance(candidate.embedding, list):
                continue
            similarity = ChatService._cosine_similarity(query_embedding, candidate.embedding)
            if similarity > 0:
                scored.append((similarity, candidate))

        scored.sort(key=lambda item: item[0], reverse=True)
        top_messages = [message for _, message in scored[:limit]]
        return sorted(top_messages, key=lambda message: message.created_at)

    @staticmethod
    def _build_prompt(
        user_message: str,
        relevant_messages: list[ChatMessage],
        recent_messages: list[ChatMessage],
    ) -> str:
        relevant_lines = ChatService._format_messages(relevant_messages)
        recent_lines = ChatService._format_messages(recent_messages)

        while len(relevant_lines) + len(recent_lines) > settings.chat_max_context_chars and relevant_messages:
            relevant_messages = relevant_messages[1:]
            relevant_lines = ChatService._format_messages(relevant_messages)

        while len(relevant_lines) + len(recent_lines) > settings.chat_max_context_chars and recent_messages:
            recent_messages = recent_messages[1:]
            recent_lines = ChatService._format_messages(recent_messages)

        now = datetime.now(timezone.utc).isoformat()
        return (
            "SYSTEM:\n"
            "You are a helpful assistant that remembers the user's context.\n\n"
            "CONTEXT:\n"
            f"{relevant_lines or '(no relevant semantic memory)'}\n\n"
            "RECENT:\n"
            f"{recent_lines or '(no recent chat history)'}\n\n"
            "CURRENT_TIME_UTC:\n"
            f"{now}\n\n"
            "USER:\n"
            f"{user_message}"
        )

    @staticmethod
    def _format_messages(messages: list[ChatMessage]) -> str:
        formatted: list[str] = []
        for message in messages:
            content = (message.content or "").strip().replace("\n", " ")
            if len(content) > 450:
                content = f"{content[:447]}..."
            timestamp = message.created_at.isoformat(timespec="minutes")
            formatted.append(f"[{timestamp}] {message.role.upper()}: {content}")
        return "\n".join(formatted)

    @staticmethod
    def _extract_reply(payload: dict) -> str:
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Model returned an unexpected payload",
            )

        reply = payload.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Model did not return a valid reply",
            )
        return reply.strip()

    @staticmethod
    def _parse_task_datetime(raw_value: str | None) -> datetime | None:
        if not raw_value:
            return None

        try:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="I could not understand the requested task date.",
            ) from exc

        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    @staticmethod
    def _save_message(
        db: Session,
        user_id: int,
        role: str,
        content: str,
        embedding: list[float],
    ) -> ChatMessage:
        message = ChatMessage(
            user_id=user_id,
            role=role,
            content=content,
            embedding=embedding,
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        if is_pgvector_enabled():
            db.execute(
                text(
                    """
                    UPDATE chat_messages
                    SET embedding_vector = CAST(:embedding AS vector)
                    WHERE id = :message_id
                    """
                ),
                {
                    "embedding": ChatService._vector_literal(embedding),
                    "message_id": message.id,
                },
            )
            db.commit()
            db.refresh(message)

        logger.info(f"[CHAT MESSAGE] user_id={user_id} role={role} saved")
        return message

    @staticmethod
    def _vector_literal(values: list[float]) -> str:
        return "[" + ",".join(f"{value:.12f}" for value in values) + "]"

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if len(left) != len(right):
            return 0.0

        dot_product = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot_product / (left_norm * right_norm)
