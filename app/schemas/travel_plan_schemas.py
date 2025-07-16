"""여행 계획 스키마"""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class TravelPlanStatus(str, Enum):
    """여행 계획 상태"""
    PLANNING = "PLANNING"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TravelPlanBase(BaseModel):
    """여행 계획 기본 스키마"""
    title: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[Decimal] = None
    status: TravelPlanStatus = TravelPlanStatus.PLANNING
    itinerary: Optional[Dict[str, Any]] = None
    participants: Optional[int] = None
    transportation: Optional[str] = None
    start_location: Optional[str] = None
    weather_info: Optional[Dict[str, Any]] = None
    plan_type: str = "manual"


class TravelPlanCreate(TravelPlanBase):
    """여행 계획 생성 스키마"""
    user_id: UUID


class TravelPlanUpdate(BaseModel):
    """여행 계획 수정 스키마"""
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[Decimal] = None
    status: Optional[TravelPlanStatus] = None
    itinerary: Optional[Dict[str, Any]] = None
    participants: Optional[int] = None
    transportation: Optional[str] = None
    start_location: Optional[str] = None
    weather_info: Optional[Dict[str, Any]] = None
    plan_type: Optional[str] = None


class TravelPlanResponse(TravelPlanBase):
    """여행 계획 응답 스키마"""
    plan_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)