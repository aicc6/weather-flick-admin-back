"""레저/스포츠 시설 스키마"""
from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, ConfigDict


class LeisureSportBase(BaseModel):
    """레저/스포츠 시설 기본 스키마"""
    content_id: str
    region_code: str
    facility_name: str
    sport_type: Optional[str] = None
    category_code: Optional[str] = None
    address: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    homepage: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    facilities: Optional[Dict] = None
    equipment: Optional[Dict] = None
    programs: Optional[Dict] = None
    operation_hours: Optional[Dict] = None
    closed_days: Optional[List[str]] = None
    usage_fee: Optional[Dict] = None
    reservation_info: Optional[Dict] = None
    weather_suitable: Optional[Dict] = None
    season_suitable: Optional[List[str]] = None


class LeisureSportCreate(LeisureSportBase):
    """레저/스포츠 시설 생성 스키마"""
    pass


class LeisureSportUpdate(BaseModel):
    """레저/스포츠 시설 수정 스키마"""
    facility_name: Optional[str] = None
    sport_type: Optional[str] = None
    category_code: Optional[str] = None
    address: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    homepage: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    facilities: Optional[Dict] = None
    equipment: Optional[Dict] = None
    programs: Optional[Dict] = None
    operation_hours: Optional[Dict] = None
    closed_days: Optional[List[str]] = None
    usage_fee: Optional[Dict] = None
    reservation_info: Optional[Dict] = None
    weather_suitable: Optional[Dict] = None
    season_suitable: Optional[List[str]] = None


class LeisureSportResponse(LeisureSportBase):
    """레저/스포츠 시설 응답 스키마"""
    raw_data_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_sync_at: datetime
    
    model_config = ConfigDict(from_attributes=True)