from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Admin
from app.auth.schemas import (
    AdminLogin, AdminCreate, AdminResponse,
    Token, LoginResponse
)
from app.auth.utils import (
    verify_password, get_password_hash,
    create_admin_token
)
from app.auth.dependencies import get_current_active_admin

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
async def login(
    admin_login: AdminLogin,
    db: Session = Depends(get_db)
):
    """관리자 로그인"""
    # 이메일로 관리자 조회
    admin = db.query(Admin).filter(Admin.email == admin_login.email).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다"
        )

    # 비밀번호 검증
    if not verify_password(admin_login.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다"
        )

    # 계정 상태 확인 (문자열로 비교)
    if admin.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )

    # 마지막 로그인 시간 업데이트 및 로그인 횟수 증가
    admin.last_login_at = datetime.now(timezone.utc)
    admin.updated_at = datetime.now(timezone.utc)
    if admin.login_count is None:
        admin.login_count = 1
    else:
        admin.login_count += 1
    db.commit()

    # JWT 토큰 생성 (id 사용)
    access_token = create_admin_token(admin.id, admin.email)

    return LoginResponse(
        admin=AdminResponse.model_validate(admin),
        token=Token(access_token=access_token)
    )

@router.post("/register", response_model=AdminResponse)
async def register(
    admin_create: AdminCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """새 관리자 계정 등록 (기존 관리자만 가능)"""
    # 이메일 중복 확인
    existing_admin = db.query(Admin).filter(Admin.email == admin_create.email).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 이메일입니다"
        )

    # 비밀번호 해싱
    hashed_password = get_password_hash(admin_create.password)

    # 새 관리자 생성
    new_admin = Admin(
        email=admin_create.email,
        password_hash=hashed_password,
        name=admin_create.name,
        phone=admin_create.phone,
        status="ACTIVE",  # 문자열로 설정
        login_count=0
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return AdminResponse.model_validate(new_admin)

@router.get("/me", response_model=AdminResponse)
async def get_current_admin_profile(
    current_admin: Admin = Depends(get_current_active_admin)
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
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 호환 로그인 (Swagger UI용)"""
    admin = db.query(Admin).filter(Admin.email == form_data.username).first()

    if not admin or not verify_password(form_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if admin.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )

    # 마지막 로그인 시간 업데이트 및 로그인 횟수 증가
    admin.last_login_at = datetime.now(timezone.utc)
    admin.updated_at = datetime.now(timezone.utc)
    if admin.login_count is None:
        admin.login_count = 1
    else:
        admin.login_count += 1
    db.commit()

    access_token = create_admin_token(admin.id, admin.email)
    return Token(access_token=access_token)
