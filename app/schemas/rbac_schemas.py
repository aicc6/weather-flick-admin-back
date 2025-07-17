"""
RBAC 관련 Pydantic 스키마
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


# Role 스키마
class RoleBase(BaseModel):
    name: str = Field(..., description="역할 이름 (영문)")
    display_name: str = Field(..., description="표시 이름")
    description: Optional[str] = Field(None, description="역할 설명")


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(RoleBase):
    id: int
    is_system: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Resource 스키마
class ResourceResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str]
    module: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Permission 스키마
class PermissionResponse(BaseModel):
    id: int
    name: str
    resource_id: int
    action: str
    description: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# 권한 할당 스키마
class PermissionAssignment(BaseModel):
    permission_ids: List[int] = Field(..., description="할당할 권한 ID 목록")


# 역할 할당 스키마
class AdminRoleAssignment(BaseModel):
    role_id: int = Field(..., description="할당할 역할 ID")


# 감사 로그 스키마
class AuditLogResponse(BaseModel):
    id: int
    admin_id: Optional[int]
    permission_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    success: bool
    failure_reason: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)