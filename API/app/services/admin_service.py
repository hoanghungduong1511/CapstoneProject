from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.ai_result import AIResult
from app.models.classification_result import ClassificationResult
from app.models.image import Image
from app.models.segmentation_result import SegmentationResult
from app.models.user import User


def list_managed_users(
    db: Session,
    search: str | None = None,
    user_status: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> dict:
    analysis_stats = (
        db.query(
            AIResult.user_id.label("user_id"),
            func.count(AIResult.id).label("analysis_count"),
            func.max(AIResult.created_at).label("last_analysis_at"),
        )
        .group_by(AIResult.user_id)
        .subquery()
    )

    query = (
        db.query(
            User,
            func.coalesce(analysis_stats.c.analysis_count, 0).label("analysis_count"),
            analysis_stats.c.last_analysis_at,
        )
        .outerjoin(analysis_stats, analysis_stats.c.user_id == User.id)
        .filter(User.role == "user", User.deleted_at.is_(None))
    )

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.email.ilike(pattern),
                User.name.ilike(pattern),
            )
        )

    if user_status in {"active", "inactive"}:
        query = query.filter(User.status == user_status)

    total = query.count()
    rows = (
        query.order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    active = (
        db.query(func.count(User.id))
        .filter(User.role == "user", User.status == "active", User.deleted_at.is_(None))
        .scalar()
        or 0
    )
    inactive = (
        db.query(func.count(User.id))
        .filter(User.role == "user", User.status == "inactive", User.deleted_at.is_(None))
        .scalar()
        or 0
    )
    total_analyses = (
        db.query(func.count(AIResult.id))
        .join(User, AIResult.user_id == User.id)
        .filter(User.role == "user", User.deleted_at.is_(None))
        .scalar()
        or 0
    )

    return {
        "items": [
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "provider": user.provider,
                "status": user.status,
                "date_of_birth": user.date_of_birth,
                "gender": user.gender,
                "analysis_count": int(analysis_count or 0),
                "last_analysis_at": last_analysis_at,
                "created_at": user.created_at,
            }
            for user, analysis_count, last_analysis_at in rows
        ],
        "total": total,
        "active": active,
        "inactive": inactive,
        "total_analyses": total_analyses,
    }


def get_managed_user_detail(db: Session, user_id: UUID) -> dict:
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.role == "user",
            User.deleted_at.is_(None),
        )
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng",
        )

    history_rows = (
        db.query(
            AIResult.id,
            Image.image_url,
            AIResult.status,
            ClassificationResult.top1_label,
            ClassificationResult.top1_confidence,
            SegmentationResult.lesion_area_percent,
            AIResult.processing_time_ms,
            AIResult.created_at,
        )
        .join(Image, AIResult.image_id == Image.id)
        .outerjoin(
            ClassificationResult,
            ClassificationResult.ai_result_id == AIResult.id,
        )
        .outerjoin(
            SegmentationResult,
            SegmentationResult.ai_result_id == AIResult.id,
        )
        .filter(AIResult.user_id == user.id)
        .order_by(AIResult.created_at.desc())
        .all()
    )

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "provider": user.provider,
        "role": user.role,
        "status": user.status,
        "date_of_birth": user.date_of_birth,
        "gender": user.gender,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "analysis_count": len(history_rows),
        "history": [
            {
                "id": row.id,
                "image_url": row.image_url,
                "status": row.status,
                "top1_label": row.top1_label,
                "top1_confidence": row.top1_confidence,
                "lesion_area_percent": row.lesion_area_percent,
                "processing_time_ms": row.processing_time_ms,
                "created_at": row.created_at,
            }
            for row in history_rows
        ],
    }


def set_managed_user_locked(db: Session, user_id: UUID, locked: bool) -> dict:
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.role == "user",
            User.deleted_at.is_(None),
        )
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng",
        )

    user.status = "inactive" if locked else "active"
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "status": user.status,
        "message": "Đã khóa tài khoản" if locked else "Đã mở khóa tài khoản",
    }
