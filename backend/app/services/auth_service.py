from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import OAuthToken, User
from app.db.schemas import UserCreate

import logging

logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    def register_user(db: Session, payload: UserCreate) -> User:
        existing_user = db.query(User).filter(User.email == payload.email).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        user = User(
            name=payload.name,
            email=payload.email,
            password=hash_password(payload.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User | None:
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password):
            return None
        return user

    @staticmethod
    def get_google_auth_url() -> str:
        AuthService._ensure_google_oauth_config()
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": settings.google_oauth_scope,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    @staticmethod
    async def handle_google_callback(db: Session, code: str) -> dict:
        token_data = await AuthService._exchange_code_for_tokens(code)
        user_info = await AuthService._fetch_google_user_info(token_data["access_token"])

        user = db.query(User).filter(User.email == user_info["email"]).first()
        if not user:
            user = User(
                name=user_info.get("name") or user_info["email"].split("@")[0],
                email=user_info["email"],
                password=hash_password(AuthService._generate_google_placeholder_password(user_info["email"])),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        AuthService._store_oauth_tokens(db, user.id, token_data)

        return {"user": user, "jwt": create_access_token(str(user.id))}

    @staticmethod
    async def _exchange_code_for_tokens(code: str) -> dict:
        AuthService._ensure_google_oauth_config()
        payload = {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post("https://oauth2.googleapis.com/token", data=payload)
            if response.status_code >= 400:
                logger.error(
                    "[ERROR] Google OAuth token exchange failed status=%s body=%s",
                    response.status_code,
                    response.text,
                )
                raise HTTPException(status_code=400, detail="Failed to exchange Google OAuth code")
            return response.json()

    @staticmethod
    async def _fetch_google_user_info(access_token: str) -> dict:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", headers=headers)
            if response.status_code >= 400:
                logger.error(
                    "[ERROR] Google user profile fetch failed status=%s body=%s",
                    response.status_code,
                    response.text,
                )
                raise HTTPException(status_code=400, detail="Failed to fetch Google user profile")
            return response.json()

    @staticmethod
    def _store_oauth_tokens(db: Session, user_id: int, token_data: dict) -> OAuthToken:
        expires_in = token_data.get("expires_in")
        token_expiry = None
        if expires_in:
            token_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=int(expires_in))

        oauth_token = db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()
        if not oauth_token:
            oauth_token = OAuthToken(
                user_id=user_id,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_expiry=token_expiry,
            )
            db.add(oauth_token)
        else:
            oauth_token.access_token = token_data["access_token"]
            oauth_token.refresh_token = token_data.get("refresh_token") or oauth_token.refresh_token
            oauth_token.token_expiry = token_expiry

        db.commit()
        db.refresh(oauth_token)
        return oauth_token

    @staticmethod
    def get_success_redirect_url() -> str:
        return settings.frontend_success_url

    @staticmethod
    def _generate_google_placeholder_password(email: str) -> str:
        return f"google-oauth::{email}"

    @staticmethod
    def _ensure_google_oauth_config() -> None:
        missing = []
        if not settings.google_client_id:
            missing.append("GOOGLE_CLIENT_ID")
        if not settings.google_client_secret:
            missing.append("GOOGLE_CLIENT_SECRET")
        if not settings.google_redirect_uri:
            missing.append("GOOGLE_REDIRECT_URI")
        if missing:
            logger.error("[ERROR] Missing Google OAuth configuration: %s", ", ".join(missing))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth is not configured on the server",
            )
