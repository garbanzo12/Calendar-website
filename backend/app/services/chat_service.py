import re
from datetime import datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.schemas import ChatResponse, TaskCreate
from app.services.task_service import TaskService


DAY_MAP = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


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
            message=f'Task "{parsed["title"]}" scheduled for {parsed["date"].strftime("%A, %B %d at %I:%M %p")}',
        )

    @staticmethod
    def _parse_message(message: str) -> dict:
        base_date = datetime.now()
        target_date, remaining = ChatService._extract_date(message, base_date)
        
        target_time = ChatService._extract_time(remaining or message, base_date)
        final_datetime = datetime.combine(target_date.date(), target_time)
        
        if final_datetime < base_date:
            final_datetime = final_datetime + timedelta(days=1)
        
        title = ChatService._extract_title(message)
        
        if not title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not infer a task title from the message",
            )

        return {"title": title, "date": final_datetime}

    @staticmethod
    def _extract_date(message: str, base_date: datetime) -> tuple[datetime, str]:
        lowered = message.lower()
        remaining = message
        
        if "tomorrow" in lowered:
            target = base_date + timedelta(days=1)
            remaining = re.sub(r"\btomorrow\b", "", lowered, flags=re.IGNORECASE)
            return target, remaining
        
        if "today" in lowered:
            target = base_date
            remaining = re.sub(r"\btoday\b", "", lowered, flags=re.IGNORECASE)
            return target, remaining
        
        for day_name, day_offset in DAY_MAP.items():
            pattern = rf"\b(this\s+)?{day_name}\b"
            match = re.search(pattern, lowered)
            if match:
                current_day = base_date.weekday()
                days_until = (day_offset - current_day) % 7
                if days_until == 0:
                    days_until = 7
                target = base_date + timedelta(days=days_until)
                remaining = re.sub(pattern, "", lowered, flags=re.IGNORECASE)
                return target, remaining
        
        for month_name, month_num in MONTH_MAP.items():
            pattern = rf"\b{month_name}\s+(\d{{1,2}})(?:st|nd|rd|th)?\b"
            match = re.search(pattern, lowered)
            if match:
                day = int(match.group(1))
                try:
                    target = base_date.replace(month=month_num, day=day)
                    if target < base_date:
                        target = target.replace(year=target.year + 1)
                    remaining = re.sub(pattern, "", lowered, flags=re.IGNORECASE)
                    return target, remaining
                except ValueError:
                    pass
        
        in_days_match = re.search(r"\bin\s+(\d+)\s+(day|days|week|weeks)\b", lowered)
        if in_days_match:
            num = int(in_days_match.group(1))
            unit = in_days_match.group(2)
            if "week" in unit:
                target = base_date + timedelta(weeks=num)
            else:
                target = base_date + timedelta(days=num)
            remaining = re.sub(r"\bin\s+\d+\s+(day|days|week|weeks)\b", "", lowered, flags=re.IGNORECASE)
            return target, remaining
        
        next_week_match = re.search(r"\bnext\s+week\b", lowered)
        if next_week_match:
            target = base_date + timedelta(weeks=1)
            remaining = re.sub(r"\bnext\s+week\b", "", lowered, flags=re.IGNORECASE)
            return target, remaining
        
        return base_date, remaining

    @staticmethod
    def _extract_time(message: str, base_date: datetime) -> time:
        lowered = message.lower()
        
        patterns = [
            (r"\b(\d{1,2}):(\d{2})\s*(am|pm)\b", True),
            (r"\b(\d{1,2})\s*(am|pm)\b", True),
            (r"\b(\d{1,2}):(\d{2})\b", False),
            (r"\bnoon\b", None),
            (r"\bmidnight\b", None),
        ]
        
        for pattern, has_meridiem in patterns:
            match = re.search(pattern, lowered)
            if match:
                if pattern == r"\bnoon\b":
                    return time(hour=12, minute=0)
                if pattern == r"\bmidnight\b":
                    return time(hour=0, minute=0)
                
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.lastindex >= 2 else 0
                
                if has_meridiem:
                    meridiem = match.group(3) if match.lastindex >= 3 else None
                    if meridiem == "pm" and hour != 12:
                        hour += 12
                    if meridiem == "am" and hour == 12:
                        hour = 0
                elif hour < 12 and hour >= 0:
                    pass
                elif 12 <= hour <= 23:
                    pass
                else:
                    pass
                
                return time(hour=hour % 24, minute=minute)
        
        return time(hour=9, minute=0)

    @staticmethod
    def _extract_title(message: str) -> str:
        cleaned = message
        
        remove_patterns = [
            r"\b(today|tomorrow|this\s+\w+|next\s+\w+)\b",
            r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\b",
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+\d{1,2}(?:st|nd|rd|th)?\b",
            r"\bin\s+\d+\s+(day|days|week|weeks)\b",
            r"\bat\s+\d{1,2}(?::\d{2})?\s*(am|pm)?\b",
            r"\bat\s+(noon|midnight)\b",
            r"\b(schedule|add|create|set up|book|plan|安排|添加|创建)\b",
            r"\b(please|can you|could you|will you|would you)\b",
            r"\b(a|an|the)\b",
            r"\s+",
        ]
        
        for pattern in remove_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        
        cleaned = cleaned.strip(" .,-_():;!?¿¡'\"")
        
        words = cleaned.split()
        if len(words) > 10:
            cleaned = " ".join(words[:10])
        
        return cleaned[:200] if cleaned else ""