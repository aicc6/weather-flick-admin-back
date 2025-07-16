"""
RBAC (Role-Based Access Control) 관리 API
"""

from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_active_admin
from app.auth.rbac_dependencies import require_permission, require_super_admin
from app.models_admin import Admin
from app.models_rbac import Role, Resource, Permission, PermissionAuditLog
from app.models_rbac import admin_roles, role_permissions
from app.schemas.rbac_schemas import (
    RoleCreate, RoleUpdate, RoleResponse,
    PermissionResponse, ResourceResponse,
    AdminRoleAssignment, PermissionAssignment
)

router = APIRouter(
    prefix="/rbac",
    tags=["RBAC"],
    responses={404: {"description": "Not found"}},
)


@router.get("/my-permissions")
async def get_my_permissions(
    admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """현재 로그인한 관리자의 권한 목록 조회"""
    # 관리자의 모든 권한 수집
    all_permissions = set()
    roles_data = []
    
    if admin.is_superuser:
        # 슈퍼유저는 모든 권한
        all_permissions = db.query(Permission).all()
        permissions_list = [{
            "id": p.id,
            "name": p.name,
            "resource": p.resource.name if p.resource else None,
            "action": p.action
        } for p in all_permissions]
    else:
        # 일반 관리자는 역할에 할당된 권한만
        for role in admin.roles:
            roles_data.append({
                "id": role.id,
                "name": role.name,
                "display_name": role.display_name
            })
            all_permissions.update(role.permissions)
        
        permissions_list = [{
            "id": p.id,
            "name": p.name,
            "resource": p.resource.name if p.resource else None,
            "action": p.action
        } for p in all_permissions]
    
    return {
        "admin_id": admin.admin_id,
        "email": admin.email,
        "is_superuser": admin.is_superuser,
        "roles": roles_data,
        "permissions": permissions_list
    }


@router.get("/roles", response_model=List[RoleResponse])
async def get_roles(
    admin: Admin = Depends(require_permission("roles.read")),
    db: Session = Depends(get_db),
):
    """역할 목록 조회"""
    roles = db.query(Role).all()
    return roles


@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    admin: Admin = Depends(require_permission("roles.write")),
    db: Session = Depends(get_db),
):
    """새 역할 생성"""
    # 역할명 중복 체크
    existing_role = db.query(Role).filter(Role.name == role_data.name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role_data.name}' already exists"
        )
    
    new_role = Role(
        name=role_data.name,
        display_name=role_data.display_name,
        description=role_data.description,
        is_system=False
    )
    
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    return new_role


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    admin: Admin = Depends(require_permission("roles.write")),
    db: Session = Depends(get_db),
):
    """역할 정보 수정"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # 시스템 역할은 수정 불가
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System roles cannot be modified"
        )
    
    if role_data.display_name:
        role.display_name = role_data.display_name
    if role_data.description:
        role.description = role_data.description
    
    db.commit()
    db.refresh(role)
    
    return role


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    admin: Admin = Depends(require_permission("roles.delete")),
    db: Session = Depends(get_db),
):
    """역할 삭제"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # 시스템 역할은 삭제 불가
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System roles cannot be deleted"
        )
    
    # 해당 역할을 가진 관리자가 있는지 확인
    admin_count = db.execute(
        admin_roles.select().where(admin_roles.c.role_id == role_id)
    ).fetchone()
    
    if admin_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete role that is assigned to admins"
        )
    
    db.delete(role)
    db.commit()
    
    return {"message": "Role deleted successfully"}


