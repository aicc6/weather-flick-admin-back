from datetime import datetime

from pydantic import BaseModel, Field


class RegionBase(BaseModel):
    region_name: str = Field(..., description="지역명")
    parent_region_code: str | None = Field(None, description="상위 지역 코드")
    latitude: float | None = Field(None, description="위도")
    longitude: float | None = Field(None, description="경도")
    region_level: int | None = Field(None, description="지역 레벨 (1: 시/도, 2: 시/군/구)")


class RegionCreate(RegionBase):
    region_code: str = Field(..., description="지역 코드")


class RegionUpdate(RegionBase):
    region_name: str | None = Field(None, description="지역명")
    parent_region_code: str | None = Field(None, description="상위 지역 코드")
    latitude: float | None = Field(None, description="위도")
    longitude: float | None = Field(None, description="경도")
    region_level: int | None = Field(None, description="지역 레벨")


class RegionResponse(RegionBase):
    region_code: str
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
