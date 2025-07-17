"""
음식점 관련 Pydantic 스키마
"""

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class RestaurantBase(BaseModel):
    """음식점 기본 스키마"""

    restaurant_name: str = Field(..., description="음식점명")
    region_code: str = Field(..., description="지역 코드")
    category_code: str | None = Field(None, description="대분류 코드")
    sub_category_code: str | None = Field(None, description="중분류 코드")
    address: str | None = Field(None, description="주소")
    detail_address: str | None = Field(None, description="상세 주소")
    zipcode: str | None = Field(None, description="우편번호")
    tel: str | None = Field(None, description="전화번호")
    homepage: str | None = Field(None, description="홈페이지")
    latitude: float | None = Field(None, description="위도")
    longitude: float | None = Field(None, description="경도")
    cuisine_type: str | None = Field(None, description="음식 종류")
    specialty_dish: str | None = Field(None, description="대표 메뉴")
    operating_hours: str | None = Field(None, description="영업 시간")
    rest_date: str | None = Field(None, description="휴무일")
    parking: bool | None = Field(None, description="주차 가능 여부")
    credit_card: bool | None = Field(None, description="신용카드 가능 여부")
    smoking: bool | None = Field(None, description="흡연 가능 여부")
    takeout: bool | None = Field(None, description="포장 가능 여부")
    delivery: bool | None = Field(None, description="배달 가능 여부")
    first_image: str | None = Field(None, description="대표 이미지")
    overview: str | None = Field(None, description="개요")


class RestaurantCreate(RestaurantBase):
    """음식점 생성 스키마"""

    pass


class RestaurantUpdate(BaseModel):
    """음식점 수정 스키마"""

    restaurant_name: str | None = None
    category_code: str | None = None
    sub_category_code: str | None = None
    address: str | None = None
    detail_address: str | None = None
    zipcode: str | None = None
    tel: str | None = None
    homepage: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    cuisine_type: str | None = None
    specialty_dish: str | None = None
    operating_hours: str | None = None
    rest_date: str | None = None
    parking: bool | None = None
    credit_card: bool | None = None
    smoking: bool | None = None
    takeout: bool | None = None
    delivery: bool | None = None
    first_image: str | None = None
    overview: str | None = None


class RestaurantResponse(RestaurantBase):
    """음식점 응답 스키마"""

    content_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RestaurantListResponse(BaseModel):
    """음식점 목록 응답 스키마"""

    items: list[RestaurantResponse]
    total: int
    skip: int
    limit: int
