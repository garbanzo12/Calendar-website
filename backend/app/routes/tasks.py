import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.db.schemas import TaskCreate, TaskResponse, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])
logger = logging.getLogger("api")

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    try:
        task = await TaskService.create_task(db, current_user, payload)
        logger.info(f"[ACTION] Task created: {task.id} for user {current_user.id}")
        return task
    except Exception as exc:
        logger.exception(f"[ERROR] POST /tasks: {str(exc)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create task")

@router.get("", response_model=list[TaskResponse])
def list_tasks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TaskResponse]:
    return TaskService.list_tasks(db, current_user.id)

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    try:
        task = await TaskService.update_task(db, current_user, task_id, payload)
        if not task:
            logger.warning(f"[WARNING] PUT /tasks/{task_id}: Task not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        logger.info(f"[ACTION] Task updated: {task.id} for user {current_user.id}")
        return task
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"[ERROR] PUT /tasks/{task_id}: {str(exc)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update task")

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        deleted = await TaskService.delete_task(db, current_user, task_id)
        if not deleted:
            logger.warning(f"[WARNING] DELETE /tasks/{task_id}: Task not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        logger.info(f"[ACTION] Task deleted: {task_id} for user {current_user.id}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"[ERROR] DELETE /tasks/{task_id}: {str(exc)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete task")
