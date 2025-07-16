"""축제/행사 스키마"""
from datetime import date, datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID


class FestivalEventBase(BaseModel):
    """축제/행사 기본 스키마"""
    content_id: str
    region_code: str
    event_name: str
    event_type: Optional[str] = None
    category_code: Optional[str] = None
    event_start_date: Optional[date] = None
    event_end_date: Optional[date] = None
    play_time: Optional[str] = None
    event_place: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    organizer: Optional[str] = None
    sponsor: Optional[str] = None
    tel: Optional[str] = None
    homepage: Optional[str] = None
    description: Optional[str] = None
    overview: Optional[str] = None
    event_program: Optional[str] = None
    first_image: Optional[str] = None
    first_image_small: Optional[str] = None
    age_limit: Optional[str] = None
    cost_info: Optional[str] = None
    discount_info: Optional[str] = None
    booktour: Optional[str] = None
    telname: Optional[str] = None
    faxno: Optional[str] = None
    mlevel: Optional[int] = None
    createdtime: Optional[str] = None
    modifiedtime: Optional[str] = None
    detail_intro_info: Optional[Dict[str, Any]] = None
    detail_additional_info: Optional[Dict[str, Any]] = None
    data_quality_score: Optional[float] = None
    processing_status: Optional[str] = None


class FestivalEventCreate(FestivalEventBase):
    """축제/행사 생성 스키마"""
    pass


class FestivalEventUpdate(BaseModel):
    """축제/행사 수정 스키마"""
    event_name: Optional[str] = None
    event_type: Optional[str] = None
    category_code: Optional[str] = None
    event_start_date: Optional[date] = None
    event_end_date: Optional[date] = None
    play_time: Optional[str] = None
    event_place: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    organizer: Optional[str] = None
    sponsor: Optional[str] = None
    tel: Optional[str] = None
    homepage: Optional[str] = None
    description: Optional[str] = None
    overview: Optional[str] = None
    event_program: Optional[str] = None
    first_image: Optional[str] = None
    first_image_small: Optional[str] = None
    age_limit: Optional[str] = None
    cost_info: Optional[str] = None
    discount_info: Optional[str] = None
    booktour: Optional[str] = None
    telname: Optional[str] = None
    faxno: Optional[str] = None
    mlevel: Optional[int] = None
    createdtime: Optional[str] = None
    modifiedtime: Optional[str] = None
    detail_intro_info: Optional[Dict[str, Any]] = None
    detail_additional_info: Optional[Dict[str, Any]] = None
    data_quality_score: Optional[float] = None
    processing_status: Optional[str] = None


class FestivalEventResponse(FestivalEventBase):
    """축제/행사 응답 스키마"""
    raw_data_id: Optional[str | UUID] = None
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None
    
    @field_validator('raw_data_id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v
    
    model_config = ConfigDict(from_attributes=True)