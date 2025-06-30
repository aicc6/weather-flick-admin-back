from pydantic import BaseModel, EmailStr
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
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

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
