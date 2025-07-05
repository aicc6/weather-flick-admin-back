from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Admin, AdminStatus
from .schemas import (
    AdminCreate,
    AdminResponse,
    AdminListResponse,
    AdminStatusUpdate,
    AdminUpdate,
)
from ..auth.utils import get_password_hash, generate_temporary_password
from ..auth.dependencies import get_current_active_admin
import math

router = APIRouter(prefix="/admins", tags=["Admin Management"])


@router.post("/", response_model=AdminResponse)
async def create_admin(
    admin_create: AdminCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin),
):
    """새 관리자 계정 생성 (기존 관리자만 가능)"""
    # 이메일 중복 확인
    existing_admin = db.query(Admin).filter(Admin.email == admin_create.email).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 이메일입니다",
        )

    # 비밀번호 해싱
    hashed_password = get_password_hash(admin_create.password)

    # 새 관리자 생성
    new_admin = Admin(
        email=admin_create.email,
        password_hash=hashed_password,
        name=admin_create.name,
        phone=admin_create.phone,
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return AdminResponse.model_validate(new_admin)


@router.get("/", response_model=AdminListResponse)
async def get_admin_list(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=100, description="페이지 크기"),
    status: Optional[str] = Query(
        None, description="상태 필터 (ACTIVE, INACTIVE, LOCKED)"
    ),
    search: Optional[str] = Query(None, description="이메일 또는 이름으로 검색"),
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
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
            (Admin.email.ilike(search_filter)) | (Admin.name.ilike(search_filter))
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
        total_pages=total_pages,
    )


@router.get("/stats")
async def get_admin_statistics(
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """관리자 통계 조회"""
    try:
        total = db.query(Admin).count()
        active = db.query(Admin).filter(Admin.status == AdminStatus.ACTIVE).count()
        inactive = db.query(Admin).filter(Admin.status == AdminStatus.INACTIVE).count()
        
        return {
            "total": total,
            "active": active,
            "inactive": inactive
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="관리자 통계 조회 중 오류가 발생했습니다"
        )


@router.get("/{admin_id}", response_model=AdminResponse)
async def get_admin_detail(
    admin_id: int,
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """특정 관리자 상세 조회"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다"
        )

    return AdminResponse.model_validate(admin)


@router.put("/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: int,
    admin_update: AdminUpdate,
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """관리자 정보 수정"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다"
        )

    # 업데이트할 필드들 적용
    if admin_update.name is not None:
        admin.name = admin_update.name
    if admin_update.phone is not None:
        admin.phone = admin_update.phone
    if admin_update.status is not None:
        # 자기 자신의 상태는 변경할 수 없음
        if (
            admin.admin_id == current_admin.admin_id
            and admin_update.status != admin.status
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="자신의 계정 상태는 변경할 수 없습니다",
            )
        admin.status = admin_update.status

    db.commit()
    db.refresh(admin)

    return AdminResponse.model_validate(admin)


@router.put("/{admin_id}/status", response_model=AdminResponse)
async def update_admin_status(
    admin_id: int,
    status_update: AdminStatusUpdate,
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """관리자 상태 변경"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다"
        )

    # 자기 자신의 상태는 변경할 수 없음
    if admin.admin_id == current_admin.admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 계정 상태는 변경할 수 없습니다",
        )

    # 상태 값 검증
    valid_statuses = ["ACTIVE", "INACTIVE", "LOCKED"]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 상태입니다. 가능한 값: {valid_statuses}",
        )

    admin.status = status_update.status
    db.commit()
    db.refresh(admin)

    return AdminResponse.model_validate(admin)


@router.delete("/{admin_id}")
async def deactivate_admin(
    admin_id: int,
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """관리자 계정 비활성화 (삭제 대신)"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다"
        )

    # 자기 자신은 비활성화할 수 없음
    if admin.admin_id == current_admin.admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 계정은 비활성화할 수 없습니다",
        )

    # 이미 비활성화된 계정인지 확인
    if admin.status == AdminStatus.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="이미 비활성화된 계정입니다"
        )

    admin.status = AdminStatus.INACTIVE
    db.commit()

    return {"message": f"관리자 '{admin.name}' 계정이 비활성화되었습니다"}


@router.delete("/{admin_id}/permanent")
async def delete_admin_permanently(
    admin_id: int,
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """관리자 계정 완전 삭제 (superadmin만 가능)"""
    # superadmin 권한 확인
    if current_admin.email != "admin@weatherflick.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 삭제는 슈퍼 관리자만 가능합니다"
        )
    
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다"
        )

    # 자기 자신은 삭제할 수 없음
    if admin.admin_id == current_admin.admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 계정은 삭제할 수 없습니다",
        )

    admin_name = admin.name or admin.email
    db.delete(admin)
    db.commit()

    return {"message": f"관리자 '{admin_name}' 계정이 완전히 삭제되었습니다"}


@router.post("/{admin_id}/reset-password")
async def reset_admin_password(
    admin_id: int,
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """관리자 비밀번호 초기화"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다"
        )

    # 보안 강화된 임시 비밀번호 생성
    temp_password = generate_temporary_password()
    admin.password_hash = get_password_hash(temp_password)
    
    db.commit()

    return {
        "message": f"관리자 '{admin.name or admin.email}' 비밀번호가 초기화되었습니다",
        "admin_id": admin_id,
        "temporary_password": temp_password
    }