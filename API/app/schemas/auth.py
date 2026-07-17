from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Request schemas ──────────────────────────────────────────────────
class UserRegister(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    password: str
    date_of_birth: Optional[date] = None  # format: YYYY-MM-DD
    gender: Optional[str] = None  # "male" | "female" | "other"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenRefresh(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class GoogleLoginRequest(BaseModel):
    """Frontend gửi Google ID token (credential) lên để backend verify."""
    credential: str  # Google ID token từ Google Sign-In


# ── Response schemas ─────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: str = "local"
    role: str = "user"
    status: str = "active"
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str
