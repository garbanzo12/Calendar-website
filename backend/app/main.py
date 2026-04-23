import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import Base, engine
from app.routes import auth, calendar, chat, tasks

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("api")

# Keep uvicorn access logs minimal to reduce noise
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Personal AI Calendar Backend",
    version="1.0.0",
    description="FastAPI backend with PostgreSQL, JWT auth, Google OAuth, Google Calendar, and chat-to-task processing.",
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
