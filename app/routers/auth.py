from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_active_admin
from ..auth.utils import create_admin_token, verify_password
from ..database import get_db
from ..models import Admin, AdminStatus
from ..schemas.auth_schemas import (
    AdminLogin,
    AdminResponse,
    LoginResponse,
    Token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(admin_login: AdminLogin, db: Session = Depends(get_db)):
    """관리자 로그인"""
    # 이메일로 관리자 조회
    admin = db.query(Admin).filter(Admin.email == admin_login.email).first()

    if not admin or not verify_password(admin_login.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )

    # 계정 상태 확인 - INACTIVE 상태일 때만 차단
    if admin.status and admin.status == AdminStatus.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 계정입니다"
        )

    # 마지막 로그인 시간 업데이트
    admin.last_login_at = datetime.now(UTC)
    db.commit()

    # JWT 토큰 생성
    access_token = create_admin_token(admin.admin_id, admin.email)

    return LoginResponse(
        admin=AdminResponse.model_validate(admin),
        token=Token(access_token=access_token),
    )


@router.get("/me", response_model=AdminResponse)
async def get_current_admin_profile(
    current_admin: Admin = Depends(get_current_active_admin),
):
    """현재 관리자 프로필 조회"""
    return AdminResponse.model_validate(current_admin)


@router.post("/logout")
async def logout():
    """로그아웃 (클라이언트에서 토큰 삭제)"""
    return {"message": "로그아웃되었습니다"}


# OAuth2 호환 로그인 엔드포인트 (Swagger UI 지원)
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """OAuth2 호환 로그인 (Swagger UI용)"""
    admin = db.query(Admin).filter(Admin.email == form_data.username).first()

    if not admin or not verify_password(form_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 계정 상태 확인 - INACTIVE 상태일 때만 차단
    if admin.status and admin.status == AdminStatus.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 계정입니다"
        )

    # 마지막 로그인 시간 업데이트
    admin.last_login_at = datetime.now(UTC)
    db.commit()

    access_token = create_admin_token(admin.admin_id, admin.email)
    return Token(access_token=access_token)
