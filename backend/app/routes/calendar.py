from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.db.schemas import CalendarEventCreate, CalendarEventResponse, CalendarEventUpdate
from app.services.google_calendar_service import GoogleCalendarService

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.get("/events", response_model=list[CalendarEventResponse])
def get_events(
    time_min: str | None = Query(default=None),
    time_max: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return GoogleCalendarService.get_events(db, current_user.id, time_min=time_min, time_max=time_max)


@router.post("/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: CalendarEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return GoogleCalendarService.create_event(
        db=db,
        user_id=current_user.id,
        summary=payload.summary,
        description=payload.description,
        start=payload.start,
        end=payload.end,
    )


@router.put("/events/{event_id}", response_model=CalendarEventResponse)
def update_event(
    event_id: str,
    payload: CalendarEventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return GoogleCalendarService.update_event(db, current_user.id, event_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    GoogleCalendarService.delete_event(db, current_user.id, event_id)
