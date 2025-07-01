from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Admin
from app.auth.schemas import (
    AdminLogin, AdminCreate, AdminResponse,
    Token, LoginResponse, AdminListResponse,
    AdminStatusUpdate, AdminUpdate
)
from app.auth.utils import (
    verify_password, get_password_hash,
    create_admin_token
)
from app.auth.dependencies import get_current_active_admin
import math

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

    # 계정 상태 확인 - INACTIVE나 LOCKED 상태일 때만 차단
    if admin.status and admin.status in ["INACTIVE", "LOCKED"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )

    # 마지막 로그인 시간 업데이트
    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # JWT 토큰 생성
    access_token = create_admin_token(admin.admin_id, admin.email)

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

    # 새 관리자 생성 (login_count 제거, 기본값들 수정)
    new_admin = Admin(
        email=admin_create.email,
        password_hash=hashed_password,
        name=admin_create.name,
        phone=admin_create.phone,
        status="ACTIVE"
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

@router.get("/admins", response_model=AdminListResponse)
async def get_admin_list(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=100, description="페이지 크기"),
    status: Optional[str] = Query(None, description="상태 필터 (ACTIVE, INACTIVE, LOCKED)"),
    search: Optional[str] = Query(None, description="이메일 또는 이름으로 검색"),
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """관리자 목록 조회 (페이지네이션)"""

    # 기본 쿼리
    query = db.query(Admin)

    # 상태 필터
    if status:
        query = query.filter(Admin.status == status)

    # 검색 필터
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Admin.email.ilike(search_filter)) |
            (Admin.name.ilike(search_filter))
        )

    # 전체 개수 조회
    total = query.count()

    # 페이지네이션 적용
    offset = (page - 1) * size
    admins = query.order_by(Admin.created_at.desc()).offset(offset).limit(size).all()

    # 총 페이지 수 계산
    total_pages = math.ceil(total / size)

    return AdminListResponse(
        admins=[AdminResponse.model_validate(admin) for admin in admins],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )

@router.get("/admins/{admin_id}", response_model=AdminResponse)
async def get_admin_detail(
    admin_id: int,
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """특정 관리자 상세 조회"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="관리자를 찾을 수 없습니다"
        )

    return AdminResponse.model_validate(admin)

@router.put("/admins/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: int,
    admin_update: AdminUpdate,
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """관리자 정보 수정"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="관리자를 찾을 수 없습니다"
        )

    # 업데이트할 필드들 적용
    if admin_update.name is not None:
        admin.name = admin_update.name
    if admin_update.phone is not None:
        admin.phone = admin_update.phone
    if admin_update.status is not None:
        # 자기 자신의 상태는 변경할 수 없음
        if admin.admin_id == current_admin.admin_id and admin_update.status != admin.status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="자신의 계정 상태는 변경할 수 없습니다"
            )
        admin.status = admin_update.status

    # updated_at 필드 제거
    db.commit()
    db.refresh(admin)

    return AdminResponse.model_validate(admin)

@router.put("/admins/{admin_id}/status", response_model=AdminResponse)
async def update_admin_status(
    admin_id: int,
    status_update: AdminStatusUpdate,
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """관리자 상태 변경"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="관리자를 찾을 수 없습니다"
        )

    # 자기 자신의 상태는 변경할 수 없음
    if admin.admin_id == current_admin.admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 계정 상태는 변경할 수 없습니다"
        )

    # 상태 값 검증
    valid_statuses = ["ACTIVE", "INACTIVE", "LOCKED"]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 상태입니다. 가능한 값: {valid_statuses}"
        )

    admin.status = status_update.status
    # updated_at 필드 제거
    db.commit()
    db.refresh(admin)

    return AdminResponse.model_validate(admin)

@router.delete("/admins/{admin_id}")
async def deactivate_admin(
    admin_id: int,
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """관리자 계정 비활성화 (삭제 대신)"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="관리자를 찾을 수 없습니다"
        )

    # 자기 자신은 비활성화할 수 없음
    if admin.admin_id == current_admin.admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 계정은 비활성화할 수 없습니다"
        )

    # 이미 비활성화된 계정인지 확인
    if admin.status == "INACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 비활성화된 계정입니다"
        )

    admin.status = "INACTIVE"
    # updated_at 필드 제거
    db.commit()

    return {"message": f"관리자 '{admin.name}' 계정이 비활성화되었습니다"}

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

    # 계정 상태 확인 - INACTIVE나 LOCKED 상태일 때만 차단
    if admin.status and admin.status in ["INACTIVE", "LOCKED"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )

    # 마지막 로그인 시간 업데이트
    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()

    access_token = create_admin_token(admin.admin_id, admin.email)
    return Token(access_token=access_token)
