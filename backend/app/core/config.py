import os
from dataclasses import dataclass
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    secret_key: str = os.getenv("SECRET_KEY", "")
    algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", "")
    google_oauth_scope: str = os.getenv(
        "GOOGLE_OAUTH_SCOPE",
        "openid email profile https://www.googleapis.com/auth/calendar",
    )
    frontend_success_url: str = os.getenv("FRONTEND_SUCCESS_URL", "")
    backend_cors_origins: str = os.getenv(
        "BACKEND_CORS_ORIGINS",
        "*",
    )
    db_connect_retries: int = int(os.getenv("DB_CONNECT_RETRIES", "5"))
    db_connect_retry_delay_seconds: float = float(os.getenv("DB_CONNECT_RETRY_DELAY_SECONDS", "2"))

    @property
    def access_token_expire_delta(self) -> timedelta:
        return timedelta(minutes=self.access_token_expire_minutes)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def normalized_database_url(self) -> str:
        # Render may provide DATABASE_URL using `postgres://`; SQLAlchemy expects `postgresql://`.
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql://", 1)
        return self.database_url


settings = Settings()
