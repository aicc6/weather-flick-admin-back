"""레저/스포츠 시설 스키마"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LeisureSportBase(BaseModel):
    """레저/스포츠 시설 기본 스키마"""

    content_id: str
    region_code: str
    facility_name: str
    sports_type: str | None = None
    category_code: str | None = None
    address: str | None = None
    zipcode: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    tel: str | None = None
    homepage: str | None = None
    operationg_hours: dict | None | None = None
    reservation_info: dict | None = None


class LeisureSportCreate(BaseModel):
    region_code: str
    facility_name: str
    category_code: str | None = None
    sub_category_code: str | None = None
    raw_data_id: str | None = None
    sports_type: str | None = None
    reservation_info: str | None = None
    admission_fee: str | None = None
    parking_info: str | None = None
    rental_info: str | None = None
    capacity: str | None = None
    operating_hours: str | None = None
    address: str | None = None
    detail_address: str | None = None
    zipcode: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    tel: str | None = None
    homepage: str | None = None
    overview: str | None = None
    first_image: str | None = None
    first_image_small: str | None = None
    data_quality_score: float | None = None
    processing_status: str | None = None
    booktour: str | None = None
    createdtime: str | None = None
    modifiedtime: str | None = None
    telname: str | None = None
    faxno: str | None = None
    mlevel: int | None = None
    detail_intro_info: dict | None = None
    detail_additional_info: dict | None = None
    sigungu_code: str | None = None
    last_sync_at: str | None = None


class LeisureSportUpdate(LeisureSportCreate):
    """레저/스포츠 시설 수정 스키마"""

    pass


class LeisureSportResponse(BaseModel):
    """레저/스포츠 시설 응답 스키마"""

    content_id: str
    region_code: str
    facility_name: str
    sports_type: str | None = None
    category_code: str | None = None
    address: str | None = None
    zipcode: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    tel: str | None = None
    homepage: str | None = None
    operating_hours: str | None = None
    reservation_info: str | None = None
    admission_fee: str | None = None
    parking_info: str | None = None
    first_image: str | None = None
    raw_data_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeisureSportListResponse(BaseModel):
    items: list[LeisureSportResponse]
    total: int
