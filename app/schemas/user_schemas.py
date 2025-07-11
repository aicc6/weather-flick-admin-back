from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class UserBase(BaseModel):
    """사용자 기본 정보"""
    email: EmailStr
    nickname: str
    profile_image: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    preferred_region: Optional[str] = None
    preferred_theme: Optional[str] = None
    bio: Optional[str] = None

    @field_validator('preferences', mode='before')
    @classmethod
    def validate_preferences(cls, v):
        """preferences 필드 검증 - 빈 배열이나 None을 빈 딕셔너리로 변환"""
        if v is None or v == []:
            return {}
        if isinstance(v, list):
            # 리스트가 비어있지 않은 경우에도 빈 딕셔너리로 변환
            return {}
        return v


class UserCreate(UserBase):
    """사용자 생성 요청"""
    password: str = Field(..., min_length=8, description="비밀번호 (최소 8자)")
    role: UserRole = Field(default=UserRole.USER, description="사용자 역할")


class UserUpdate(BaseModel):
    """사용자 정보 수정 요청"""
    nickname: Optional[str] = None
    profile_image: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    preferred_region: Optional[str] = None
    preferred_theme: Optional[str] = None
    bio: Optional[str] = None


class UserResponse(UserBase):
    """사용자 정보 응답"""
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    is_active: bool
    is_email_verified: bool
    role: UserRole
    last_login: Optional[datetime] = None
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


class UserSearchParams(BaseModel):
    """사용자 검색 파라미터"""
    email: Optional[str] = None
    nickname: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_email_verified: Optional[bool] = None
    preferred_region: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None