from typing import Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import UserRegister
from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_provider_id(db: Session, provider: str, provider_id: str) -> Optional[User]:
    return db.query(User).filter(
        User.provider == provider,
        User.provider_id == provider_id,
    ).first()


def register_user(db: Session, user_data: UserRegister) -> User:
    """Đăng ký người dùng mới (local)."""
    existing = get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được đăng ký",
        )

    new_user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=hash_password(user_data.password),
        provider="local",
        role="user",
        status="active",
        date_of_birth=user_data.date_of_birth,
        gender=user_data.gender,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def authenticate_user(db: Session, email: str, password: str) -> dict:
    """Xác thực local user và trả về tokens."""
    user = get_user_by_email(db, email)
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa",
        )

    return _generate_tokens(user)


def refresh_access_token(db: Session, refresh_token: str) -> dict:
    """Tạo access token mới từ refresh token."""
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không phải là refresh token",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tồn tại",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa",
        )

    return _generate_tokens(user)


def get_user_profile(db: Session, user_id: str) -> User:
    """Lấy thông tin profile người dùng."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tồn tại",
        )
    return user


# ══════════════════════════════════════════════════════════════════════
# Google OAuth
# ══════════════════════════════════════════════════════════════════════


GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


async def verify_google_token(credential: str) -> dict:
    """
    Verify Google token — hỗ trợ cả id_token (One Tap) và access_token (OAuth implicit).
    
    Thử verify bằng tokeninfo (id_token) trước.
    Nếu thất bại, thử lấy userinfo bằng access_token.
    """
    async with httpx.AsyncClient() as client:
        # 1. Thử verify như id_token
        response = await client.get(
            GOOGLE_TOKENINFO_URL,
            params={"id_token": credential},
        )

        if response.status_code == 200:
            payload = response.json()
            # Verify audience
            if settings.GOOGLE_CLIENT_ID and payload.get("aud") != settings.GOOGLE_CLIENT_ID:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token không thuộc về ứng dụng này",
                )
            return payload

        # 2. Thử verify như access_token → lấy userinfo
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {credential}"},
        )

        if userinfo_response.status_code == 200:
            payload = userinfo_response.json()
            # Map userinfo fields to match tokeninfo format
            return {
                "sub": payload.get("sub"),
                "email": payload.get("email"),
                "name": payload.get("name"),
                "picture": payload.get("picture"),
                "email_verified": payload.get("email_verified", False),
            }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Google token không hợp lệ hoặc đã hết hạn",
    )


async def google_login(db: Session, credential: str) -> dict:
    """
    Login/Register bằng Google OAuth.
    Flow: verify token → tìm hoặc tạo user → trả JWT tokens.
    """
    # 1. Verify Google token
    google_data = await verify_google_token(credential)

    google_id = google_data.get("sub")
    email = google_data.get("email")
    name = google_data.get("name")
    avatar_url = google_data.get("picture")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không lấy được email từ Google",
        )

    # 2. Tìm user theo provider_id trước
    user = get_user_by_provider_id(db, "google", google_id)

    if not user:
        # 3. Tìm theo email (trường hợp đã register local trước)
        user = get_user_by_email(db, email)

        if user:
            # Link Google account vào user đã có
            user.provider_id = google_id
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
            db.commit()
            db.refresh(user)
        else:
            # 4. Tạo user mới
            user = User(
                email=email,
                name=name,
                provider="google",
                provider_id=google_id,
                avatar_url=avatar_url,
                role="user",
                status="active",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa",
        )

    return _generate_tokens(user)


def _generate_tokens(user: User) -> dict:
    """Helper: tạo access + refresh tokens."""
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# ══════════════════════════════════════════════════════════════════════
# PROFILE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════


def update_user_profile(db: Session, user: User, update_data: dict) -> User:
    """Cập nhật thông tin cá nhân (name, date_of_birth, gender)."""
    allowed_fields = {"name", "date_of_birth", "gender"}
    for key, value in update_data.items():
        if key in allowed_fields and value is not None:
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def change_user_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """Verify the current password and replace it with a new password hash."""
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản này không sử dụng mật khẩu nội bộ",
        )

    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không đúng",
        )

    if verify_password(new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới phải khác mật khẩu hiện tại",
        )

    user.password_hash = hash_password(new_password)
    db.commit()


async def upload_user_avatar(db: Session, user: User, file) -> str:
    """Upload avatar lên MinIO và cập nhật avatar_url trong DB."""
    from app.services.minio_service import upload_file, extract_object_name, delete_file

    # Xóa avatar cũ nếu có (và không phải external URL)
    if user.avatar_url and "minio" in user.avatar_url:
        old_object = extract_object_name(user.avatar_url)
        delete_file(old_object)

    # Upload avatar mới
    avatar_url = await upload_file(file, folder="avatars")
    user.avatar_url = avatar_url
    db.commit()
    db.refresh(user)
    return avatar_url


def get_diagnosis_history(db: Session, user_id, skip: int = 0, limit: int = 50) -> dict:
    """Lấy lịch sử phân tích bệnh da liễu của user."""
    from app.models.ai_result import AIResult
    from app.models.image import Image
    from app.models.classification_result import ClassificationResult

    query = (
        db.query(
            AIResult.id,
            Image.image_url,
            ClassificationResult.top1_label,
            ClassificationResult.top1_confidence,
            AIResult.status,
            AIResult.created_at,
        )
        .join(Image, AIResult.image_id == Image.id)
        .outerjoin(ClassificationResult, ClassificationResult.ai_result_id == AIResult.id)
        .filter(AIResult.user_id == user_id)
        .order_by(AIResult.created_at.desc())
    )

    total = query.count()
    items = query.offset(skip).limit(limit).all()

    return {
        "items": [
            {
                "id": item.id,
                "image_url": item.image_url,
                "top1_label": item.top1_label,
                "top1_confidence": item.top1_confidence,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "total": total,
    }
