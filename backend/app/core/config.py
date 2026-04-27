import os
from dataclasses import dataclass
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/calendar_db")
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    openai_timeout_seconds: float = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "45"))
    chat_temperature: float = float(os.getenv("CHAT_TEMPERATURE", "0.6"))
    chat_max_tokens: int = int(os.getenv("CHAT_MAX_TOKENS", "450"))
    chat_recent_messages: int = int(os.getenv("CHAT_RECENT_MESSAGES", "5"))
    chat_relevant_messages: int = int(os.getenv("CHAT_RELEVANT_MESSAGES", "6"))
    chat_embedding_cache_limit: int = int(os.getenv("CHAT_EMBEDDING_CACHE_LIMIT", "1"))
    chat_retrieval_scan_limit: int = int(os.getenv("CHAT_RETRIEVAL_SCAN_LIMIT", "200"))
    chat_max_context_chars: int = int(os.getenv("CHAT_MAX_CONTEXT_CHARS", "6000"))
    embedding_dimensions: int = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536"))
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    google_oauth_scope: str = os.getenv(
        "GOOGLE_OAUTH_SCOPE",
        "openid email profile https://www.googleapis.com/auth/calendar",
    )
    frontend_success_url: str = os.getenv("FRONTEND_SUCCESS_URL", "http://localhost:5173/dashboard")
    backend_cors_origins: str = os.getenv(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    @property
    def access_token_expire_delta(self) -> timedelta:
        return timedelta(minutes=self.access_token_expire_minutes)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


settings = Settings()
