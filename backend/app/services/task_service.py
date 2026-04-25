from datetime import timedelta

from sqlalchemy.orm import Session

from app.db.models import Task, User
from app.db.schemas import TaskCreate, TaskUpdate
from app.services.google_calendar_service import GoogleCalendarService


class TaskService:
    @staticmethod
    async def create_task(db: Session, user: User, payload: TaskCreate) -> Task:
        event = await GoogleCalendarService.create_event(
            db=db,
            user_id=user.id,
            summary=payload.title,
            description=payload.description,
            start=payload.date,
            end=payload.date + timedelta(hours=1),
        )

        task = Task(
            user_id=user.id,
            title=payload.title,
            description=payload.description,
            date=payload.date,
            google_event_id=event.get("id"),
        )
        db.add(task)
        db.commit()
        db.refresh(task)

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

        if task.google_event_id:
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

        db.commit()
        db.refresh(task)

        return task

    @staticmethod
    async def delete_task(db: Session, user: User, task_id: int) -> bool:
        task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
        if not task:
            return False

        if task.google_event_id:
            await GoogleCalendarService.delete_event(db, user.id, task.google_event_id)

        db.delete(task)
        db.commit()

        return True
