from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user_id, get_current_user
from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenRefresh,
    ChangePasswordRequest,
    GoogleLoginRequest,
    Token,
    UserResponse,
    MessageResponse,
)
from app.schemas.user import (
    UserUpdate,
    AvatarResponse,
    DiagnosisHistoryResponse,
)
from app.services.auth_service import (
    register_user,
    authenticate_user,
    refresh_access_token,
    get_user_profile,
    google_login,
    update_user_profile,
    change_user_password,
    upload_user_avatar,
    get_diagnosis_history,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Đăng ký tài khoản mới."""
    user = register_user(db, user_data)
    return user


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Đăng nhập và nhận access + refresh token."""
    tokens = authenticate_user(db, user_data.email, user_data.password)
    return tokens


@router.post("/google", response_model=Token)
async def login_google(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Đăng nhập bằng Google OAuth.

    Frontend gửi Google ID token (credential) lên.
    Backend verify với Google → tạo/tìm user → trả JWT tokens.
    """
    tokens = await google_login(db, data.credential)
    return tokens


@router.post("/refresh", response_model=Token)
def refresh(token_data: TokenRefresh, db: Session = Depends(get_db)):
    """Làm mới access token bằng refresh token."""
    tokens = refresh_access_token(db, token_data.refresh_token)
    return tokens


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin người dùng hiện tại (yêu cầu đăng nhập)."""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_me(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cập nhật thông tin cá nhân."""
    updated_user = update_user_profile(
        db, current_user, update_data.model_dump(exclude_unset=True)
    )
    return updated_user


@router.put("/me/password", response_model=MessageResponse)
def update_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the password for a local account."""
    change_user_password(
        db,
        current_user,
        password_data.current_password,
        password_data.new_password,
    )
    return {"message": "Đổi mật khẩu thành công"}


@router.put("/me/avatar", response_model=AvatarResponse)
async def update_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload avatar mới."""
    avatar_url = await upload_user_avatar(db, current_user, file)
    return {"avatar_url": avatar_url}


@router.get("/me/history", response_model=DiagnosisHistoryResponse)
def diagnosis_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy lịch sử phân tích bệnh da liễu."""
    return get_diagnosis_history(db, current_user.id, skip, limit)


@router.post("/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user)):
    """
    Đăng xuất.
    
    Hiện tại JWT là stateless nên chỉ cần FE xóa token.
    Endpoint này để FE có thể gọi cho clean flow.
    """
    return {"message": "Đăng xuất thành công"}
