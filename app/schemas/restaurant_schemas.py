"""음식점 스키마"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RestaurantBase(BaseModel):
    """음식점 기본 스키마"""

    content_id: str
    region_code: str
    restaurant_name: str
    food_type: str | None = None
    address: str | None = None
    tel: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    category_code: str | None = None
    sub_category_code: str | None = None
    sigungu_code: str | None = None
    main_menu: str | None = None
    price_range: str | None = None
    operating_hours: str | None = None
    parking: str | None = None


class RestaurantCreate(BaseModel):
    """음식점 생성 스키마"""

    region_code: str
    restaurant_name: str
    food_type: str | None = None
    address: str | None = None
    tel: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    category_code: str | None = None
    sub_category_code: str | None = None
    sigungu_code: str | None = None
    main_menu: str | None = None
    price_range: str | None = None
    operating_hours: str | None = None
    parking: str | None = None


class RestaurantUpdate(RestaurantCreate):
    """음식점 수정 스키마"""

    pass


class RestaurantResponse(RestaurantBase):
    """음식점 응답 스키마"""

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RestaurantListResponse(BaseModel):
    """음식점 목록 응답 스키마"""

    items: list[RestaurantResponse]
    total: int


class RestaurantSearch(BaseModel):
    """음식점 검색 스키마"""

    region_code: str | None = None
    restaurant_name: str | None = None
    food_type: str | None = None
    category_code: str | None = None
    sigungu_code: str | None = None
    skip: int = 0
    limit: int = 100