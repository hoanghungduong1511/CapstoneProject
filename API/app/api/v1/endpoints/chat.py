from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatTurnResponse,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionListResponse,
)
from app.services.chat_service import (
    add_chat_message,
    create_chat_session,
    delete_chat_session,
    generate_chat_message,
    get_chat_session_detail,
    list_chat_sessions,
)


router = APIRouter(prefix="/chat", tags=["Chat History"])


@router.post("/sessions", response_model=ChatSessionDetail, status_code=status.HTTP_201_CREATED)
def create_session(
    data: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = create_chat_session(
        db,
        current_user.id,
        data.ai_result_id,
        data.initial_message,
        data.title,
    )
    return get_chat_session_detail(db, current_user.id, session.id)


@router.get("/sessions", response_model=ChatSessionListResponse)
def sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_chat_sessions(db, current_user.id, skip, limit)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def session_detail(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_chat_session_detail(db, current_user.id, session_id)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageResponse | ChatTurnResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    session_id: UUID,
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.message:
        return await generate_chat_message(
            db,
            current_user.id,
            session_id,
            data.message,
            data.ai_result_id,
            data.user_symptoms.model_dump() if data.user_symptoms else None,
        )
    return add_chat_message(
        db,
        current_user.id,
        session_id,
        data.role or "user",
        data.content or "",
        data.metadata,
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_chat_session(db, current_user.id, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
