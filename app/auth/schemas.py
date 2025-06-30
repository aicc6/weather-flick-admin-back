from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class AdminLogin(BaseModel):
    email: EmailStr
    password: str

class AdminCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None

class AdminResponse(BaseModel):
    id: int
    email: str
    name: str
    phone: Optional[str]
    status: str
    last_login_at: Optional[datetime]
    login_count: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    admin_id: Optional[int] = None
    email: Optional[str] = None

class LoginResponse(BaseModel):
    admin: AdminResponse
    token: Token
