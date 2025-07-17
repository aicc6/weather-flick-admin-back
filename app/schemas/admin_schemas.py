import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, computed_field, field_validator
from ..validators import CommonValidators


class AdminStatus(enum.Enum):
    """관리자 계정 상태"""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"


class AdminBase(BaseModel):
    """관리자 기본 정보"""

    email: str
    nickname: str
    profile_image: str | None = None
    preferences: dict[str, Any] | None = None
    preferred_region: str | None = None
    preferred_theme: str | None = None
    bio: str | None = None

    @field_validator("preferences", mode="before")
    @classmethod
    def validate_preferences(cls, v):
        """preferences 필드 검증 - 빈 배열이나 None을 빈 딕셔너리로 변환"""
        return CommonValidators.validate_preferences(v)

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v):
        return CommonValidators.validate_email(v)


class AdminCreate(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None
    phone: str | None = None
    is_superuser: bool = False
    role_ids: list[int] | None = None


class AdminResponse(BaseModel):
    admin_id: int
    email: str
    name: str | None
    phone: str | None
    status: AdminStatus
    is_superuser: bool = False  # 데이터베이스 필드로부터 직접 가져옴
    last_login_at: datetime | None
    created_at: datetime

    @computed_field
    @property
    def username(self) -> str:
        """프론트엔드 호환을 위한 username 필드 (name 또는 email 반환)"""
        return self.name or self.email.split("@")[0]

    @computed_field
    @property
    def id(self) -> int:
        """프론트엔드 호환을 위한 id 필드 (admin_id 반환)"""
        return self.admin_id

    @computed_field
    @property
    def is_active(self) -> bool:
        """프론트엔드 호환을 위한 is_active 필드"""
        return self.status == AdminStatus.ACTIVE

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class AdminListResponse(BaseModel):
    admins: list[AdminResponse]
    total: int
    page: int
    size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class AdminStatusUpdate(BaseModel):
    status: str


class AdminUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    status: str | None = None
