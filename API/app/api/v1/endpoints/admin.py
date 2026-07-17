from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import (
    AdminUserDetail,
    AdminUserListResponse,
    AdminUserStatusResponse,
    AdminUserStatusUpdate,
)
from app.services.admin_service import (
    get_managed_user_detail,
    list_managed_users,
    set_managed_user_locked,
)


router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/users", response_model=AdminUserListResponse)
def users(
    search: str | None = Query(None, max_length=255),
    status: str | None = Query(None, pattern="^(active|inactive)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    return list_managed_users(db, search, status, skip, limit)


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def user_detail(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    return get_managed_user_detail(db, user_id)


@router.patch("/users/{user_id}/status", response_model=AdminUserStatusResponse)
def update_user_status(
    user_id: UUID,
    data: AdminUserStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    return set_managed_user_locked(db, user_id, data.locked)
