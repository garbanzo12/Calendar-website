from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import Base, engine
from app.routes import auth, calendar, chat, tasks

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Personal AI Calendar Backend",
    version="1.0.0",
    description="FastAPI backend with PostgreSQL, JWT auth, Google OAuth, Google Calendar, and chat-to-task processing.",
)

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
