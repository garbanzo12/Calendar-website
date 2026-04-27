from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.db.schemas import ChatClearResponse, ChatMessageResponse, ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/history", response_model=list[ChatMessageResponse])
async def get_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatMessageResponse]:
    return await ChatService.get_history(db, current_user, limit)


@router.delete("/history", response_model=ChatClearResponse)
async def clear_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatClearResponse:
    await ChatService.clear_history(db, current_user)
    return ChatClearResponse(message="Chat memory cleared")


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
@router.post("/message", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def process_chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    return await ChatService.process_message(db, current_user, payload.message)
