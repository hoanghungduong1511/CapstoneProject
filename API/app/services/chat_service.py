from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ai_result import AIResult
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.rag_query import RAGQuery
from app.models.rag_result import RAGResult
from app.services.ai_service import AIServiceError, call_ai_chat
from app.services.medical_context_service import build_medical_context


def _get_owned_session(
    db: Session,
    user_id: UUID,
    session_id: UUID,
    include_deleted: bool = False,
) -> ChatSession:
    query = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user_id,
    )
    if not include_deleted:
        query = query.filter(ChatSession.status != "deleted")
    session = query.first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy phiên hội thoại.",
        )
    return session


def create_chat_session(
    db: Session,
    user_id: UUID,
    ai_result_id: UUID | None = None,
    initial_message: str | None = None,
    title: str | None = None,
) -> ChatSession:
    if ai_result_id:
        analysis_exists = (
            db.query(AIResult.id)
            .filter(AIResult.id == ai_result_id, AIResult.user_id == user_id)
            .first()
        )
        if not analysis_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy kết quả phân tích của người dùng.",
            )

    session = ChatSession(
        user_id=user_id,
        ai_result_id=ai_result_id,
        title=title.strip() if title else None,
        status="active",
    )
    db.add(session)
    db.flush()

    if initial_message and initial_message.strip():
        db.add(
            ChatMessage(
                session_id=session.id,
                role="assistant",
                content=initial_message.strip(),
                ai_result_id=ai_result_id,
                safety_level="low",
                model_name="system",
            )
        )

    db.commit()
    db.refresh(session)
    return session


def _ensure_owned_ai_result(
    db: Session,
    user_id: UUID,
    ai_result_id: UUID,
) -> None:
    analysis_exists = (
        db.query(AIResult.id)
        .filter(AIResult.id == ai_result_id, AIResult.user_id == user_id)
        .first()
    )
    if not analysis_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy kết quả phân tích của người dùng.",
        )


def add_chat_message(
    db: Session,
    user_id: UUID,
    session_id: UUID,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> ChatMessage:
    session = _get_owned_session(db, user_id, session_id)
    message = ChatMessage(
        session_id=session.id,
        role=role,
        content=content.strip(),
        meta=metadata,
        ai_result_id=session.ai_result_id,
    )
    session.updated_at = datetime.utcnow()
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


async def generate_chat_message(
    db: Session,
    user_id: UUID,
    session_id: UUID,
    message: str,
    ai_result_id: UUID | None,
    user_symptoms: dict | None,
) -> dict:
    session = _get_owned_session(db, user_id, session_id)
    if ai_result_id and session.ai_result_id != ai_result_id:
        _ensure_owned_ai_result(db, user_id, ai_result_id)
        session.ai_result_id = ai_result_id
        session.updated_at = datetime.utcnow()
        db.flush()

    if not session.ai_result_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phiên tư vấn AI cần gắn với một kết quả phân tích ảnh.",
        )

    medical_context = build_medical_context(
        db,
        user_id,
        session.ai_result_id,
        user_symptoms,
    )
    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=message.strip(),
        ai_result_id=session.ai_result_id,
        medical_context_id=medical_context.id,
    )
    db.add(user_message)
    session.updated_at = datetime.utcnow()
    db.commit()

    history_rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session.id,
            ChatMessage.id != user_message.id,
            ChatMessage.role.in_(["user", "assistant"]),
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(4)
        .all()
    )
    history = [
        {"role": item.role, "content": item.content}
        for item in reversed(history_rows)
    ]

    try:
        generated = await call_ai_chat(
            message,
            medical_context.context_json or {},
            history,
        )
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    chunks = generated.get("retrieved_chunks") or []
    rag_query = RAGQuery(
        medical_context_id=medical_context.id,
        session_id=session.id,
        query_text=message,
        user_question=message,
        rewritten_query=generated.get("rewritten_query"),
        topk_labels_json=[
            item.get("label")
            for item in medical_context.classification_topk_json or []
        ],
    )
    db.add(rag_query)
    db.flush()

    rag_result = RAGResult(
        rag_query_id=rag_query.id,
        document_id="csv-rag-aggregate",
        document_snippet="\n\n".join(
            str(chunk.get("content", ""))[:500] for chunk in chunks
        )[:4000],
        score=max(
            [float(chunk.get("score", 0) or 0) for chunk in chunks],
            default=0.0,
        ),
        retrieved_chunks_json=chunks,
        sources_json=generated.get("sources") or [],
        ranking_scores_json=[
            {
                "document_id": chunk.get("document_id"),
                "score": chunk.get("score"),
            }
            for chunk in chunks
        ],
        final_context="\n\n---\n\n".join(
            str(chunk.get("content", "")) for chunk in chunks
        ),
    )
    db.add(rag_result)
    db.flush()

    user_message.rag_query_id = rag_query.id
    user_message.rag_result_id = rag_result.id

    assistant = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=generated["answer"],
        ai_result_id=session.ai_result_id,
        medical_context_id=medical_context.id,
        rag_query_id=rag_query.id,
        rag_result_id=rag_result.id,
        safety_level=generated.get("safety_level", "low"),
        model_name=generated.get("model_name"),
        meta={
            "sources": generated.get("sources") or [],
            "token_usage": generated.get("token_usage"),
            "missing_questions": generated.get("missing_questions") or [],
        },
    )
    db.add(assistant)
    session.updated_at = datetime.utcnow()
    if not session.title:
        session.title = message.strip()[:100]
    db.commit()
    db.refresh(assistant)

    return {
        "message_id": assistant.id,
        "answer": assistant.content,
        "safety_level": assistant.safety_level,
        "sources": generated.get("sources") or [],
        "missing_questions": generated.get("missing_questions") or [],
        "medical_context_id": medical_context.id,
        "rag_query_id": rag_query.id,
        "rag_result_id": rag_result.id,
        "model_name": assistant.model_name or "unknown",
        "token_usage": generated.get("token_usage"),
    }


