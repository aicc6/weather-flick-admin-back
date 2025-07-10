from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class UserBase(BaseModel):
    """사용자 기본 정보"""

    email: EmailStr
    nickname: str
    profile_image: str | None = None
    preferences: dict[str, Any] | None = None
    preferred_region: str | None = None
    preferred_theme: str | None = None
    bio: str | None = None


class UserCreate(UserBase):
    """사용자 생성 요청"""

    password: str = Field(..., min_length=8, description="비밀번호 (최소 8자)")
    role: UserRole = Field(default=UserRole.USER, description="사용자 역할")


class UserUpdate(BaseModel):
    """사용자 정보 수정 요청"""

    nickname: str | None = None
    profile_image: str | None = None
    preferences: dict[str, Any] | None = None
    preferred_region: str | None = None
    preferred_theme: str | None = None
    bio: str | None = None


class UserResponse(UserBase):
    """사용자 정보 응답"""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    is_active: bool
    is_email_verified: bool
    role: UserRole
    last_login: datetime | None = None
    login_count: int
    created_at: datetime
    updated_at: datetime


# UserListResponse는 이제 PaginatedResponse[UserResponse]로 대체됩니다.
# 호환성을 위해 임시로 유지하되, 향후 제거 예정
class UserListResponse(BaseModel):
    """사용자 목록 응답 (Deprecated: PaginatedResponse[UserResponse] 사용 권장)"""

    users: list[UserResponse]
    total: int
    page: int
    size: int
    total_pages: int


class UserDetailResponse(UserResponse):
    """사용자 상세 정보 응답 (관리자용)"""

    hashed_password: str = Field(..., description="해시된 비밀번호")


class UserStats(BaseModel):
    """사용자 통계"""

    total_users: int
    active_users: int
    verified_users: int
    admin_users: int
    recent_registrations: int  # 최근 30일
    recent_logins: int  # 최근 7일
    
    # 프론트엔드 호환성을 위한 추가 필드
    total: int
    active: int
    inactive: int
    verified: int
    admin: int


class UserSearchParams(BaseModel):
    """사용자 검색 파라미터"""

    email: str | None = None
    nickname: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    is_email_verified: bool | None = None
    preferred_region: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
