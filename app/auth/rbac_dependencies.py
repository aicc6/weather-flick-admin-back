"""
RBAC 권한 체크를 위한 FastAPI dependency
"""
from typing import Callable
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_active_admin
from app.models_admin import Admin
from app.models_rbac import PermissionAuditLog


def require_permission(permission_name: str) -> Callable:
    """특정 권한을 요구하는 dependency 생성"""
    async def permission_checker(
        admin: Admin = Depends(get_current_active_admin),
        db: Session = Depends(get_db)
    ) -> Admin:
        # 슈퍼유저는 모든 권한 통과
        if admin.is_superuser:
            return admin
            
        # 권한 체크
        has_permission = False
        for role in admin.roles:
            if role.has_permission(permission_name):
                has_permission = True
                break
        
        if not has_permission:
            # 권한 실패 로그
            audit_log = PermissionAuditLog(
                admin_id=admin.admin_id,
                action=permission_name,
                success=False,
                failure_reason=f"Permission denied: {permission_name}"
            )
            db.add(audit_log)
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission_name}"
            )
        
        # 권한 성공 로그
        audit_log = PermissionAuditLog(
            admin_id=admin.admin_id,
            action=permission_name,
            success=True
        )
        db.add(audit_log)
        db.commit()
        
        return admin
    
    return permission_checker


async def require_super_admin(
    admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
) -> Admin:
    """슈퍼관리자 권한을 요구하는 dependency"""
    if not admin.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return admin