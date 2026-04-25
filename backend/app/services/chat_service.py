import logging
import re
import time
from datetime import datetime, time as datetime_time, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import ChatMessage, User
from app.db.schemas import ChatResponse, TaskCreate
from app.services.task_service import TaskService

logger = logging.getLogger("api")


class ChatService:
    @staticmethod
    async def get_history(db: Session, user: User, limit: int = 50) -> list[ChatMessage]:
        return db.query(ChatMessage).filter(ChatMessage.user_id == user.id).order_by(ChatMessage.created_at.asc()).limit(limit).all()

    @staticmethod
    async def process_message(db: Session, user: User, message: str) -> ChatResponse:
        start_time = time.time()
        
        user_msg = ChatMessage(user_id=user.id, role="user", content=message)
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        logger.info(f"[CHAT MESSAGE] user_id={user.id} role=user saved")

        try:
            parsed = ChatService._parse_message(message)
            task = await TaskService.create_task(
                db,
                user,
                TaskCreate(
                    title=parsed["title"],
                    description=message,
                    date=parsed["date"],
                ),
            )
            
            system_message_content = f'Task "{parsed["title"]}" scheduled for {parsed["date"].isoformat()}'
            assistant_msg = ChatMessage(user_id=user.id, role="assistant", content=system_message_content)
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)
            
            process_time = int((time.time() - start_time) * 1000)
            logger.info(f"[CHAT RESPONSE] user_id={user.id} generated in {process_time}ms")
            
            return ChatResponse(
                parsed_title=parsed["title"],
                parsed_date=parsed["date"],
                task=task,
                message=system_message_content,
                messages=[user_msg, assistant_msg]
            )
            
        except HTTPException as e:
            assistant_msg = ChatMessage(user_id=user.id, role="assistant", content=e.detail)
            db.add(assistant_msg)
            db.commit()
            
            process_time = int((time.time() - start_time) * 1000)
            logger.info(f"[CHAT RESPONSE] user_id={user.id} generated in {process_time}ms (error)")
            
            raise e

    @staticmethod
    def _parse_message(message: str) -> dict:
        lowered = message.lower().strip()
        base_date = datetime.now()
        target_date = base_date.date()

        if "tomorrow" in lowered:
            target_date = (base_date + timedelta(days=1)).date()
        elif "today" in lowered:
            target_date = base_date.date()

        hour, minute = ChatService._extract_time(lowered)
        parsed_datetime = datetime.combine(target_date, datetime_time(hour=hour, minute=minute))
        title = ChatService._extract_title(message)

        if not title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not infer a task title from the message",
            )

        return {"title": title, "date": parsed_datetime}

    @staticmethod
    def _extract_time(message: str) -> tuple[int, int]:
        match = re.search(r"\b(?:at\s*)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", message)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            meridiem = match.group(3)

            if meridiem == "pm" and hour != 12:
                hour += 12
            if meridiem == "am" and hour == 12:
                hour = 0
            return hour, minute

        match_24h = re.search(r"\b(?:at\s*)?(\d{1,2}):(\d{2})\b", message)
        if match_24h:
            return int(match_24h.group(1)), int(match_24h.group(2))

        return 9, 0

    @staticmethod
    def _extract_title(message: str) -> str:
        cleaned = re.sub(r"\b(today|tomorrow)\b", "", message, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bat\s*\d{1,2}(?::\d{2})?\s*(am|pm)?\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"\b(schedule|add|create|set up|book|plan|a|an|the)\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")
        return cleaned[:255]
