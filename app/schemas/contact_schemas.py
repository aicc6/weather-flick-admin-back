"""
문의사항 관련 스키마 정의
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, validator


class ContactBase(BaseModel):
    """문의사항 기본 스키마"""
    category: str
    title: str
    content: str
    name: str
    email: EmailStr
    is_private: bool = False
    
    @validator('category')
    def validate_category(cls, v):
        if len(v) > 50:
            raise ValueError('Category must be 50 characters or less')
        return v
    
    @validator('title')
    def validate_title(cls, v):
        if len(v) > 200:
            raise ValueError('Title must be 200 characters or less')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if len(v) > 50:
            raise ValueError('Name must be 50 characters or less')
        return v


class ContactListResponse(BaseModel):
    """문의 목록 응답 스키마"""
    id: int
    category: str
    title: str
    name: str
    email: str
    approval_status: str
    views: int
    created_at: datetime
    is_private: bool
    has_answer: bool = False
    
    class Config:
        from_attributes = True


class ContactDetailResponse(BaseModel):
    """문의 상세 응답 스키마"""
    id: int
    category: str
    title: str
    content: str
    name: str
    email: str
    approval_status: str
    views: int
    created_at: datetime
    is_private: bool
    answer: Optional['ContactAnswerResponse'] = None
    
    class Config:
        from_attributes = True


class ContactAnswerBase(BaseModel):
    """문의 답변 기본 스키마"""
    content: str


class ContactAnswerCreate(ContactAnswerBase):
    """문의 답변 생성 스키마"""
    pass


class ContactAnswerUpdate(ContactAnswerBase):
    """문의 답변 수정 스키마"""
    pass


class ContactAnswerResponse(ContactAnswerBase):
    """문의 답변 응답 스키마"""
    id: int
    contact_id: int
    admin_id: int
    admin_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ContactStatusUpdate(BaseModel):
    """문의 상태 변경 스키마"""
    approval_status: str
    
    @validator('approval_status')
    def validate_status(cls, v):
        allowed_statuses = ['PENDING', 'PROCESSING', 'COMPLETE']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v


class ContactStatsResponse(BaseModel):
    """문의 통계 응답 스키마"""
    total_count: int
    pending_count: int
    processing_count: int
    complete_count: int
    today_count: int
    this_week_count: int
    this_month_count: int


# Forward reference 해결
ContactDetailResponse.model_rebuild()