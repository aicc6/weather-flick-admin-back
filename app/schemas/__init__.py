"""
스키마 패키지
모든 Pydantic 스키마를 포함합니다.
"""

from .common import (
    BaseResponse,
    EmptySuccessResponse,
    ErrorDetail,
    ErrorResponse,
    ErrorResponseModel,
    MessageResponse,
    MetaInfo,
    PaginatedResponse,
    SuccessResponse,
)
from .rbac_schemas import (
    RoleBase,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    ResourceResponse,
    PermissionResponse,
    PermissionAssignment,
    AdminRoleAssignment,
    AuditLogResponse,
)

__all__ = [
    "BaseResponse",
    "ErrorDetail",
    "ErrorResponse",
    "ErrorResponseModel",
    "EmptySuccessResponse",
    "MessageResponse",
    "MetaInfo",
    "PaginatedResponse",
    "SuccessResponse",
    # RBAC schemas
    "RoleBase",
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    "ResourceResponse",
    "PermissionResponse",
    "PermissionAssignment",
    "AdminRoleAssignment",
    "AuditLogResponse",
]