@router.post("/roles/{role_id}/permissions")
async def assign_permissions_to_role(
    role_id: int,
    assignment: PermissionAssignment,
    admin: Admin = Depends(require_permission("roles.write")),
    db: Session = Depends(get_db),
):
    """역할에 권한 할당"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # 권한 존재 여부 확인
    permissions = db.query(Permission).filter(
        Permission.id.in_(assignment.permission_ids)
    ).all()
    
    if len(permissions) != len(assignment.permission_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some permissions not found"
        )
    
    # 기존 권한 제거
    db.execute(
        role_permissions.delete().where(role_permissions.c.role_id == role_id)
    )
    
    # 새 권한 할당
    for permission in permissions:
        db.execute(
            role_permissions.insert().values(
                role_id=role_id,
                permission_id=permission.id
            )
        )
    
    db.commit()
    
    return {
        "message": "Permissions assigned successfully",
        "role_id": role_id,
        "permission_count": len(permissions)
    }


@router.get("/resources", response_model=List[ResourceResponse])
async def get_resources(
    admin: Admin = Depends(require_permission("system.read")),
    db: Session = Depends(get_db),
):
    """리소스 목록 조회"""
    resources = db.query(Resource).all()
    return resources


@router.get("/permissions", response_model=List[PermissionResponse])
async def get_permissions(
    admin: Admin = Depends(require_permission("system.read")),
    db: Session = Depends(get_db),
    resource_id: Optional[int] = None,
):
    """권한 목록 조회"""
    query = db.query(Permission)
    
    if resource_id:
        query = query.filter(Permission.resource_id == resource_id)
    
    permissions = query.all()
    return permissions


@router.post("/admins/{admin_id}/roles")
async def assign_role_to_admin(
    admin_id: int,
    assignment: AdminRoleAssignment,
    current_admin: Admin = Depends(require_permission("roles.write")),
    db: Session = Depends(get_db),
):
    """관리자에게 역할 할당"""
    target_admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()
    if not target_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    role = db.query(Role).filter(Role.id == assignment.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # 이미 할당된 역할인지 확인
    existing = db.execute(
        admin_roles.select().where(
            (admin_roles.c.admin_id == admin_id) &
            (admin_roles.c.role_id == assignment.role_id)
        )
    ).fetchone()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already assigned to this admin"
        )
    
    # 역할 할당
    db.execute(
        admin_roles.insert().values(
            admin_id=admin_id,
            role_id=assignment.role_id,
            assigned_by=current_admin.admin_id
        )
    )
    
    db.commit()
    
    return {
        "message": "Role assigned successfully",
        "admin_id": admin_id,
        "role": role.display_name
    }


@router.delete("/admins/{admin_id}/roles/{role_id}")
async def remove_role_from_admin(
    admin_id: int,
    role_id: int,
    current_admin: Admin = Depends(require_permission("roles.write")),
    db: Session = Depends(get_db),
):
    """관리자로부터 역할 제거"""
    # 역할 할당 여부 확인
    existing = db.execute(
        admin_roles.select().where(
            (admin_roles.c.admin_id == admin_id) &
            (admin_roles.c.role_id == role_id)
        )
    ).fetchone()
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found"
        )
    
    # 슈퍼관리자의 super_admin 역할은 제거 불가
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()
    role = db.query(Role).filter(Role.id == role_id).first()
    
    if admin and admin.is_superuser and role and role.name == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot remove super_admin role from superuser"
        )
    
    # 역할 제거
    db.execute(
        admin_roles.delete().where(
            (admin_roles.c.admin_id == admin_id) &
            (admin_roles.c.role_id == role_id)
        )
    )
    
    db.commit()
    
    return {"message": "Role removed successfully"}


@router.get("/audit-logs")
async def get_permission_audit_logs(
    admin: Admin = Depends(require_permission("logs.read")),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 50,
    admin_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """권한 사용 감사 로그 조회"""
    query = db.query(PermissionAuditLog)
    
    if admin_id:
        query = query.filter(PermissionAuditLog.admin_id == admin_id)
    
    if start_date:
        query = query.filter(PermissionAuditLog.created_at >= start_date)
    
    if end_date:
        query = query.filter(PermissionAuditLog.created_at <= end_date)
    
    # 페이지네이션
    total = query.count()
    logs = query.order_by(PermissionAuditLog.created_at.desc())\
                .offset((page - 1) * page_size)\
                .limit(page_size)\
                .all()
    
    return {
        "logs": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }