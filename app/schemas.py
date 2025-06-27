# Pydantic 스키마

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from .models import UserRole


class AdminBase(BaseModel):
    full_name: Optional[str] = None
    email: EmailStr
    username: str


class AdminCreate(AdminBase):
    password: str


class AdminUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class Admin(AdminBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    role: Optional[UserRole] = None
    profile_image: Optional[str] = None
    bio: Optional[str] = None


class User(UserBase):
    id: int
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    role: Optional[UserRole] = None
    profile_image: Optional[str] = None
    bio: Optional[str] = None
    last_login: Optional[datetime] = None
    login_count: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    google_id: Optional[str] = None

    class Config:
        from_attributes = True
