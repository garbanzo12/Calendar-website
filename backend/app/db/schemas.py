from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TaskBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    date: datetime


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    date: datetime | None = None


class TaskResponse(TaskBase):
    id: int
    user_id: int
    google_event_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    parsed_title: str
    parsed_date: datetime
    task: TaskResponse
    message: str


class CalendarEventCreate(BaseModel):
    summary: str
    description: str | None = None
    start: datetime
    end: datetime


class CalendarEventUpdate(BaseModel):
    summary: str | None = None
    description: str | None = None
    start: datetime | None = None
    end: datetime | None = None


class CalendarEventResponse(BaseModel):
    id: str
    summary: str | None = None
    description: str | None = None
    start: dict
    end: dict


class CalendarSyncResponse(BaseModel):
    imported: int
    skipped: int
