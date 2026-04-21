import logging
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import OAuthToken

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
        access_token = await cls._get_valid_access_token(db, user_id)
        payload = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": cls._to_google_datetime(start)},
            "end": {"dateTime": cls._to_google_datetime(end)},
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(cls.base_url, headers=cls._headers(access_token), json=payload)
            cls._raise_for_status(response, "Failed to create Google Calendar event")
            return response.json()

    @classmethod
    async def get_events(
        cls,
        db: Session,
        user_id: int,
        time_min: str | None = None,
        time_max: str | None = None,
    ) -> list[dict]:
        access_token = await cls._get_valid_access_token(db, user_id)
        params = {"singleEvents": "true", "orderBy": "startTime"}
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(cls.base_url, headers=cls._headers(access_token), params=params)
            cls._raise_for_status(response, "Failed to fetch Google Calendar events")
            return response.json().get("items", [])

    @classmethod
    def list_events(cls, db: Session, user_id: int) -> list[dict]:
        
        logger.info("Listing Google Calendar events for user %s", user_id)
        access_token = cls._get_valid_access_token_sync(db, user_id)
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        params = {"singleEvents": "true", "orderBy": "startTime"}
        
        with httpx.Client(timeout=20.0) as client:
            response = client.get(cls.base_url, headers=headers, params=params)
            cls._raise_for_status(response, "Failed to fetch Google Calendar events")
            return response.json().get("items", [])

    @classmethod
    async def update_event(cls, db: Session, user_id: int, event_id: str, payload) -> dict:
        access_token = await cls._get_valid_access_token(db, user_id)
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
            start_dt = cls._from_google_datetime(event["start"]["dateTime"])
            end_dt = cls._from_google_datetime(event["end"]["dateTime"])
            if end_dt <= start_dt:
                raise ValueError("Event end time must be later than start time")

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.put(
                f"{cls.base_url}/{event_id}",
                headers=cls._headers(access_token),
                json=event,
            )
            cls._raise_for_status(response, "Failed to update Google Calendar event")
            return response.json()

    @classmethod
    async def delete_event(cls, db: Session, user_id: int, event_id: str) -> None:
        access_token = await cls._get_valid_access_token(db, user_id)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.delete(f"{cls.base_url}/{event_id}", headers=cls._headers(access_token))
            cls._raise_for_status(response, "Failed to delete Google Calendar event")

    @classmethod
    async def _get_event(cls, db: Session, user_id: int, event_id: str) -> dict:
        access_token = await cls._get_valid_access_token(db, user_id)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{cls.base_url}/{event_id}", headers=cls._headers(access_token))
            cls._raise_for_status(response, "Failed to fetch Google Calendar event")
            return response.json()

    @classmethod
    async def _get_valid_access_token(cls, db: Session, user_id: int) -> str:
        oauth_token = db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()
        if not oauth_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account not connected. Complete OAuth first.",
            )

        now = datetime.utcnow()
        if oauth_token.token_expiry and oauth_token.token_expiry <= now and oauth_token.refresh_token:
            refreshed = await cls._refresh_access_token(oauth_token.refresh_token)
            oauth_token.access_token = refreshed["access_token"]
            expires_in = int(refreshed.get("expires_in", 3600))
            oauth_token.token_expiry = now + timedelta(seconds=expires_in)
            db.commit()
            db.refresh(oauth_token)

        return oauth_token.access_token

    @classmethod
    def _get_valid_access_token_sync(cls, db: Session, user_id: int) -> str:
        oauth_token = db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()
        if not oauth_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account not connected. Complete OAuth first.",
            )

        now = datetime.utcnow()
        if oauth_token.token_expiry and oauth_token.token_expiry <= now and oauth_token.refresh_token:
            refreshed = cls._refresh_access_token_sync(oauth_token.refresh_token)
            oauth_token.access_token = refreshed["access_token"]
            expires_in = int(refreshed.get("expires_in", 3600))
            oauth_token.token_expiry = now + timedelta(seconds=expires_in)
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
            if response.status_code >= 400:
                raise HTTPException(status_code=400, detail="Failed to refresh Google access token")
            return response.json()

    @staticmethod
    def _refresh_access_token_sync(refresh_token: str) -> dict:
        payload = {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.post("https://oauth2.googleapis.com/token", data=payload)
            if response.status_code >= 400:
                raise HTTPException(status_code=400, detail="Failed to refresh Google access token")
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

    @staticmethod
    def _raise_for_status(response: httpx.Response, message: str) -> None:
        if response.status_code >= 400:
            logger.error("%s: %s", message, response.text)
            raise HTTPException(status_code=response.status_code, detail=message)
