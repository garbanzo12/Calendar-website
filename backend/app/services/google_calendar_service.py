import logging
from datetime import date, datetime, time, timedelta, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import OAuthToken
from urllib.parse import quote

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    base_url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

    @classmethod
    async def create_event(
        cls,
        db: Session,
        user_id: int,
        summary: str,
        description: str | None,
        start: datetime,
        end: datetime,
    ) -> dict:
        payload = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": cls._to_google_datetime(start)},
            "end": {"dateTime": cls._to_google_datetime(end)},
        }
        response = await cls._calendar_request(
            db=db,
            user_id=user_id,
            method="POST",
            url=cls.base_url,
            json=payload,
            error_message="Failed to create Google Calendar event",
        )
        return response.json()

    @classmethod
    async def list_calendars(cls, db: Session, user_id: int) -> list[dict]:
        """Fetch all calendars from the user's Google Calendar list."""
        response = await cls._calendar_request(
            db=db,
            user_id=user_id,
            method="GET",
            url="https://www.googleapis.com/calendar/v3/users/me/calendarList",
            error_message="Failed to fetch Google Calendar list",
        )
        return response.json().get("items", [])

    @classmethod
    async def list_events(
        cls,
        db: Session,
        user_id: int,
        time_min: str | None = None,
        time_max: str | None = None,
        calendar_id: str = "primary",
        year: int | None = None,
    ) -> list[dict]:

        # Determine the target year (explicit > current)
        target_year = year or datetime.now(timezone.utc).year

        # Use full-year boundaries when no manual range is provided
        if not time_min:
            time_min = datetime(target_year, 1, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat()
        if not time_max:
            time_max = datetime(target_year, 12, 31, 23, 59, 59, tzinfo=timezone.utc).isoformat()

        print(f"Fetching events from {time_min} to {time_max}")

        params = {
            "singleEvents": "true",
            "orderBy": "startTime",
            "timeMin": time_min,
            "timeMax": time_max,
        }
        encoded_calendar_id = quote(calendar_id, safe="")
        url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_calendar_id}/events"

        response = await cls._calendar_request(
            db=db,
            user_id=user_id,
            method="GET",
            url=url,
            params=params,
            error_message="Failed to fetch Google Calendar events",
        )

        print("=== GOOGLE EVENTS RESPONSE ===")
        print(response.json())
        print("==============================")

        return response.json().get("items", [])

    @classmethod
    async def get_events(
        cls,
        db: Session,
        user_id: int,
        time_min: str | None = None,
        time_max: str | None = None,
    ) -> list[dict]:
        return await cls.list_events(db, user_id, time_min=time_min, time_max=time_max)

    @classmethod
    async def update_event(cls, db: Session, user_id: int, event_id: str, payload) -> dict:
        event = await cls._get_event(db, user_id, event_id)

        if payload.summary is not None:
            event["summary"] = payload.summary
        if payload.description is not None:
            event["description"] = payload.description
        if payload.start is not None:
            event["start"] = {"dateTime": cls._to_google_datetime(payload.start)}
        if payload.end is not None:
            event["end"] = {"dateTime": cls._to_google_datetime(payload.end)}

        if "start" in event and "end" in event:
            start_dt = cls._event_boundary_to_datetime(event["start"], is_end=False)
            end_dt = cls._event_boundary_to_datetime(event["end"], is_end=True)
            if end_dt <= start_dt:
                raise ValueError("Event end time must be later than start time")

        response = await cls._calendar_request(
            db=db,
            user_id=user_id,
            method="PUT",
            url=f"{cls.base_url}/{event_id}",
            json=event,
            error_message="Failed to update Google Calendar event",
        )
        return response.json()

    @classmethod
    async def delete_event(cls, db: Session, user_id: int, event_id: str) -> None:
        await cls._calendar_request(
            db=db,
            user_id=user_id,
            method="DELETE",
            url=f"{cls.base_url}/{event_id}",
            error_message="Failed to delete Google Calendar event",
        )

    @classmethod
    async def _get_event(cls, db: Session, user_id: int, event_id: str) -> dict:
        response = await cls._calendar_request(
            db=db,
            user_id=user_id,
            method="GET",
            url=f"{cls.base_url}/{event_id}",
            error_message="Failed to fetch Google Calendar event",
        )
        return response.json()

    @classmethod
    async def _get_valid_access_token(cls, db: Session, user_id: int) -> str:
        oauth_token = cls._get_oauth_token(db, user_id)
        return await cls._ensure_valid_access_token(db, oauth_token)

    @classmethod
    async def _calendar_request(
        cls,
        db: Session,
        user_id: int,
        method: str,
        url: str,
        error_message: str,
        **request_kwargs,
    ) -> httpx.Response:
        oauth_token = cls._get_oauth_token(db, user_id)
        access_token = await cls._ensure_valid_access_token(db, oauth_token)

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=cls._headers(access_token),
                    **request_kwargs,
                )
                if response.status_code == status.HTTP_401_UNAUTHORIZED and oauth_token.refresh_token:
                    access_token = await cls._refresh_and_store_access_token(db, oauth_token)
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=cls._headers(access_token),
                        **request_kwargs,
                    )
                cls._raise_for_status(response, error_message)
                return response
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("%s", error_message)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error_message) from exc

    @classmethod
    def _get_oauth_token(cls, db: Session, user_id: int) -> OAuthToken:
        oauth_token = db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()
        if not oauth_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account not connected. Complete OAuth first.",
            )
        return oauth_token

    @classmethod
    async def _ensure_valid_access_token(cls, db: Session, oauth_token: OAuthToken) -> str:
        now = datetime.utcnow()
        if oauth_token.token_expiry and oauth_token.token_expiry <= now:
            if not oauth_token.refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google access token expired. Reconnect your Google account.",
                )
            return await cls._refresh_and_store_access_token(db, oauth_token)
        return oauth_token.access_token

    @classmethod
    async def _refresh_and_store_access_token(cls, db: Session, oauth_token: OAuthToken) -> str:
        try:
            refreshed = await cls._refresh_access_token(oauth_token.refresh_token)
        except HTTPException:
            logger.exception("Failed to refresh Google access token for user_id=%s", oauth_token.user_id)
            raise

        expires_in = int(refreshed.get("expires_in", 3600))
        oauth_token.access_token = refreshed["access_token"]
        oauth_token.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        db.commit()
        db.refresh(oauth_token)
        return oauth_token.access_token

    @staticmethod
    async def _refresh_access_token(refresh_token: str) -> dict:
        payload = {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post("https://oauth2.googleapis.com/token", data=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.exception(
                    "Google token refresh failed with status=%s body=%s",
                    response.status_code,
                    response.text,
                )
                raise HTTPException(status_code=400, detail="Failed to refresh Google access token") from exc
            return response.json()

    @staticmethod
    def _headers(access_token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    @staticmethod
    def _to_google_datetime(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    @staticmethod
    def _from_google_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @classmethod
    def event_start_to_task_date(cls, event: dict) -> datetime:
        start = event.get("start") or {}
        return cls._event_boundary_to_datetime(start, is_end=False)

    @classmethod
    def _event_boundary_to_datetime(cls, value: dict, is_end: bool) -> datetime:
        date_time = value.get("dateTime")
        if date_time:
            parsed = cls._from_google_datetime(date_time)
            if parsed.tzinfo is not None:
                return parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed

        date_value = value.get("date")
        if date_value:
            parsed_date = date.fromisoformat(date_value)
            parsed_time = time.max if is_end else time.min
            return datetime.combine(parsed_date, parsed_time)

        boundary_name = "end" if is_end else "start"
        raise ValueError(f"Google event is missing a {boundary_name} date")

    @staticmethod
    def _raise_for_status(response: httpx.Response, message: str) -> None:
        if response.status_code >= 400:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.exception(
                    "%s status=%s body=%s",
                    message,
                    response.status_code,
                    response.text,
                )
                raise HTTPException(status_code=response.status_code, detail=message) from exc
