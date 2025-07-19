"""
인증 및 권한 관련 의존성
"""

from functools import wraps
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models_admin import Admin, AdminStatus
from app.models_rbac import PermissionAuditLog

security = HTTPBearer()


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Admin:
    """현재 인증된 관리자 반환"""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        admin_id: str = payload.get("sub")
        email: str = payload.get("email")
        if admin_id is None or email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    admin = (
        db.query(Admin)
        .options(joinedload(Admin.roles))
        .filter(Admin.admin_id == int(admin_id))
        .first()
    )
    if admin is None:
        raise credentials_exception

    # 비활성 계정 체크
    if admin.status != AdminStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active"
        )

    return admin


# 타입 어노테이션을 위한 CurrentAdmin
CurrentAdmin = Annotated[Admin, Depends(get_current_admin)]


def require_permission(permission_name: str):
    """특정 권한을 요구하는 데코레이터"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # FastAPI dependency injection에서 admin 객체 찾기
            admin = None
            db = None

            # kwargs에서 admin과 db 찾기
            for key, value in kwargs.items():
                if isinstance(value, Admin):
                    admin = value
                elif hasattr(value, "query"):  # Session 객체인지 확인
                    db = value

            if not admin:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # 권한 체크
            if not admin.has_permission(permission_name):
                # 권한 실패 로그 기록
                if db:
                    audit_log = PermissionAuditLog(
                        admin_id=admin.admin_id,
                        action="access_denied",
                        resource_type=permission_name.split(".")[0],
                        success=False,
                        failure_reason=f"Missing permission: {permission_name}",
                    )
                    db.add(audit_log)
                    db.commit()

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required: {permission_name}",
                )

            # 권한 성공 로그 기록
            if db:
                audit_log = PermissionAuditLog(
                    admin_id=admin.admin_id,
                    action="access_granted",
                    resource_type=permission_name.split(".")[0],
                    success=True,
                )
                db.add(audit_log)
                db.commit()

            # 원래 함수 실행
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(*permission_names: str):
    """여러 권한 중 하나라도 있으면 허용하는 데코레이터"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # FastAPI dependency injection에서 admin 객체 찾기
            admin = None
            db = None

            for key, value in kwargs.items():
                if isinstance(value, Admin):
                    admin = value
                elif hasattr(value, "query"):  # Session 객체인지 확인
                    db = value

            if not admin:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # 권한 중 하나라도 있는지 체크
            has_any_permission = any(
                admin.has_permission(perm) for perm in permission_names
            )

            if not has_any_permission:
                # 권한 실패 로그 기록
                if db:
                    audit_log = PermissionAuditLog(
                        admin_id=admin.admin_id,
                        action="access_denied",
                        resource_type=permission_names[0].split(".")[0],
                        success=False,
                        failure_reason=f"Missing any of permissions: {', '.join(permission_names)}",
                    )
                    db.add(audit_log)
                    db.commit()

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required one of: {', '.join(permission_names)}",
                )

            # 권한 성공 로그 기록
            if db:
                # 실제 사용된 권한 찾기
                used_permission = next(
                    perm for perm in permission_names if admin.has_permission(perm)
                )

                audit_log = PermissionAuditLog(
                    admin_id=admin.admin_id,
                    action="access_granted",
                    resource_type=used_permission.split(".")[0],
                    success=True,
                )
                db.add(audit_log)
                db.commit()

            # 원래 함수 실행
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_all_permissions(*permission_names: str):
    """모든 권한을 요구하는 데코레이터"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # FastAPI dependency injection에서 admin 객체 찾기
            admin = None
            db = None

            for key, value in kwargs.items():
                if isinstance(value, Admin):
                    admin = value
                elif hasattr(value, "query"):  # Session 객체인지 확인
                    db = value

            if not admin:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # 모든 권한이 있는지 체크
            missing_permissions = [
                perm for perm in permission_names if not admin.has_permission(perm)
            ]

            if missing_permissions:
                # 권한 실패 로그 기록
                if db:
                    audit_log = PermissionAuditLog(
                        admin_id=admin.admin_id,
                        action="access_denied",
                        resource_type=permission_names[0].split(".")[0],
                        success=False,
                        failure_reason=f"Missing permissions: {', '.join(missing_permissions)}",
                    )
                    db.add(audit_log)
                    db.commit()

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Missing: {', '.join(missing_permissions)}",
                )

            # 권한 성공 로그 기록
            if db:
                audit_log = PermissionAuditLog(
                    admin_id=admin.admin_id,
                    action="access_granted",
                    resource_type=permission_names[0].split(".")[0],
                    success=True,
                )
                db.add(audit_log)
                db.commit()

            # 원래 함수 실행
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# 권한 검사를 위한 의존성 함수
def check_permission(permission_name: str):
    """특정 권한을 확인하는 의존성 함수"""
    async def permission_checker(
        current_admin: Admin = Depends(get_current_admin),
        db: Session = Depends(get_db)
    ):
        if not current_admin.has_permission(permission_name):
            # 권한 실패 로그 기록
            audit_log = PermissionAuditLog(
                admin_id=current_admin.admin_id,
                action="access_denied",
                resource_type=permission_name.split(".")[0],
                success=False,
                failure_reason=f"Missing permission: {permission_name}",
            )
            db.add(audit_log)
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {permission_name}",
            )
        
        # 권한 성공 로그 기록
        audit_log = PermissionAuditLog(
            admin_id=current_admin.admin_id,
            action="access_granted",
            resource_type=permission_name.split(".")[0],
            success=True,
        )
        db.add(audit_log)
        db.commit()
        
        return current_admin
    
    return permission_checker

# 자주 사용되는 권한 조합을 위한 헬퍼 데코레이터
def require_super_admin(func):
    """슈퍼관리자 권한 요구"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        admin = None
        for key, value in kwargs.items():
            if isinstance(value, Admin):
                admin = value
                break

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        if not admin.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super admin permission required",
            )

        return await func(*args, **kwargs)

    return wrapper
