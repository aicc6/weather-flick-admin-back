from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RegionBase(BaseModel):
    region_name: str = Field(..., description="지역명")
    parent_region_code: Optional[str] = Field(None, description="상위 지역 코드")
    latitude: Optional[float] = Field(None, description="위도")
    longitude: Optional[float] = Field(None, description="경도")
    region_level: Optional[int] = Field(None, description="지역 레벨 (1: 시/도, 2: 시/군/구)")


class RegionCreate(RegionBase):
    region_code: str = Field(..., description="지역 코드")


class RegionUpdate(RegionBase):
    region_name: Optional[str] = Field(None, description="지역명")
    parent_region_code: Optional[str] = Field(None, description="상위 지역 코드")
    latitude: Optional[float] = Field(None, description="위도")
    longitude: Optional[float] = Field(None, description="경도")
    region_level: Optional[int] = Field(None, description="지역 레벨")


class RegionResponse(RegionBase):
    region_code: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RegionListResponse(BaseModel):
    regions: List[RegionResponse]
    total: int
    page: int
    size: int
    total_pages: int