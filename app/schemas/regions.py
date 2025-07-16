from datetime import datetime

from pydantic import BaseModel, Field


class RegionBase(BaseModel):
    region_name: str = Field(..., description="지역명")
    parent_region_code: str | None = Field(None, description="상위 지역 코드")
    latitude: float | None = Field(None, description="위도")
    longitude: float | None = Field(None, description="경도")
    region_level: int | None = Field(None, description="지역 레벨 (1: 시/도, 2: 시/군/구)")
    tour_api_area_code: str | None = Field(None, description="한국관광공사 API 지역 코드")


class RegionCreate(RegionBase):
    region_code: str = Field(..., description="지역 코드")


class RegionUpdate(RegionBase):
    region_name: str | None = Field(None, description="지역명")
    region_name_full: str | None = Field(None, description="전체 지역명")
    parent_region_code: str | None = Field(None, description="상위 지역 코드")
    latitude: float | None = Field(None, description="위도")
    longitude: float | None = Field(None, description="경도")
    region_level: int | None = Field(None, description="지역 레벨")
    tour_api_area_code: str | None = Field(None, description="한국관광공사 API 지역 코드")
    is_active: bool | None = Field(None, description="활성화 상태")


class RegionResponse(RegionBase):
    region_code: str
    region_name_full: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RegionListResponse(BaseModel):
    regions: list[RegionResponse]
    total: int
    page: int
    size: int
    total_pages: int
