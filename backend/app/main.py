import logging
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import check_database_connection
from app.routes import auth, calendar, chat, tasks

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("api")

# Keep uvicorn access logs minimal to reduce noise
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("[STARTUP] Server initialization started")

    for attempt in range(1, settings.db_connect_retries + 1):
        try:
            check_database_connection()
            logger.info("[DB] Connected successfully")
            break
        except Exception as exc:
            logger.error(
                "[ERROR] Database connection failed (attempt %s/%s): %s",
                attempt,
                settings.db_connect_retries,
                str(exc),
            )
            if attempt >= settings.db_connect_retries:
                raise
            await asyncio.sleep(settings.db_connect_retry_delay_seconds)

    if settings.google_redirect_uri:
        logger.info("[STARTUP] GOOGLE_REDIRECT_URI configured as %s", settings.google_redirect_uri)
    else:
        logger.warning("[STARTUP] GOOGLE_REDIRECT_URI is not configured")

    logger.info("[STARTUP] Server initialized")
    yield
    logger.info("[SHUTDOWN] Server stopped")

app = FastAPI(
    title="Personal AI Calendar Backend",
    version="1.0.0",
    description="FastAPI backend with PostgreSQL, JWT auth, Google OAuth, Google Calendar, and chat-to-task processing.",
    lifespan=lifespan,
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    if request.url.path in ["/favicon.ico"] or request.url.path.startswith(("/assets", "/static")):
        return await call_next(request)

    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = int((time.time() - start_time) * 1000)
        logger.info(f"[INFO] {request.method} {request.url.path} → {response.status_code} ({process_time}ms)")
        return response
    except Exception as exc:
        process_time = int((time.time() - start_time) * 1000)
        logger.exception(f"[ERROR] {request.method} {request.url.path} → 500 ({process_time}ms): {str(exc)}")
        raise
origins = [
    "http://localhost:5173",  # desarrollo
    "https://calendar-website-frontend.onrender.com"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(calendar.router)
app.include_router(chat.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Personal AI Calendar Backend is running"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
