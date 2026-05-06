import re
from datetime import datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.schemas import ChatResponse, TaskCreate
from app.services.task_service import TaskService


DAY_MAP_EN = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

DAY_MAP_ES = {
    "lunes": 0, "lun": 0,
    "martes": 1, "mar": 1,
    "miercoles": 2, "mié": 2, "mie": 2,
    "jueves": 3, "jue": 3,
    "viernes": 4, "vie": 4,
    "sabado": 5, "sáb": 5, "sab": 5,
    "domingo": 6, "dom": 6,
}

MONTH_MAP_EN = {
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

MONTH_MAP_ES = {
    "enero": 1, "ene": 1,
    "febrero": 2, "feb": 2,
    "marzo": 3,
    "abril": 4, "abr": 4,
    "mayo": 5,
    "junio": 6, "jun": 6,
    "julio": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "septiembre": 9, "sep": 9, "septiembre": 9,
    "octubre": 10, "oct": 10,
    "noviembre": 11, "nov": 11,
    "diciembre": 12, "dic": 12,
}

TIME_CONTEXT = {
    "breakfast": time(9, 0),
    "desayuno": time(9, 0),
    "almuerzo": time(13, 0),
    "lunch": time(13, 0),
    "cena": time(19, 0),
    "dinner": time(19, 0),
    "comida": time(13, 0),
    "reunion": time(10, 0),
    "meeting": time(10, 0),
    "cita": time(10, 0),
    "appointment": time(10, 0),
    "llamada": time(10, 0),
    "call": time(10, 0),
    "gym": time(7, 0),
    "ejercicio": time(7, 0),
    "exercise": time(7, 0),
    "clase": time(9, 0),
    "class": time(9, 0),
    "trabajo": time(9, 0),
    "work": time(9, 0),
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
        
        target_time = ChatService._extract_time(remaining or message, target_date, base_date)
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
        
        tomorrow_patterns = [
            r"\bmañana\b", r"\btomorrow\b", r"\bmanana\b"
        ]
        for pattern in tomorrow_patterns:
            if re.search(pattern, lowered):
                target = base_date + timedelta(days=1)
                remaining = re.sub(pattern, "", lowered, flags=re.IGNORECASE)
                return target, remaining
        
        today_patterns = [r"\bhoy\b", r"\btoday\b"]
        for pattern in today_patterns:
            if re.search(pattern, lowered):
                target = base_date
                remaining = re.sub(pattern, "", lowered, flags=re.IGNORECASE)
                return target, remaining
        
        for day_name, day_offset in {**DAY_MAP_EN, **DAY_MAP_ES}.items():
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
        
        for month_name, month_num in {**MONTH_MAP_EN, **MONTH_MAP_ES}.items():
            patterns = [
                rf"\b{month_name}\s+(\d{{1,2}})\b",
                rf"\b(\d{{1,2}})\s+de\s+{month_name}\b",
                rf"\b{month_name}\s+(\d{{1,2}})(?:st|nd|rd|th)?\b",
            ]
            for pattern in patterns:
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
        
        in_days_match = re.search(r"\bin\s+(\d+)\s+(day|days|semana|semanas|week|weeks)\b", lowered)
        if in_days_match:
            num = int(in_days_match.group(1))
            unit = in_days_match.group(2)
            if any(w in unit for w in ["semana", "week"]):
                target = base_date + timedelta(weeks=num)
            else:
                target = base_date + timedelta(days=num)
            remaining = re.sub(r"\bin\s+\d+\s+(day|days|semana|semanas|week|weeks)\b", "", lowered, flags=re.IGNORECASE)
            return target, remaining
        
        next_week_match = re.search(r"\bnext\s+week\b", lowered)
        if next_week_match:
            target = base_date + timedelta(weeks=1)
            remaining = re.sub(r"\bnext\s+week\b", "", lowered, flags=re.IGNORECASE)
            return target, remaining
        
        return base_date, remaining

    @staticmethod
    def _extract_time(message: str, target_date: datetime, base_date: datetime) -> time:
        lowered = message.lower()
        
        time_patterns = [
            (r"\b(\d{1,2}):(\d{2})\s*(am|pm)\b", True),
            (r"\b(\d{1,2})\s*(am|pm)\b", True),
            (r"\b(\d{1,2}):(\d{2})\b", False),
            (r"\bnoon\b", None),
            (r"\bmidnight\b", None),
            (r"\bmediodia\b", None),
            (r"\bmedianoche\b", None),
            (r"\bde\s+la\s+manana\b", None),
            (r"\bde\s+la\s+tarde\b", None),
            (r"\bde\s+la\s+noche\b", None),
            (r"\bla\s+(manana|tarde|noche)\b", None),
        ]
        
        for pattern, _ in time_patterns:
            match = re.search(pattern, lowered)
            if match:
                if pattern == r"\bnoon\b" or pattern == r"\bmediodia\b":
                    return time(hour=12, minute=0)
                if pattern == r"\bmidnight\b" or pattern == r"\bmedianoche\b":
                    return time(hour=0, minute=0)
                if pattern == r"\bde\s+la\s+manana\b" or pattern == r"\bla\s+manana\b":
                    return time(hour=9, minute=0)
                if pattern == r"\bde\s+la\s+tarde\b" or pattern == r"\bla\s+tarde\b":
                    return time(hour=15, minute=0)
                if pattern == r"\bde\s+la\s+noche\b" or pattern == r"\bla\s+noche\b":
                    return time(hour=20, minute=0)
                
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.lastindex >= 2 else 0
                
                if "pm" in lowered[match.start():match.end()] and hour != 12:
                    hour += 12
                if "am" in lowered[match.start():match.end()] and hour == 12:
                    hour = 0
                
                return time(hour=hour % 24, minute=minute)
        
        for keyword, default_time in TIME_CONTEXT.items():
            if keyword in lowered:
                return default_time
        
        return time(hour=9, minute=0)

    @staticmethod
    def _extract_title(message: str) -> str:
        cleaned = message
        
        remove_patterns = [
            r"\b(mañana|tomorrow|manana|hoy|today|this\s+\w+|next\s+\w+)\b",
            r"\b(lunes|martes|miercoles|jueves|viernes|sabado|domingo|monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun|lun|mar|mie|jue|vie|sab|dom)\b",
            r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b",
            r"\b\d{1,2}\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b",
            r"\bin\s+\d+\s+(day|days|semana|semanas|week|weeks)\b",
            r"\bat\s+\d{1,2}(?::\d{2})?\s*(am|pm)?\b",
            r"\ba\s+las\s+\d{1,2}(?::\d{2})?\s*(am|pm)?\b",
            r"\bpor\s+la\s+(manana|tarde|noche)\b",
            r"\bde\s+la\s+(manana|tarde|noche)\b",
            r"\b(schedule|add|create|set up|book|plan|安排|添加|创建|agendar|programar|reservar|crear)\b",
            r"\b(please|can you|could you|will you|would you|por favor|podrías|puedes)\b",
            r"\b(a|an|the|un|una|el|la)\b",
            r"\s+",
        ]
        
        for pattern in remove_patterns:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
        
        cleaned = re.sub(r"\bdavid\b", "David", cleaned, flags=re.IGNORECASE)
        
        cleaned = cleaned.strip(" .,-_():;!?¿¡'\"")
        
        words = cleaned.split()
        if len(words) > 12:
            cleaned = " ".join(words[:12])
        
        result = cleaned[:200].strip()
        return result if result else ""