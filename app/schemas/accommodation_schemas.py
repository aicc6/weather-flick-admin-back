"""
숙박시설 관련 Pydantic 스키마
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class AccommodationBase(BaseModel):
    """숙박시설 기본 스키마"""
    accommodation_name: str = Field(..., description="숙박시설명")
    region_code: str = Field(..., description="지역 코드")
    accommodation_type: Optional[str] = Field(None, description="숙박시설 유형")
    address: Optional[str] = Field(None, description="주소")
    detail_address: Optional[str] = Field(None, description="상세 주소")
    zipcode: Optional[str] = Field(None, description="우편번호")
    tel: Optional[str] = Field(None, description="전화번호")
    homepage: Optional[str] = Field(None, description="홈페이지")
    latitude: Optional[float] = Field(None, description="위도")
    longitude: Optional[float] = Field(None, description="경도")
    room_count: Optional[int] = Field(None, description="객실 수")
    parking: Optional[bool] = Field(None, description="주차 가능 여부")
    check_in_time: Optional[str] = Field(None, description="체크인 시간")
    check_out_time: Optional[str] = Field(None, description="체크아웃 시간")
    amenities: Optional[str] = Field(None, description="편의시설")
    first_image: Optional[str] = Field(None, description="대표 이미지")
    second_image: Optional[str] = Field(None, description="보조 이미지")
    overview: Optional[str] = Field(None, description="개요")


class AccommodationCreate(AccommodationBase):
    """숙박시설 생성 스키마"""
    pass


class AccommodationUpdate(BaseModel):
    """숙박시설 수정 스키마"""
    accommodation_name: Optional[str] = None
    accommodation_type: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    zipcode: Optional[str] = None
    tel: Optional[str] = None
    homepage: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    room_count: Optional[int] = None
    parking: Optional[bool] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    amenities: Optional[str] = None
    first_image: Optional[str] = None
    second_image: Optional[str] = None
    overview: Optional[str] = None


class AccommodationResponse(AccommodationBase):
    """숙박시설 응답 스키마"""
    content_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class AccommodationListResponse(BaseModel):
    """숙박시설 목록 응답 스키마"""
    items: List[AccommodationResponse]
    total: int
    skip: int
    limit: int