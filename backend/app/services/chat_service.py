import re
from datetime import datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.schemas import ChatResponse, TaskCreate
from app.services.task_service import TaskService


class ChatService:
    @staticmethod
    async def process_message(db: Session, user: User, message: str) -> ChatResponse:
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

        return ChatResponse(
            parsed_title=parsed["title"],
            parsed_date=parsed["date"],
            task=task,
            message=f'Task "{parsed["title"]}" scheduled for {parsed["date"].isoformat()}',
        )

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
        parsed_datetime = datetime.combine(target_date, time(hour=hour, minute=minute))
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