def list_chat_sessions(
    db: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 30,
) -> dict:
    stats = (
        db.query(
            ChatMessage.session_id.label("session_id"),
            func.count(ChatMessage.id).label("message_count"),
            func.max(ChatMessage.created_at).label("last_message_at"),
        )
        .group_by(ChatMessage.session_id)
        .subquery()
    )

    query = (
        db.query(
            ChatSession,
            func.coalesce(stats.c.message_count, 0).label("message_count"),
            func.coalesce(stats.c.last_message_at, ChatSession.created_at).label(
                "last_message_at"
            ),
        )
        .outerjoin(stats, stats.c.session_id == ChatSession.id)
        .filter(
            ChatSession.user_id == user_id,
            ChatSession.status != "deleted",
        )
        .order_by(
            func.coalesce(stats.c.last_message_at, ChatSession.created_at).desc()
        )
    )

    total = query.count()
    rows = query.offset(skip).limit(limit).all()
    items = []
    for session, message_count, last_message_at in rows:
        first_user_message = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.session_id == session.id,
                ChatMessage.role == "user",
            )
            .order_by(ChatMessage.created_at.asc())
            .first()
        )
        last_message = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        title = session.title or (
            first_user_message.content[:100]
            if first_user_message
            else "Tư vấn da liễu"
        )
        items.append(
            {
                "id": session.id,
                "ai_result_id": session.ai_result_id,
                "title": title,
                "status": session.status,
                "message_count": int(message_count or 0),
                "last_message": last_message.content[:160] if last_message else None,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "last_message_at": last_message_at,
            }
        )
    return {"items": items, "total": total}


def get_chat_session_detail(
    db: Session,
    user_id: UUID,
    session_id: UUID,
) -> dict:
    session = _get_owned_session(db, user_id, session_id)
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )
    return {
        "id": session.id,
        "ai_result_id": session.ai_result_id,
        "title": session.title,
        "status": session.status,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "messages": messages,
    }


def delete_chat_session(
    db: Session,
    user_id: UUID,
    session_id: UUID,
) -> None:
    session = _get_owned_session(db, user_id, session_id)
    session.status = "deleted"
    session.updated_at = datetime.utcnow()
    db.commit()
