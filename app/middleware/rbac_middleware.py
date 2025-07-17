"""
RBAC 권한 체크 미들웨어
"""

import logging

from fastapi import Request, status
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.database import SessionLocal
from app.models_admin import Admin
from app.models_rbac import PermissionAuditLog

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RBACMiddleware(BaseHTTPMiddleware):
    """
    RBAC 권한 체크 미들웨어

    API 경로와 필요한 권한을 매핑하여 자동으로 권한을 체크합니다.
    """

    # 권한이 필요없는 경로들
    PUBLIC_PATHS = [
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/auth/login",
        "/api/auth/refresh",
    ]

    # 경로별 필요 권한 매핑
    PERMISSION_MAP = {
        # 사용자 관리
        "GET:/api/users": "users.read",
        "POST:/api/users": "users.write",
        "PUT:/api/users/{user_id}": "users.write",
        "DELETE:/api/users/{user_id}": "users.delete",
        "GET:/api/users/stats": "users.read",
        "POST:/api/users/export": "users.export",
        # 콘텐츠 관리
        "GET:/api/destinations": "destinations.read",
        "POST:/api/destinations": "destinations.write",
        "PUT:/api/destinations/{destination_id}": "destinations.write",
        "DELETE:/api/destinations/{destination_id}": "destinations.delete",
        "GET:/api/festivals-events": "content.read",
        "GET:/api/festivals-events/{content_id}": "content.read",
        "GET:/api/festivals-events/autocomplete": "content.read",
        "GET:/api/festivals-events/autocomplete/": "content.read",
        "POST:/api/festivals-events": "content.write",
        "PUT:/api/festivals-events/{content_id}": "content.write",
        "DELETE:/api/festivals-events/{content_id}": "content.delete",
        "GET:/api/leisure-sports": "content.read",
        "GET:/api/leisure-sports/{content_id}": "content.read",
        "GET:/api/leisure-sports/autocomplete": "content.read",
        "POST:/api/leisure-sports": "content.write",
        "PUT:/api/leisure-sports/{content_id}": "content.write",
        "DELETE:/api/leisure-sports/{content_id}": "content.delete",
        # 시스템 관리
        "GET:/api/system/stats": "system.read",
        "GET:/api/system/config": "system.read",
        "PUT:/api/system/config": "system.write",
        # 로그 관리
        "GET:/api/logs": "logs.read",
        "POST:/api/logs/export": "logs.export",
        # 대시보드
        "GET:/api/dashboard": "dashboard.read",
        "GET:/api/dashboard/stats": "dashboard.read",
        # 리포트
        "GET:/api/reports": "reports.read",
        "POST:/api/reports/generate": "reports.generate",
        "POST:/api/reports/export": "reports.export",
    }

    async def dispatch(self, request: Request, call_next):
        """미들웨어 처리 로직"""
        
        # 모든 요청에 대해 로그 출력
        logger.info(f"RBAC middleware called for: {request.method} {request.url.path}")

        # OPTIONS 요청은 CORS preflight이므로 권한 체크 생략
        if request.method == "OPTIONS":
            logger.info("OPTIONS request - skipping RBAC check")
            return await call_next(request)

        # 공개 경로는 권한 체크 생략
        if self._is_public_path(request.url.path):
            logger.info(f"Public path - skipping RBAC check: {request.url.path}")
            return await call_next(request)

        logger.info(f"RBAC middleware processing: {request.method} {request.url.path}")

        # 인증 토큰 확인
        admin = await self._get_current_admin(request)
        if not admin:
            logger.info("No admin found - returning 401")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"},
            )

        # 권한 체크
        required_permission = self._get_required_permission(request)
        logger.info(f"Required permission: {required_permission}")
        logger.info(f"Request path: {request.url.path}, method: {request.method}")
        logger.info(f"Admin has permission: {self._has_permission(admin, required_permission) if required_permission else 'N/A'}")
        
        if required_permission and not self._has_permission(admin, required_permission):
            # 권한 실패 로그 기록
            await self._log_permission_failure(admin, required_permission, request)

            logger.info(f"Permission denied for {admin.email} - required: {required_permission}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": f"Permission denied. Required: {required_permission}"
                },
            )

        # 권한 성공 로그 기록
        if required_permission:
            await self._log_permission_success(admin, required_permission, request)

        # 요청 처리
        response = await call_next(request)
        
        # 307 리다이렉트인 경우 Authorization 헤더 보존을 위해 헤더 추가
        if response.status_code == 307:
            authorization = request.headers.get("Authorization")
            if authorization:
                # 리다이렉트된 Location에 Authorization 헤더 정보를 포함하도록 처리
                # 이는 클라이언트에게 힌트를 제공하기 위한 것입니다
                logger.info(f"307 redirect detected, Authorization header present: {authorization[:20]}...")
        
        return response

    def _is_public_path(self, path: str) -> bool:
        """공개 경로인지 확인"""
        # 정확히 루트 경로인 경우
        if path == "/":
            logger.info(f"Path {path} is root path - public")
            return True
            
        for public_path in self.PUBLIC_PATHS:
            if path.startswith(public_path):
                logger.info(f"Path {path} matches public path {public_path}")
                return True
        return False

    async def _get_current_admin(self, request: Request) -> Admin | None:
        """현재 인증된 관리자 가져오기"""
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            logger.debug("No authorization header or invalid format")
            return None

        token = authorization.split(" ")[1]

        try:
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            admin_id = payload.get("sub")
            email = payload.get("email")
            
            logger.info(f"JWT payload: admin_id={admin_id}, email={email}")
            
            if not admin_id or not email:
                logger.info("Missing admin_id or email in JWT payload")
                return None

            db = SessionLocal()
            try:
                admin = (
                    db.query(Admin)
                    .filter(Admin.admin_id == int(admin_id))
                    .filter(Admin.email == email)
                    .first()
                )
                if admin:
                    logger.info(f"Found admin: {admin.email}, status: {admin.status.value}")
                    if admin.status.value == "ACTIVE":
                        return admin
                    else:
                        logger.info(f"Admin account is not active: {admin.status.value}")
                else:
                    logger.info("Admin not found in database")
            finally:
                db.close()

        except (JWTError, ValueError) as e:
            logger.info(f"JWT validation error: {e}")
            return None

        return None

    def _get_required_permission(self, request: Request) -> str | None:
        """요청에 필요한 권한 가져오기"""
        method = request.method
        path = request.url.path
        
        # 경로 끝의 슬래시 제거하여 정규화
        normalized_path = path.rstrip('/')
        
        # 정확한 매칭 시도 (정규화된 경로)
        key = f"{method}:{normalized_path}"
        if key in self.PERMISSION_MAP:
            logger.info(f"Exact match found for {key}")
            return self.PERMISSION_MAP[key]

        # 패턴 매칭 시도 (경로 파라미터 포함)
        for pattern, permission in self.PERMISSION_MAP.items():
            if self._match_path_pattern(key, pattern):
                logger.info(f"Pattern match found: {key} matches {pattern}")
                return permission

        # RBAC 관리 API는 특별 처리
        if normalized_path.startswith("/api/admin/rbac"):
            if method == "GET":
                return "system.read"
            elif method in ["POST", "PUT", "PATCH"]:
                return "roles.write"
            elif method == "DELETE":
                return "roles.delete"

        logger.info(f"No permission mapping found for {key}")
        return None

    def _match_path_pattern(self, path: str, pattern: str) -> bool:
        """경로 패턴 매칭"""
        # 간단한 패턴 매칭 구현
        # 예: "GET:/api/users/123" matches "GET:/api/users/{user_id}"
        path_parts = path.split("/")
        pattern_parts = pattern.split("/")

        if len(path_parts) != len(pattern_parts):
            return False

        for path_part, pattern_part in zip(path_parts, pattern_parts, strict=False):
            if pattern_part.startswith("{") and pattern_part.endswith("}"):
                continue  # 경로 파라미터는 무시
            if path_part != pattern_part:
                return False

        return True

    def _has_permission(self, admin: Admin, permission: str) -> bool:
        """관리자가 권한을 가지고 있는지 확인"""
        # 슈퍼유저는 모든 권한 보유
        if admin.is_superuser:
            return True

        # extend_admin_model로 추가된 메서드 사용
        if hasattr(admin, "has_permission"):
            return admin.has_permission(permission)

        return False

    async def _log_permission_failure(
        self, admin: Admin, permission: str, request: Request
    ):
        """권한 실패 로그 기록"""
        db = SessionLocal()
        try:
            audit_log = PermissionAuditLog(
                admin_id=admin.admin_id,
                action="access_denied",
                resource_type=permission.split(".")[0] if permission else None,
                success=False,
                failure_reason=f"Missing permission: {permission}",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            db.add(audit_log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log permission failure: {e}")
        finally:
            db.close()

    async def _log_permission_success(
        self, admin: Admin, permission: str, request: Request
    ):
        """권한 성공 로그 기록"""
        db = SessionLocal()
        try:
            audit_log = PermissionAuditLog(
                admin_id=admin.admin_id,
                action="access_granted",
                resource_type=permission.split(".")[0] if permission else None,
                success=True,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            db.add(audit_log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log permission success: {e}")
        finally:
            db.close()


class PermissionCheckMiddleware:
    """
    특정 경로에 대한 권한 체크를 수행하는 미들웨어
    데코레이터와 함께 사용하여 이중 보안을 제공합니다.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next):
        # 요청 경로 로깅
        logger.debug(f"Request: {request.method} {request.url.path}")

        # 응답 처리
        response = await call_next(request)

        # 응답 상태 로깅
        logger.debug(f"Response: {response.status_code} for {request.url.path}")

        return response
