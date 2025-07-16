"""여행 코스 스키마"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TravelCourseBase(BaseModel):
    """여행 코스 기본 스키마"""

    content_id: str
    region_code: str
    course_name: str
    course_theme: str | None = None
    required_time: str | None = None
    course_distance: str | None = None
    difficulty_level: str | None = None
    schedule: str | None = None
    category_code: str | None = None
    sub_category_code: str | None = None
    sigungu_code: str | None = None
    address: str | None = None
    detail_address: str | None = None
    zipcode: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    tel: str | None = None
    telname: str | None = None
    faxno: str | None = None
    homepage: str | None = None
    overview: str | None = None
    first_image: str | None = None
    first_image_small: str | None = None


class TravelCourseCreate(BaseModel):
    """여행 코스 생성 스키마"""

    region_code: str
    course_name: str
    course_theme: str | None = None
    required_time: str | None = None
    course_distance: str | None = None
    difficulty_level: str | None = None
    schedule: str | None = None
    category_code: str | None = None
    sub_category_code: str | None = None
    sigungu_code: str | None = None
    address: str | None = None
    detail_address: str | None = None
    zipcode: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    tel: str | None = None
    telname: str | None = None
    faxno: str | None = None
    homepage: str | None = None
    overview: str | None = None
    first_image: str | None = None
    first_image_small: str | None = None
    raw_data_id: UUID | None = None
    detail_intro_info: dict | None = None
    detail_additional_info: dict | None = None
    booktour: str | None = None
    createdtime: str | None = None
    modifiedtime: str | None = None
    mlevel: int | None = None
    data_quality_score: float | None = None
    processing_status: str | None = None


class TravelCourseUpdate(TravelCourseCreate):
    """여행 코스 수정 스키마"""

    pass


class TravelCourseResponse(TravelCourseBase):
    """여행 코스 응답 스키마"""

    raw_data_id: UUID | None = None
    data_quality_score: float | None = None
    processing_status: str | None = None
    created_at: datetime
    updated_at: datetime
    last_sync_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TravelCourseListResponse(BaseModel):
    """여행 코스 목록 응답 스키마"""

    items: list[TravelCourseResponse]
    total: int


class TravelCourseSearch(BaseModel):
    """여행 코스 검색 스키마"""

    region_code: str | None = None
    course_name: str | None = None
    course_theme: str | None = None
    difficulty_level: str | None = None
    category_code: str | None = None
    sigungu_code: str | None = None
    skip: int = 0
    limit: int = 100


class TravelCourseSpotBase(BaseModel):
    """여행 코스 구성 지점 기본 스키마"""

    course_id: str
    spot_content_id: str | None = None
    sequence: int
    spot_name: str
    spot_type: str | None = None
    recommended_duration: int | None = None
    arrival_time: str | None = None
    departure_time: str | None = None
    distance_from_previous: float | None = None
    transport_to_next: str | None = None
    description: str | None = None
    tips: str | None = None


class TravelCourseSpotCreate(BaseModel):
    """여행 코스 구성 지점 생성 스키마"""

    course_id: str
    spot_content_id: str | None = None
    sequence: int
    spot_name: str
    spot_type: str | None = None
    recommended_duration: int | None = None
    arrival_time: str | None = None
    departure_time: str | None = None
    distance_from_previous: float | None = None
    transport_to_next: str | None = None
    description: str | None = None
    tips: str | None = None


class TravelCourseSpotUpdate(TravelCourseSpotCreate):
    """여행 코스 구성 지점 수정 스키마"""

    pass


class TravelCourseSpotResponse(TravelCourseSpotBase):
    """여행 코스 구성 지점 응답 스키마"""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TravelCourseSpotListResponse(BaseModel):
    """여행 코스 구성 지점 목록 응답 스키마"""

    items: list[TravelCourseSpotResponse]
    total: int