import logging
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import Task, User
from app.db.schemas import TaskCreate, TaskUpdate
from app.services.google_calendar_service import GoogleCalendarService

logger = logging.getLogger(__name__)


class TaskService:
    @staticmethod
    async def create_task(db: Session, user: User, payload: TaskCreate) -> Task:
        task = Task(
            user_id=user.id,
            title=payload.title,
            description=payload.description,
            date=payload.date,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        try:
            event = await GoogleCalendarService.create_event(
                db=db,
                user_id=user.id,
                summary=task.title,
                description=task.description,
                start=task.date,
                end=task.date + timedelta(hours=1),
            )
            task.google_event_id = event["id"]
            db.commit()
            db.refresh(task)
        except Exception:
            db.rollback()

        return task

    @staticmethod
    def list_tasks(db: Session, user_id: int) -> list[Task]:
        return db.query(Task).filter(Task.user_id == user_id).order_by(Task.date.asc()).all()

    @staticmethod
    def sync_tasks_from_google_calendar(db: Session, user: User) -> dict[str, int]:
        events = GoogleCalendarService.list_events(db, user.id)
        print("EVENTS FROM GOOGLE:", events)
        
        imported = 0
        skipped = 0

        for event in events:
            event_id = event.get("id")
            start_data = event.get("start", {})
            start_value = start_data.get("dateTime") or start_data.get("date")

            if not event_id or not start_value:
                skipped += 1
                continue

            existing = (
                db.query(Task)
                .filter(Task.user_id == user.id, Task.google_event_id == event_id)
                .first()
            )
            if existing:
                skipped += 1
                continue

            task = Task(
                user_id=user.id,
                title=event.get("summary") or "(Untitled event)",
                description=event.get("description"),
                date=TaskService._parse_google_start(start_value),
                google_event_id=event_id,
            )
            db.add(task)
            imported += 1
            logger.info("Imported event %s", event_id)

        db.commit()
        return {"imported": imported, "skipped": skipped}

    @staticmethod
    async def update_task(db: Session, user: User, task_id: int, payload: TaskUpdate) -> Task | None:
        task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
        if not task:
            return None

        if payload.title is not None:
            task.title = payload.title
        if payload.description is not None:
            task.description = payload.description
        if payload.date is not None:
            task.date = payload.date

        db.commit()
        db.refresh(task)

        if task.google_event_id:
            try:
                await GoogleCalendarService.update_event(
                    db,
                    user.id,
                    task.google_event_id,
                    type(
                        "TaskCalendarUpdate",
                        (),
                        {
                            "summary": task.title,
                            "description": task.description,
                            "start": task.date,
                            "end": task.date + timedelta(hours=1),
                        },
                    )(),
                )
            except Exception:
                pass

        return task

    @staticmethod
    async def delete_task(db: Session, user: User, task_id: int) -> bool:
        task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
        if not task:
            return False

        google_event_id = task.google_event_id
        db.delete(task)
        db.commit()

        if google_event_id:
            try:
                print("detected")
                await GoogleCalendarService.delete_event(db, user.id, google_event_id)
            except Exception:
                print("Exception detected")
                pass

        return True

    @staticmethod
    def _parse_google_start(value: str) -> datetime:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))

        parsed_date = date.fromisoformat(value)
        return datetime.combine(parsed_date, datetime.min.time())
