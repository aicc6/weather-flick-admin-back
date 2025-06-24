from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class AdminBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class AdminCreate(AdminBase):
    password: str


class AdminRegister(AdminBase):
    password: str


class AdminUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class Admin(AdminBase):
    id: int
    is_active: bool
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


class AdminResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
