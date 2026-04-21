import logging
from datetime import timedelta

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
            # Persist the Google event id so later updates/deletes can stay in sync.
            task.google_event_id = event["id"]
            db.commit()
            db.refresh(task)
        except Exception:
            db.rollback()
            logger.exception("Failed to sync created task %s with Google Calendar", task.id)

        return task

    @staticmethod
    def list_tasks(db: Session, user_id: int) -> list[Task]:
        return db.query(Task).filter(Task.user_id == user_id).order_by(Task.date.asc()).all()

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
                logger.exception("Failed to sync updated task %s to Google Calendar", task.id)

        return task

    @staticmethod
    async def delete_task(db: Session, user: User, task_id: int) -> bool:
        task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
        if not task:
            return False

        if task.google_event_id:
            try:
                # Try removing the remote event before deleting the local row.
                await GoogleCalendarService.delete_event(db, user.id, task.google_event_id)
            except Exception:
                logger.exception(
                    "Failed to delete Google Calendar event %s for task %s",
                    task.google_event_id,
                    task.id,
                )

        db.delete(task)
        db.commit()

        return True
