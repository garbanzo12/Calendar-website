import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import Task, User
from app.db.schemas import CalendarEventCreate, CalendarEventResponse, CalendarEventUpdate, CalendarSyncResponse
from app.services.google_calendar_service import GoogleCalendarService

router = APIRouter(prefix="/calendar", tags=["Calendar"])
logger = logging.getLogger(__name__)


@router.get("/events", response_model=list[CalendarEventResponse])
async def get_events(
    time_min: str | None = Query(default=None),
    time_max: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return await GoogleCalendarService.list_events(db, current_user.id, time_min=time_min, time_max=time_max)


@router.post("/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: CalendarEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return await GoogleCalendarService.create_event(
        db=db,
        user_id=current_user.id,
        summary=payload.summary,
        description=payload.description,
        start=payload.start,
        end=payload.end,
    )


@router.put("/events/{event_id}", response_model=CalendarEventResponse)
async def update_event(
    event_id: str,
    payload: CalendarEventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return await GoogleCalendarService.update_event(db, current_user.id, event_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    await GoogleCalendarService.delete_event(db, current_user.id, event_id)


@router.get("/sync", response_model=CalendarSyncResponse)
async def sync_calendar(
    year: int | None = Query(default=None, description="Year to sync (default: current year)."),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CalendarSyncResponse:
    import time
    from datetime import timedelta

    logger.info(f"[SYNC START] user_id={current_user.id}")
    
    # Debounce / Throttle: Skip if synced less than 3 minutes ago
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if current_user.last_sync_at and (now_utc - current_user.last_sync_at) < timedelta(minutes=3):
        logger.info(f"[SYNC RESULT] imported=0 skipped=0 duration=0ms reason=throttled user_id={current_user.id}")
        return CalendarSyncResponse(imported=0, skipped=0, calendars=0)

    start_time = time.time()
    target_year = year or now_utc.year

    # Fetch all user calendars
    calendars = await GoogleCalendarService.list_calendars(db=db, user_id=current_user.id)

    # Load all already-imported prefixed IDs up front
    existing_event_ids = {
        event_id
        for (event_id,) in db.query(Task.google_event_id)
        .filter(Task.user_id == current_user.id, Task.google_event_id.isnot(None))
        .all()
    }

    imported = 0
    skipped = 0

    for calendar in calendars:
        calendar_id = calendar.get("id")
        if not calendar_id:
            continue

        try:
            events = await GoogleCalendarService.list_events(
                db=db,
                user_id=current_user.id,
                calendar_id=calendar_id,
                year=target_year,
            )
        except Exception:
            logger.exception(
                "Failed to fetch events for calendar_id=%s user_id=%s — skipping",
                calendar_id,
                current_user.id,
            )
            continue

        for event in events:
            raw_event_id = event.get("id")
            if not raw_event_id:
                skipped += 1
                continue

            # Prefix with calendar_id to ensure global uniqueness
            prefixed_id = f"{calendar_id}_{raw_event_id}"

            if prefixed_id in existing_event_ids:
                skipped += 1
                continue

            try:
                task_date = GoogleCalendarService.event_start_to_task_date(event)
            except ValueError:
                logger.exception(
                    "Skipping Google event import for user_id=%s event_id=%s calendar_id=%s",
                    current_user.id,
                    raw_event_id,
                    calendar_id,
                )
                skipped += 1
                continue

            task = Task(
                user_id=current_user.id,
                title=event.get("summary") or "(No title)",
                description=event.get("description"),
                date=task_date,
                google_event_id=prefixed_id,
            )
            db.add(task)
            existing_event_ids.add(prefixed_id)
            imported += 1

    current_user.last_sync_at = now_utc
    db.commit()

    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(f"[SYNC RESULT] imported={imported} skipped={skipped} duration={duration_ms}ms user_id={current_user.id}")
    return CalendarSyncResponse(imported=imported, skipped=skipped, calendars=len(calendars))
