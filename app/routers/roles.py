"""
권한 및 역할 관리 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Role, AdminRole, Admin
from pydantic import BaseModel


router = APIRouter(prefix="/roles", tags=["Roles"])


class RoleResponse(BaseModel):
    """역할 정보 응답 스키마"""
    role_id: int
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class PermissionConstants(BaseModel):
    """권한 상수 정보 (프론트엔드 호환성)"""
    permissions: dict[str, str]
    roles: dict[str, str]
    role_permissions: dict[str, list[str]]
    permission_groups: dict[str, list[str]]


@router.get("/", response_model=List[RoleResponse])
def get_roles(
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """역할 목록 조회"""
    query = db.query(Role)
    
    if active_only:
        query = query.filter(Role.is_active == True)
    
    roles = query.order_by(Role.role_id).all()
    return roles


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(role_id: int, db: Session = Depends(get_db)):
    """특정 역할 정보 조회"""
    role = db.query(Role).filter(Role.role_id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="역할을 찾을 수 없습니다.")
    return role


@router.get("/admin/{admin_id}")
def get_admin_roles(admin_id: int, db: Session = Depends(get_db)):
    """특정 관리자의 역할 목록 조회"""
    admin_roles = (
        db.query(AdminRole, Role)
        .join(Role, AdminRole.role_id == Role.role_id)
        .filter(AdminRole.admin_id == admin_id)
        .filter(AdminRole.is_active == True)
        .filter(Role.is_active == True)
        .all()
    )
    
    roles = []
    for admin_role, role in admin_roles:
        roles.append({
            "role_id": role.role_id,
            "name": role.name,
            "display_name": role.display_name,
            "description": role.description,
            "assigned_at": admin_role.assigned_at,
            "is_active": admin_role.is_active
        })
    
    return {"admin_id": admin_id, "roles": roles}


@router.get("/constants/permissions", response_model=PermissionConstants)
def get_permission_constants():
    """권한 상수 정보 조회 (프론트엔드 호환성)"""
    # 하드코딩된 권한 정보를 DB 기반으로 변환
    permissions = {
        "USER_READ": "사용자 조회",
        "USER_WRITE": "사용자 생성/수정",
        "USER_DELETE": "사용자 삭제",
        "CONTENT_READ": "콘텐츠 조회",
        "CONTENT_WRITE": "콘텐츠 생성/수정",
        "CONTENT_DELETE": "콘텐츠 삭제",
        "ADMIN_READ": "관리자 조회",
        "ADMIN_WRITE": "관리자 생성/수정",
        "ADMIN_DELETE": "관리자 삭제",
        "SYSTEM_CONFIG": "시스템 설정",
        "SYSTEM_MONITOR": "시스템 모니터링",
        "DATA_EXPORT": "데이터 내보내기",
        "ANALYTICS_READ": "분석 데이터 조회",
        "LOG_READ": "로그 조회"
    }
    
    roles = {
        "SUPER_ADMIN": "슈퍼 관리자",
        "ADMIN": "관리자", 
        "CONTENT_MANAGER": "콘텐츠 관리자",
        "DATA_ANALYST": "데이터 분석가",
        "MODERATOR": "모더레이터",
        "SUPPORT": "고객 지원"
    }
    
    role_permissions = {
        "SUPER_ADMIN": list(permissions.keys()),
        "ADMIN": [
            "USER_READ", "USER_WRITE", "USER_DELETE",
            "CONTENT_READ", "CONTENT_WRITE", "CONTENT_DELETE",
            "ADMIN_READ", "ADMIN_WRITE",
            "SYSTEM_MONITOR", "DATA_EXPORT", "ANALYTICS_READ", "LOG_READ"
        ],
        "CONTENT_MANAGER": [
            "USER_READ", "CONTENT_READ", "CONTENT_WRITE", "CONTENT_DELETE",
            "ANALYTICS_READ", "LOG_READ"
        ],
        "DATA_ANALYST": [
            "USER_READ", "CONTENT_READ", "ANALYTICS_READ", "DATA_EXPORT", "LOG_READ"
        ],
        "MODERATOR": [
            "USER_READ", "USER_WRITE", "CONTENT_READ", "CONTENT_WRITE", "LOG_READ"
        ],
        "SUPPORT": [
            "USER_READ", "USER_WRITE", "CONTENT_READ", "LOG_READ"
        ]
    }
    
    permission_groups = {
        "사용자 관리": ["USER_READ", "USER_WRITE", "USER_DELETE"],
        "콘텐츠 관리": ["CONTENT_READ", "CONTENT_WRITE", "CONTENT_DELETE"],
        "관리자 관리": ["ADMIN_READ", "ADMIN_WRITE", "ADMIN_DELETE"],
        "시스템 관리": ["SYSTEM_CONFIG", "SYSTEM_MONITOR"],
        "데이터 관리": ["DATA_EXPORT", "ANALYTICS_READ", "LOG_READ"]
    }
    
    return PermissionConstants(
        permissions=permissions,
        roles=roles,
        role_permissions=role_permissions,
        permission_groups=permission_groups
    )