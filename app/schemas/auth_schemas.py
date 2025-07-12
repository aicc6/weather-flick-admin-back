from pydantic import BaseModel, EmailStr, computed_field
from typing import Optional, List
from datetime import datetime

class AdminLogin(BaseModel):
    email: EmailStr
    password: str

class AdminCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    phone: Optional[str] = None

class AdminResponse(BaseModel):
    admin_id: int
    email: str
    name: Optional[str]
    phone: Optional[str]
    status: Optional[str]
    is_superuser: bool = False  # 데이터베이스 필드로부터 직접 가져옴
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

    @computed_field
    @property
    def username(self) -> str:
        """프론트엔드 호환을 위한 username 필드 (name 또는 email 반환)"""
        return self.name or self.email.split('@')[0]

    @computed_field
    @property
    def id(self) -> int:
        """프론트엔드 호환을 위한 id 필드 (admin_id 반환)"""
        return self.admin_id

    @computed_field
    @property
    def is_active(self) -> bool:
        """프론트엔드 호환을 위한 is_active 필드"""
        return self.status == "ACTIVE"

class AdminListResponse(BaseModel):
    admins: List[AdminResponse]
    total: int
    page: int
    size: int
    total_pages: int

class AdminStatusUpdate(BaseModel):
    status: str

class AdminUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    admin_id: Optional[int] = None
    email: Optional[str] = None

class LoginResponse(BaseModel):
    admin: AdminResponse
    token: Token