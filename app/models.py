"""
통합 데이터베이스 모델 정의
모든 서비스에서 공통으로 사용하는 SQLAlchemy ORM 모델들

각 모델의 주석에는 다음과 같은 정보가 포함됩니다:
- 사용처: 해당 모델을 사용하는 서비스 목록
- 설명: 테이블의 용도와 주요 기능
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    CHAR,
    DECIMAL,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

# Admin 모델 임포트

# RBAC 모델 임포트

# ===========================================
# Enum 정의
# ===========================================


class UserRole(enum.Enum):
    """사용자 역할"""

    USER = "USER"
    ADMIN = "ADMIN"


class TravelPlanStatus(enum.Enum):
    """여행 계획 상태"""

    PLANNING = "PLANNING"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ===========================================
# 사용자 및 인증 관련 테이블
# ===========================================


class User(Base):
    """
    사용자 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 일반 사용자 계정 정보 및 프로필 관리
    """

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True, "autoload_replace": False}

    user_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(
        String, nullable=True
    )  # OAuth 사용자는 비밀번호가 없을 수 있음
    nickname = Column(String, index=True, nullable=False)
    profile_image = Column(String)
    preferences = Column(JSONB, default=dict)
    preferred_region = Column(String)  # 선호 지역
    preferred_theme = Column(String)  # 선호 테마
    bio = Column(Text)  # 자기소개
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    google_id = Column(String, unique=True, nullable=True)  # 구글 OAuth ID
    auth_provider = Column(String, default="local")  # 인증 제공자 (local, google 등)
    last_login = Column(DateTime)
    login_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # id 속성을 user_id의 별칭으로 추가
    @property
    def id(self):
        return self.user_id

    # 관계 설정 - 관리자 대시보드에서 필요한 것만
    activity_logs = relationship(
        "UserActivityLog", back_populates="user", cascade="all, delete-orphan"
    )
    reviews = relationship(
        "Review", back_populates="user", cascade="all, delete-orphan"
    )
    travel_plans = relationship(
        "TravelPlan", back_populates="user", cascade="all, delete-orphan"
    )
    chat_messages = relationship(
        "ChatMessage", back_populates="user", cascade="all, delete-orphan"
    )


class EmailVerification(Base):
    """
    이메일 인증 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 이메일 인증 코드 관리
    """

    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# ===========================================
# 여행 계획 및 일정 관련 테이블
# ===========================================


class TravelPlan(Base):
    """
    여행 계획 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 사용자의 여행 계획 및 일정 정보
    """

    __tablename__ = "travel_plans"

    plan_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    budget = Column(DECIMAL(10, 2))
    status = Column(Enum(TravelPlanStatus), default=TravelPlanStatus.PLANNING)
    itinerary = Column(JSONB)
    participants = Column(Integer, nullable=True)
    transportation = Column(String, nullable=True)
    start_location = Column(String, nullable=True)  # 출발지
    weather_info = Column(JSONB, nullable=True)  # 날씨 정보
    plan_type = Column(String(50), default="manual")  # 'manual' 또는 'custom'
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    user = relationship("User", back_populates="travel_plans")
    reviews = relationship("Review", back_populates="travel_plan")
    routes = relationship("TravelRoute", back_populates="travel_plan")


class TravelRoute(Base):
    """
    여행 경로 정보 테이블
    사용처: weather-flick-back
    설명: 여행 계획의 상세 경로 및 교통 정보
    """

    __tablename__ = "travel_routes"

    route_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    plan_id = Column(
        UUID(as_uuid=True), ForeignKey("travel_plans.plan_id"), nullable=False
    )
    day = Column(Integer, nullable=False)
    sequence = Column(Integer, nullable=False)

    # 출발지 정보
    departure_name = Column(String, nullable=False)
    departure_lat = Column(Float)
    departure_lng = Column(Float)

    # 도착지 정보
    destination_name = Column(String, nullable=False)
    destination_lat = Column(Float)
    destination_lng = Column(Float)

    # 교통 정보
    transport_type = Column(String)  # car, bus, subway, walk, taxi
    route_data = Column(JSONB)  # 상세 경로 정보
    duration = Column(Integer)  # 소요 시간 (분)
    distance = Column(Float)  # 거리 (km)
    cost = Column(Float)  # 교통비 (원)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    travel_plan = relationship("TravelPlan", back_populates="routes")
    # transport_details = relationship("TransportationDetail", back_populates="route") # TransportationDetail 테이블이 현재 파일에 없음


class TransportationDetail(Base):
    """
    교통수단 상세 정보 테이블
    사용처: weather-flick-back
    설명: 경로별 상세 교통 정보 (환승, 요금 등)
    """

    __tablename__ = "transportation_details"

    detail_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    route_id = Column(
        UUID(as_uuid=True), ForeignKey("travel_routes.route_id"), nullable=False
    )

    # 교통수단 정보
    transport_name = Column(String)  # 지하철 2호선, 버스 146번 등
    transport_color = Column(String)  # 노선 색상

    # 정류장/역 정보
    departure_station = Column(String)
    arrival_station = Column(String)

    # 시간 정보
    departure_time = Column(DateTime)
    arrival_time = Column(DateTime)

    # 요금 정보
    fare = Column(Float)

    # 환승 정보
    transfer_info = Column(JSONB)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    # route = relationship("TravelRoute", back_populates="transport_details") # 관리자 대시보드에서 필요 없음


# ===========================================
# 여행지 및 시설 정보 테이블
# ===========================================


class Destination(Base):
    """
    여행지 정보 테이블
    사용처: weather-flick-admin-back
    설명: 추천 여행지 기본 정보 (관리자용)
    """

    __tablename__ = "destinations"

    destination_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    name = Column(String, nullable=False, index=True)
    province = Column(String, nullable=False, index=True)  # 도/광역시
    region = Column(String, index=True)  # 시/군/구
    category = Column(String)
    is_indoor = Column(Boolean, default=False)  # 실내/실외 여부
    tags = Column(JSONB)  # 여행지 특성 태그
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    amenities = Column(JSONB)
    image_url = Column(String)
    rating = Column(Float)
    recommendation_weight = Column(DECIMAL(3, 2))
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    weather_data = relationship("WeatherData", back_populates="destination")
    reviews = relationship("Review", back_populates="destination")


class TouristAttraction(Base):
    """
    관광지 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 한국관광공사 API 기반 관광지 정보
    """

    __tablename__ = "tourist_attractions"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    attraction_name = Column(String, nullable=False, index=True)
    category_code = Column(String(10))
    category_name = Column(String(50))

    # 주소 및 위치 정보
    address = Column(String)
    zipcode = Column(String(10))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))

    # 연락처 정보
    homepage = Column(Text)

    # 설명 및 이미지
    description = Column(Text)
    image_url = Column(String)

    # API 원본 필드
    booktour = Column(String(1))
    createdtime = Column(String(14))
    modifiedtime = Column(String(14))
    telname = Column(String(100))
    faxno = Column(String(50))
    mlevel = Column(Integer)

    # JSON 데이터
    detail_intro_info = Column(JSONB)
    detail_additional_info = Column(JSONB)

    # 메타데이터
    data_quality_score = Column(DECIMAL(5, 2))
    processing_status = Column(String(20), default="processed")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_sync_at = Column(DateTime, server_default=func.now())


class CulturalFacility(Base):
    """
    문화시설 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 박물관, 전시관 등 문화시설 정보
    """

    __tablename__ = "cultural_facilities"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    facility_name = Column(String, nullable=False, index=True)
    facility_type = Column(String)
    category_code = Column(String(10))
    sub_category_code = Column(String(10))

    # 주소 및 위치 정보
    address = Column(String)
    detail_address = Column(String)
    zipcode = Column(String(10))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))

    # 연락처 정보
    phone = Column(String(50))
    email = Column(String(100))
    homepage = Column(Text)

    # 시설 정보
    description = Column(Text)
    image_url = Column(String)
    operation_hours = Column(JSONB)  # 운영 시간 정보
    closed_days = Column(JSONB)  # 휴관일
    admission_fee = Column(JSONB)  # 입장료 정보
    facilities = Column(JSONB)  # 편의시설 정보

    # 메타데이터
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_sync_at = Column(DateTime, server_default=func.now())


class TravelCourse(Base):
    """
    여행 코스 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 추천 여행 코스 정보
    """

    __tablename__ = "travel_courses"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    course_name = Column(String, nullable=False, index=True)
    course_theme = Column(String)  # 코스 테마
    required_time = Column(String)  # 소요 시간 (예: "1일", "2박3일")
    course_distance = Column(String)  # 총 거리
    difficulty_level = Column(String)  # 난이도
    schedule = Column(Text)  # 일정 정보

    # 카테고리 정보
    category_code = Column(String)
    sub_category_code = Column(String)
    sigungu_code = Column(String)

    # 주소 및 위치 정보
    address = Column(String)
    detail_address = Column(String)
    zipcode = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    # 연락처 정보
    tel = Column(String)
    telname = Column(String)
    faxno = Column(String)
    homepage = Column(String)

    # 상세 정보
    overview = Column(Text)  # 코스 개요
    detail_intro_info = Column(JSONB)  # 상세 소개 정보
    detail_additional_info = Column(JSONB)  # 추가 정보

    # 이미지
    first_image = Column(String)
    first_image_small = Column(String)

    # API 원본 필드
    booktour = Column(String)
    createdtime = Column(String)
    modifiedtime = Column(String)
    mlevel = Column(Integer)

    # 메타데이터
    data_quality_score = Column(Float)
    processing_status = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_sync_at = Column(DateTime, server_default=func.now())


class TravelCourseSpot(Base):
    """
    여행 코스 구성 지점 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 여행 코스를 구성하는 개별 지점 정보
    """

    __tablename__ = "travel_course_spots"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    course_id = Column(
        String(20), ForeignKey("travel_courses.content_id"), nullable=False, index=True
    )
    spot_content_id = Column(String(20), index=True)  # 관광지/시설의 content_id

    # 순서 및 정보
    sequence = Column(Integer, nullable=False)  # 코스 내 순서
    spot_name = Column(String, nullable=False)
    spot_type = Column(String)  # 관광지, 식당, 숙박 등

    # 시간 정보
    recommended_duration = Column(Integer)  # 추천 체류 시간 (분)
    arrival_time = Column(String)  # 도착 시간
    departure_time = Column(String)  # 출발 시간

    # 교통 정보
    distance_from_previous = Column(Float)  # 이전 지점으로부터의 거리 (km)
    transport_to_next = Column(String)  # 다음 지점까지의 교통수단

    # 추가 정보
    description = Column(Text)
    tips = Column(Text)  # 팁이나 주의사항

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class LeisureSport(Base):
    """
    레저스포츠 시설 정보 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 레저 및 스포츠 시설 정보
    """

    __tablename__ = "leisure_sports"

    content_id = Column(String(20), primary_key=True, index=True)
    region_code = Column(String, nullable=False, index=True)
    facility_name = Column(String, nullable=False, index=True)
    category_code = Column(String(10))
    sub_category_code = Column(String(10))
    raw_data_id = Column(UUID(as_uuid=True), index=True)
    sports_type = Column(String)
    reservation_info = Column(String)
    admission_fee = Column(String)
    parking_info = Column(String)
    rental_info = Column(String)
    capacity = Column(String)
    operating_hours = Column(String)
    address = Column(String)
    detail_address = Column(String)
    zipcode = Column(String)
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    tel = Column(String)
    homepage = Column(String)
    overview = Column(Text)
    first_image = Column(String)
    first_image_small = Column(String)
    data_quality_score = Column(DECIMAL(5, 2))
    processing_status = Column(String(20), default="processed")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_sync_at = Column(DateTime, server_default=func.now())
    booktour = Column(CHAR(1))
    createdtime = Column(String(14))
    modifiedtime = Column(String(14))
    telname = Column(String(100))
    faxno = Column(String(50))
    mlevel = Column(Integer)
    detail_intro_info = Column(JSONB)
    detail_additional_info = Column(JSONB)
    sigungu_code = Column(String)


class FestivalEvent(Base):
    """
    축제/행사 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 지역별 축제 및 행사 정보
    """

    __tablename__ = "festivals_events"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    event_name = Column(String, nullable=False, index=True)
    category_code = Column(String)
    sub_category_code = Column(String)

    # 일정 정보
    event_start_date = Column(Date, index=True)
    event_end_date = Column(Date, index=True)
    play_time = Column(String)  # 공연 시간

    # 장소 정보
    event_place = Column(String)  # 개최 장소
    address = Column(String)
    detail_address = Column(String)
    zipcode = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    # 연락처 정보
    tel = Column(String)
    telname = Column(String)
    faxno = Column(String)
    homepage = Column(Text)
    sponsor = Column(String)  # 후원
    organizer = Column(String)  # 주최/주관

    # 상세 정보
    description = Column(Text)
    overview = Column(Text)
    event_program = Column(Text)  # 프로그램 정보
    first_image = Column(String)
    first_image_small = Column(String)

    # 요금 정보
    cost_info = Column(String)  # 이용요금 정보
    discount_info = Column(String)  # 할인 정보

    # 기타 정보
    age_limit = Column(String)  # 관람 연령

    # API 원본 필드
    booktour = Column(String)
    createdtime = Column(String)
    modifiedtime = Column(String)
    mlevel = Column(Integer)

    # JSON 데이터
    detail_intro_info = Column(JSONB)
    detail_additional_info = Column(JSONB)

    # 메타데이터
    data_quality_score = Column(Float)
    processing_status = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_sync_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_festival_dates", "event_start_date", "event_end_date"),
    )


class TravelPlanDestination(Base):
    """
    여행 계획-여행지 연결 테이블
    사용처: weather-flick-back
    설명: 여행 계획에 포함된 여행지 정보
    """

    __tablename__ = "travel_plan_destinations"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(
        UUID(as_uuid=True), ForeignKey("travel_plans.plan_id"), nullable=False
    )
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=False
    )
    visit_date = Column(Date)
    visit_order = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # 유니크 제약조건
    __table_args__ = (
        UniqueConstraint("plan_id", "destination_id", name="uq_plan_destination"),
    )


class DestinationImage(Base):
    """
    여행지 이미지 테이블
    사용처: weather-flick-admin-back
    설명: 여행지별 이미지 관리
    """

    __tablename__ = "destination_images"

    image_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=False
    )
    image_url = Column(String, nullable=False)
    is_main = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class DestinationRating(Base):
    """
    여행지 평점 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 사용자별 여행지 평점 관리
    """

    __tablename__ = "destination_ratings"

    rating_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 평점
    created_at = Column(DateTime, server_default=func.now())

    # 유니크 제약조건: 한 사용자는 한 여행지에 하나의 평점만
    __table_args__ = (
        UniqueConstraint(
            "destination_id", "user_id", name="uq_destination_user_rating"
        ),
    )


# ===========================================
# 날씨 정보 관련 테이블
# ===========================================


class WeatherData(Base):
    """
    실시간 날씨 데이터 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 실시간 날씨 정보 저장
    """

    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, index=True)
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=True
    )
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )

    # 날씨 정보
    temperature = Column(Float)
    feels_like = Column(Float)
    humidity = Column(Integer)
    wind_speed = Column(Float)
    weather_condition = Column(String)
    weather_description = Column(String)

    # 추가 정보
    precipitation = Column(Float)  # 강수량
    cloud_coverage = Column(Integer)  # 구름양
    visibility = Column(Float)  # 가시거리
    uv_index = Column(Float)  # 자외선 지수

    observation_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    destination = relationship("Destination", back_populates="weather_data")

    # 인덱스
    __table_args__ = (
        Index("idx_weather_region_time", "region_code", "observation_time"),
    )


class WeatherInfo(Base):
    """
    날씨 예보 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 단기/중기 날씨 예보 정보
    """

    __tablename__ = "weather_info"

    weather_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
    forecast_date = Column(Date, nullable=False, index=True)
    forecast_type = Column(String(20))  # 'short_term', 'mid_term'

    # 기온 정보
    temperature_high = Column(Float)
    temperature_low = Column(Float)

    # 날씨 상태
    weather_condition = Column(String)
    weather_description = Column(String)

    # 강수 정보
    precipitation_probability = Column(Integer)  # 강수 확률
    precipitation_amount = Column(Float)  # 예상 강수량

    # 기타 정보
    humidity = Column(Integer)
    wind_speed = Column(Float)
    wind_direction = Column(String)

    # 여행 적합도
    travel_score = Column(Integer)  # 1-10 여행 적합도 점수

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 인덱스
    __table_args__ = (
        UniqueConstraint(
            "region_code", "forecast_date", "forecast_type", name="uq_weather_forecast"
        ),
        Index("idx_weather_date", "forecast_date"),
    )


class WeatherForecast(Base):
    """
    상세 날씨 예보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 시간별 상세 날씨 예보
    """

    __tablename__ = "weather_forecasts"

    forecast_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
    forecast_datetime = Column(DateTime, nullable=False, index=True)

    # 기온 정보
    temperature = Column(Float)
    feels_like = Column(Float)

    # 날씨 상태
    weather_condition = Column(String)
    weather_icon = Column(String)

    # 강수 정보
    precipitation_type = Column(String)  # rain, snow, sleet
    precipitation_probability = Column(Integer)
    precipitation_amount = Column(Float)

    # 바람 정보
    wind_speed = Column(Float)
    wind_direction = Column(Integer)  # 각도
    wind_gust = Column(Float)  # 돌풍

    # 기타
    humidity = Column(Integer)
    pressure = Column(Float)  # 기압
    visibility = Column(Float)
    cloud_coverage = Column(Integer)

    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_forecast_region_datetime", "region_code", "forecast_datetime"),
    )


class WeatherRecommendation(Base):
    """
    날씨 기반 여행지 추천 테이블
    사용처: weather-flick-back
    설명: 날씨 조건에 따른 여행지 추천 정보
    """

    __tablename__ = "weather_recommendations"

    recommendation_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    weather_condition = Column(String, nullable=False)  # sunny, rainy, snowy 등
    temperature_range = Column(String)  # cold, cool, warm, hot
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=False
    )
    recommendation_score = Column(Float)  # 추천 점수
    reason = Column(Text)  # 추천 이유
    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_weather_recommendation", "weather_condition", "temperature_range"),
    )


# ===========================================
# 리뷰 및 활동 로그 테이블
# ===========================================


class Review(Base):
    """
    리뷰 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 여행지 및 여행 계획에 대한 사용자 리뷰
    """

    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=True
    )
    plan_id = Column(
        UUID(as_uuid=True), ForeignKey("travel_plans.plan_id"), nullable=True
    )
    rating = Column(Integer, nullable=False)  # 1-5 평점
    content = Column(Text, nullable=False)
    images = Column(JSONB)  # 리뷰 이미지 URL 리스트
    is_verified = Column(Boolean, default=False)  # 실제 방문 확인 여부
    helpful_count = Column(Integer, default=0)  # 도움이 됨 수
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    user = relationship("User", back_populates="reviews")
    destination = relationship("Destination", back_populates="reviews")
    travel_plan = relationship("TravelPlan", back_populates="reviews")

    # 체크 제약조건: destination_id 또는 plan_id 중 하나는 반드시 있어야 함
    __table_args__ = (
        Index("idx_review_user", "user_id"),
        Index("idx_review_destination", "destination_id"),
        Index("idx_review_plan", "plan_id"),
    )


class UserActivityLog(Base):
    """
    사용자 활동 로그 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 사용자의 서비스 이용 활동 기록
    """

    __tablename__ = "user_activity_logs"

    log_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    activity_type = Column(String, nullable=False)  # search, view, create_plan 등
    activity_data = Column(JSONB)  # 활동 상세 데이터
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    session_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    user = relationship("User", back_populates="activity_logs")

    # 인덱스
    __table_args__ = (
        Index("idx_activity_user_created", "user_id", "created_at"),
        Index("idx_activity_type", "activity_type"),
    )


# ===========================================
# 지역 정보 테이블
# ===========================================


class Region(Base):
    """
    지역 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 한국 행정구역 정보
    """

    __tablename__ = "regions"
    __table_args__ = {"extend_existing": True}
    
    region_code = Column(String, primary_key=True, index=True)  # 지역 코드
    region_name = Column(String, nullable=False, index=True)  # 지역명
    parent_region_code = Column(String, nullable=True)  # 상위 지역 코드
    region_level = Column(Integer, nullable=True)  # 지역 레벨 (1: 시/도, 2: 시/군/구)
    region_name_full = Column(String, nullable=True)  # 전체 지역명
    region_name_en = Column(String, nullable=True)  # 영문 지역명
    region_id = Column(String, nullable=True)  # 지역 ID
    
    # 위치 정보
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    center_latitude = Column(Float, nullable=True)
    center_longitude = Column(Float, nullable=True)
    
    # 격자 정보
    grid_x = Column(Integer, nullable=True)  # 기상청 격자 X
    grid_y = Column(Integer, nullable=True)  # 기상청 격자 Y
    
    # 기타 정보
    administrative_code = Column(String, nullable=True)  # 행정 코드
    api_mappings = Column(JSONB, nullable=True)  # API 매핑 정보
    coordinate_info = Column(JSONB, nullable=True)  # 좌표 정보
    
    # API 매핑 정보 (콘텐츠 테이블과 JOIN 시 사용)
    tour_api_area_code = Column(String, nullable=True, index=True)  # 한국관광공사 API 지역 코드
    
    # 메타 정보
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ===========================================
# API 키 및 데이터 수집 관련 테이블
# ===========================================


class ApiKey(Base):
    """
    API 키 관리 테이블
    사용처: weather-flick-batch
    설명: 외부 API 키 관리 및 사용량 추적
    """

    __tablename__ = "api_keys"

    key_id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, nullable=False)  # tour_api, weather_api 등
    api_key = Column(String, nullable=False)
    key_alias = Column(String)  # 키 별칭

    # 사용량 제한
    daily_limit = Column(Integer)
    monthly_limit = Column(Integer)

    # 현재 사용량
    daily_usage = Column(Integer, default=0)
    monthly_usage = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    usage_reset_at = Column(DateTime)

    # 상태
    is_active = Column(Boolean, default=True)
    error_count = Column(Integer, default=0)
    last_error_at = Column(DateTime)
    last_error_message = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 유니크 제약조건
    __table_args__ = (
        UniqueConstraint("service_name", "api_key", name="uq_service_api_key"),
        Index("idx_api_key_service", "service_name", "is_active"),
    )


class SystemLog(Base):
    """
    시스템 로그 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 시스템 전반의 로그 기록
    """

    __tablename__ = "system_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    level = Column(String, nullable=False)
    source = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    context = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())


class DataCollectionLog(Base):
    """
    데이터 수집 로그 테이블
    사용처: weather-flick-batch
    설명: 외부 API 데이터 수집 기록
    """

    __tablename__ = "data_collection_logs"

    log_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    api_key_id = Column(Integer, ForeignKey("api_keys.key_id"), nullable=False)
    collection_type = Column(String, nullable=False)  # tourist_attraction, weather 등

    # 수집 정보
    request_url = Column(Text)
    request_params = Column(JSONB)
    response_status = Column(Integer)
    response_time = Column(Float)  # 응답 시간 (초)

    # 결과
    records_collected = Column(Integer, default=0)
    records_processed = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)

    # 에러 정보
    error_message = Column(Text)

    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)

    # 인덱스
    __table_args__ = (
        Index("idx_collection_log_api", "api_key_id"),
        Index("idx_collection_log_type_started", "collection_type", "started_at"),
    )


class RawApiData(Base):
    """
    원본 API 데이터 저장 테이블
    사용처: weather-flick-batch
    설명: 외부 API에서 수집한 원본 데이터 저장
    """

    __tablename__ = "raw_api_data"

    data_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    source_api = Column(String, nullable=False)  # tour_api, weather_api 등
    data_type = Column(String, nullable=False)  # attraction, weather_forecast 등
    content_id = Column(String, index=True)  # 원본 콘텐츠 ID

    # 원본 데이터
    raw_data = Column(JSONB, nullable=False)

    # 처리 상태
    is_processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)
    processing_error = Column(Text)

    # 메타데이터
    collected_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)  # 데이터 만료 시간

    # 인덱스
    __table_args__ = (
        Index("idx_raw_data_source_type", "source_api", "data_type"),
        Index("idx_raw_data_processed", "is_processed", "collected_at"),
    )


# ===========================================
# 배치 작업 관련 테이블
# ===========================================


class BatchJob(Base):
    """
    배치 작업 정의 테이블
    사용처: weather-flick-batch
    설명: 정기적으로 실행되는 배치 작업 정의
    """

    __tablename__ = "batch_jobs"

    job_id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String, unique=True, nullable=False)
    job_type = Column(String, nullable=False)  # data_collection, data_processing 등
    description = Column(Text)

    # 실행 설정
    is_active = Column(Boolean, default=True)
    schedule_cron = Column(String)  # 크론 표현식
    timeout_minutes = Column(Integer, default=60)
    retry_count = Column(Integer, default=3)

    # 마지막 실행 정보
    last_run_at = Column(DateTime)
    last_success_at = Column(DateTime)
    last_failure_at = Column(DateTime)
    last_error_message = Column(Text)

    # 실행 통계
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BatchJobSchedule(Base):
    """
    배치 작업 스케줄 테이블
    사용처: weather-flick-batch
    설명: 배치 작업의 실행 스케줄 관리
    """

    __tablename__ = "batch_job_schedules"

    schedule_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("batch_jobs.job_id"), nullable=False)

    # 스케줄 정보
    scheduled_time = Column(DateTime, nullable=False, index=True)
    priority = Column(Integer, default=5)  # 1-10, 높을수록 우선순위 높음

    # 실행 상태
    status = Column(
        String, default="pending"
    )  # pending, running, completed, failed, cancelled
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # 실행 결과
    result_summary = Column(JSONB)
    error_message = Column(Text)

    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_schedule_status_time", "status", "scheduled_time"),
        Index("idx_schedule_job", "job_id"),
    )


class ErrorLog(Base):
    """
    에러 로그 테이블
    사용처: 모든 서비스
    설명: 시스템 전체 에러 로그
    """

    __tablename__ = "error_logs"

    error_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    service_name = Column(String, nullable=False)  # weather-flick-back, admin-back 등
    error_type = Column(String, nullable=False)  # database, api, validation 등
    error_level = Column(String, nullable=False)  # error, warning, critical

    # 에러 정보
    error_message = Column(Text, nullable=False)
    error_trace = Column(Text)  # 스택 트레이스
    error_data = Column(JSONB)  # 추가 컨텍스트 데이터

    # 요청 정보
    request_method = Column(String)
    request_url = Column(Text)
    request_headers = Column(JSONB)
    request_body = Column(JSONB)

    # 사용자 정보
    user_id = Column(UUID(as_uuid=True))
    ip_address = Column(String(45))

    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_error_service_created", "service_name", "created_at"),
        Index("idx_error_type_level", "error_type", "error_level"),
    )


class EventLog(Base):
    """
    이벤트 로그 테이블
    사용처: 모든 서비스
    설명: 중요 시스템 이벤트 로그
    """

    __tablename__ = "event_logs"

    event_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    service_name = Column(String, nullable=False)
    event_type = Column(
        String, nullable=False
    )  # user_action, system_event, data_change 등
    event_name = Column(String, nullable=False)  # login, data_sync_completed 등

    # 이벤트 정보
    event_data = Column(JSONB)

    # 사용자 정보
    user_id = Column(UUID(as_uuid=True))
    admin_id = Column(Integer)

    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_event_service_type", "service_name", "event_type"),
        Index("idx_event_created", "created_at"),
        Index("idx_event_user", "user_id"),
        Index("idx_event_admin", "admin_id"),
    )


# ===========================================
# 채팅 및 메시징 관련 테이블
# ===========================================


class ChatMessage(Base):
    """
    채팅 메시지 테이블
    사용처: weather-flick-back
    설명: AI 챗봇 대화 기록
    """

    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)  # 봇의 응답
    sender = Column(
        String(50), nullable=True, server_default="user"
    )  # 'user' 또는 'bot'
    context = Column(JSONB, nullable=True)  # 대화 컨텍스트 정보
    suggestions = Column(ARRAY(Text), nullable=True)  # 추천 질문 목록
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    user = relationship("User", back_populates="chat_messages")


# ===========================================
# 시스템 설정 및 기타 테이블
# ===========================================


class SystemSettings(Base):
    """
    시스템 설정 테이블
    사용처: 모든 서비스
    설명: 시스템 전역 설정 값 저장
    """

    __tablename__ = "system_settings"

    setting_key = Column(String, primary_key=True)
    setting_value = Column(JSONB, nullable=False)
    setting_type = Column(String, nullable=False)  # string, number, boolean, json
    description = Column(Text)
    is_public = Column(Boolean, default=False)  # 클라이언트에 노출 가능 여부
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(Integer)  # admin_id


class DataSyncStatus(Base):
    """
    데이터 동기화 상태 테이블
    사용처: weather-flick-batch
    설명: 외부 데이터 소스와의 동기화 상태 추적
    """

    __tablename__ = "data_sync_status"

    sync_id = Column(Integer, primary_key=True, index=True)
    data_source = Column(String, nullable=False)  # tour_api, weather_api 등
    sync_type = Column(String, nullable=False)  # full, incremental

    # 동기화 범위
    sync_target = Column(String)  # regions, attractions 등
    sync_filter = Column(JSONB)  # 동기화 필터 조건

    # 진행 상태
    status = Column(String, default="pending")  # pending, running, completed, failed
    progress_percent = Column(Float, default=0)
    current_page = Column(Integer)
    total_pages = Column(Integer)

    # 결과
    records_fetched = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_deleted = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)

    # 시간 정보
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    next_sync_at = Column(DateTime)

    # 에러 정보
    error_message = Column(Text)
    error_details = Column(JSONB)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 유니크 제약조건
    __table_args__ = (
        UniqueConstraint(
            "data_source", "sync_type", "sync_target", name="uq_sync_source_type_target"
        ),
    )


# ===========================================
# 문의하기 관련 테이블
# ===========================================


class Contact(Base):
    """
    문의사항 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 사용자 문의사항 관리
    """

    __tablename__ = "contact"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)  # 문의 카테고리
    title = Column(String(200), nullable=False)  # 문의 제목
    content = Column(Text, nullable=False)  # 문의 내용
    name = Column(String(50), nullable=False)  # 작성자 이름
    email = Column(String(100), nullable=False)  # 작성자 이메일
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_private = Column(Boolean, default=False, nullable=False)  # 비공개 여부
    approval_status = Column(
        SqlEnum("PENDING", "PROCESSING", "COMPLETE", name="approval_status"),
        default="PENDING",
        nullable=False,
    )  # 처리 상태
    password_hash = Column(String(128), nullable=True)  # 비공개 문의 비밀번호 해시
    views = Column(Integer, default=0, nullable=False)  # 조회수

    # 관계 설정
    answer = relationship(
        "ContactAnswer",
        back_populates="contact",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ContactAnswer(Base):
    """
    문의사항 답변 테이블
    사용처: weather-flick-admin-back
    설명: 관리자의 문의사항 답변 관리
    """

    __tablename__ = "contact_answers"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contact.id"), nullable=False, unique=True)
    admin_id = Column(
        Integer, ForeignKey("admins.admin_id"), nullable=False
    )  # 답변한 관리자
    content = Column(Text, nullable=False)  # 답변 내용
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # 관계 설정
    contact = relationship("Contact", back_populates="answer")
    admin = relationship("Admin")

    # 인덱스
    __table_args__ = (Index("idx_contact_answer_contact_id", "contact_id"),)


class SystemConfiguration(Base):
    """
    시스템 구성 정보 테이블
    사용처: weather-flick-admin-back
    설명: 시스템 구성 및 기능 플래그 관리
    """

    __tablename__ = "system_configurations"

    config_id = Column(Integer, primary_key=True, index=True)
    config_category = Column(String, nullable=False)  # feature, api, security 등
    config_key = Column(String, nullable=False)
    config_value = Column(JSONB, nullable=False)

    # 설정 정보
    is_active = Column(Boolean, default=True)
    requires_restart = Column(Boolean, default=False)  # 재시작 필요 여부

    # 설명
    description = Column(Text)
    allowed_values = Column(JSONB)  # 허용된 값 목록
    default_value = Column(JSONB)  # 기본값

    # 감사 정보
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(Integer)  # admin_id
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(Integer)  # admin_id

    # 유니크 제약조건
    __table_args__ = (
        UniqueConstraint(
            "config_category", "config_key", name="uq_config_category_key"
        ),
        Index("idx_config_category", "config_category", "is_active"),
    )


class Accommodation(Base):
    """
    숙박시설 정보 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 한국관광공사 API 기반 숙박시설 정보
    """

    __tablename__ = "accommodations"
    __table_args__ = {"extend_existing": True, "autoload_replace": False}

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    accommodation_name = Column(String, nullable=False)
    accommodation_type = Column(String, nullable=False)
    address = Column(String, nullable=False)
    tel = Column(String)

    # 위치 정보
    latitude = Column(Float)
    longitude = Column(Float)

    # 카테고리 정보
    category_code = Column(String(10))
    sub_category_code = Column(String(10))

    # 시설 정보
    parking = Column(String)

    # 메타데이터
    created_at = Column(DateTime, server_default=func.now())


class Restaurant(Base):
    """
    음식점 정보 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 한국관광공사 API 기반 음식점 정보
    """

    __tablename__ = "restaurants"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )

    # 기본 정보
    restaurant_name = Column(String, nullable=False)
    food_type = Column(String)
    address = Column(String, nullable=False)
    tel = Column(String)

    # 위치 정보
    latitude = Column(Float)
    longitude = Column(Float)

    # 카테고리 정보
    category_code = Column(String(10))
    sub_category_code = Column(String(10))

    # 음식점 특성
    main_menu = Column(String)
    price_range = Column(String)
    operating_hours = Column(String)
    parking = Column(String)

    # 메타데이터
    created_at = Column(DateTime, server_default=func.now())


class Shopping(Base):
    """
    쇼핑 시설 정보 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 한국관광공사 API 기반 쇼핑 시설 정보
    """

    __tablename__ = "shopping"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )

    # 기본 정보
    shopping_name = Column(String, nullable=False)
    shopping_type = Column(String)
    address = Column(String, nullable=False)
    tel = Column(String)

    # 위치 정보
    latitude = Column(Float)
    longitude = Column(Float)

    # 카테고리 정보
    category_code = Column(String(10))
    sub_category_code = Column(String(10))

    # 쇼핑 시설 특성
    main_items = Column(String)
    operating_hours = Column(String)
    parking = Column(String)

    # 메타데이터
    created_at = Column(DateTime, server_default=func.now())


class Transportation(Base):
    """
    교통수단 정보 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 대중교통 및 교통수단 정보
    """

    __tablename__ = "transportation"

    transport_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )

    # 교통수단 정보
    transport_type = Column(String, nullable=False)  # bus, subway, train 등
    transport_name = Column(String, nullable=False)
    route_number = Column(String)

    # 운행 정보
    operating_hours = Column(String)
    frequency = Column(String)  # 운행 간격
    fare = Column(String)

    # 노선 정보
    start_point = Column(String)
    end_point = Column(String)
    route_description = Column(Text)

    created_at = Column(DateTime, server_default=func.now())


class PetTourInfo(Base):
    """
    펫 투어 정보 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 반려동물 동반 여행 정보
    """

    __tablename__ = "pet_tour_info"

    pet_tour_id = Column(Integer, primary_key=True, index=True)
    attraction_content_id = Column(
        String(20), ForeignKey("tourist_attractions.content_id"), nullable=False
    )

    # 펫 정보
    pet_allowed = Column(Boolean, default=False)
    pet_restrictions = Column(String)
    pet_facilities = Column(String)
    pet_fee = Column(String)

    # 추가 정보
    notes = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CategoryCode(Base):
    """
    카테고리 코드 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 한국관광공사 카테고리 코드 관리
    """

    __tablename__ = "category_codes"

    category_id = Column(Integer, primary_key=True, index=True)
    category_code = Column(String(10), unique=True, nullable=False)
    category_name = Column(String, nullable=False)
    parent_category_code = Column(String(10))
    level = Column(Integer, default=1)  # 카테고리 레벨
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FavoritePlace(Base):
    """
    즐겨찾기 장소 테이블
    사용처: weather-flick-admin-back
    설명: 사용자가 즐겨찾기한 장소 관리
    """

    __tablename__ = "favorite_places"

    favorite_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    place_type = Column(String, nullable=False)  # attraction, restaurant, accommodation
    place_id = Column(String, nullable=False)  # content_id

    # 즐겨찾기 정보
    place_name = Column(String, nullable=False)
    notes = Column(Text)
    tags = Column(JSONB)

    created_at = Column(DateTime, server_default=func.now())

    # 유니크 제약조건
    __table_args__ = (
        UniqueConstraint("user_id", "place_type", "place_id", name="uq_user_place"),
    )


class ReviewLike(Base):
    """
    리뷰 좋아요 테이블
    사용처: weather-flick-admin-back
    설명: 사용자의 리뷰 좋아요 관리
    """

    __tablename__ = "review_likes"

    like_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    review_id = Column(
        UUID(as_uuid=True), ForeignKey("reviews.review_id"), nullable=False, index=True
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )

    created_at = Column(DateTime, server_default=func.now())

    # 유니크 제약조건
    __table_args__ = (
        UniqueConstraint("review_id", "user_id", name="uq_review_user_like"),
    )


class TravelCourseLike(Base):
    """
    여행 코스 좋아요 테이블
    사용처: weather-flick-admin-back
    설명: 사용자가 좋아요한 여행 코스
    """

    __tablename__ = "travel_course_likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    title = Column(String(255), nullable=False)
    subtitle = Column(String(255))
    summary = Column(Text)
    description = Column(Text)
    region = Column(String(50))
    itinerary = Column(JSONB)


class WeatherCurrent(Base):
    """
    현재 날씨 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 실시간 날씨 정보
    """

    __tablename__ = "weather_current"

    weather_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )

    # 날씨 정보
    temperature = Column(Float)
    feels_like = Column(Float)
    humidity = Column(Integer)
    pressure = Column(Float)
    wind_speed = Column(Float)
    wind_direction = Column(Integer)
    visibility = Column(Float)
    cloud_coverage = Column(Integer)

    # 날씨 상태
    weather_condition = Column(String)
    weather_description = Column(String)
    weather_icon = Column(String)

    # 관측 시간
    observed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_weather_current_region", "region_code", "observed_at"),
    )


class WeatherForecastDaily(Base):
    """
    일별 날씨 예보 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 중장기 일별 날씨 예보 정보
    """

    __tablename__ = "weather_forecast"

    forecast_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )

    # 예보 기본 정보
    forecast_date = Column(Date, nullable=False, index=True)
    forecast_type = Column(String(20))  # short_term, mid_term

    # 기온 정보
    temperature_high = Column(Float)
    temperature_low = Column(Float)
    temperature_avg = Column(Float)

    # 날씨 상태
    weather_condition = Column(String)
    weather_description = Column(String)

    # 강수 정보
    precipitation_probability = Column(Integer)
    precipitation_amount = Column(Float)
    precipitation_type = Column(String)

    # 기타 정보
    humidity = Column(Integer)
    wind_speed = Column(Float)
    wind_direction = Column(String)

    # 여행 적합도
    travel_suitability = Column(Integer)  # 1-10 점수

    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        UniqueConstraint(
            "region_code", "forecast_date", "forecast_type", name="uq_forecast_unique"
        ),
    )


class HistoricalWeatherDaily(Base):
    """
    일별 과거 날씨 데이터 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 분석용 과거 날씨 데이터
    """

    __tablename__ = "historical_weather_daily"

    weather_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
    weather_date = Column(Date, nullable=False, index=True)

    # 기온 정보
    temperature_max = Column(Float)
    temperature_min = Column(Float)
    temperature_avg = Column(Float)

    # 강수 정보
    precipitation_total = Column(Float)
    precipitation_duration = Column(Integer)  # 강수 지속 시간 (분)

    # 날씨 상태
    weather_condition = Column(String)
    sunny_hours = Column(Float)  # 일조 시간

    # 바람 정보
    wind_speed_max = Column(Float)
    wind_speed_avg = Column(Float)

    # 기타
    humidity_avg = Column(Integer)
    pressure_avg = Column(Float)

    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        UniqueConstraint(
            "region_code", "weather_date", name="uq_historical_weather_daily"
        ),
        Index("idx_historical_weather_date", "weather_date"),
    )


class DataTransformationLog(Base):
    """
    데이터 변환 로그 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 데이터 변환 작업 로그
    """

    __tablename__ = "data_transformation_logs"

    log_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    transformation_type = Column(String, nullable=False)  # api_to_db, data_cleaning 등
    source_type = Column(String, nullable=False)
    target_type = Column(String, nullable=False)

    # 변환 정보
    records_input = Column(Integer, default=0)
    records_output = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)

    # 실행 정보
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    status = Column(String, default="running")  # running, completed, failed

    # 에러 정보
    error_message = Column(Text)
    error_details = Column(JSONB)

    created_at = Column(DateTime, server_default=func.now())


class BatchJobLog(Base):
    """
    배치 작업 실행 로그 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 배치 작업 상세 실행 로그
    """

    __tablename__ = "batch_job_logs"

    log_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    job_id = Column(Integer, ForeignKey("batch_jobs.job_id"), nullable=False)
    schedule_id = Column(
        Integer, ForeignKey("batch_job_schedules.schedule_id"), nullable=True
    )

    # 실행 정보
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    execution_time = Column(Float)  # 실행 시간 (초)

    # 상태 및 결과
    status = Column(String, nullable=False)  # success, failed, timeout
    exit_code = Column(Integer)
    
    # 처리 결과
    records_processed = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    output_summary = Column(JSONB)

    # 로그 및 에러
    log_output = Column(Text)  # 표준 출력
    error_output = Column(Text)  # 에러 출력

    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_batch_log_job", "job_id", "started_at"),
        Index("idx_batch_log_status", "status"),
    )


class AdminRole(Base):
    """
    관리자 역할 연결 테이블
    사용처: weather-flick-admin-back
    설명: 관리자와 역할의 다대다 관계
    """

    __tablename__ = "admin_roles"

    admin_id = Column(Integer, ForeignKey("admins.admin_id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.role_id"), primary_key=True)
    assigned_at = Column(DateTime, server_default=func.now())
    assigned_by = Column(Integer)  # 할당한 관리자 ID


class RolePermission(Base):
    """
    역할 권한 연결 테이블
    사용처: weather-flick-admin-back
    설명: 역할과 권한의 다대다 관계
    """

    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.role_id"), primary_key=True)
    permission_id = Column(
        Integer, ForeignKey("permissions.permission_id"), primary_key=True
    )
    granted_at = Column(DateTime, server_default=func.now())
    granted_by = Column(Integer)  # 권한을 부여한 관리자 ID


class ApiRawData(Base):
    """
    API 원본 데이터 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 외부 API 원본 응답 데이터 저장
    """

    __tablename__ = "api_raw_data"

    data_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    api_source = Column(String, nullable=False)  # tour_api, weather_api 등
    endpoint = Column(String, nullable=False)
    request_params = Column(JSONB)

    # 응답 데이터
    response_status = Column(Integer)
    response_headers = Column(JSONB)
    response_body = Column(JSONB, nullable=False)

    # 메타데이터
    response_time = Column(Float)  # 응답 시간 (초)
    content_type = Column(String)
    content_length = Column(Integer)

    # 처리 상태
    is_processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)
    processing_error = Column(Text)

    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_api_raw_source", "api_source", "created_at"),
        Index("idx_api_raw_processed", "is_processed"),
    )


# ===========================================
# Pydantic 스키마 정의 (API 요청/응답용)
# ===========================================


class UserBase(BaseModel):
    """사용자 기본 스키마"""

    email: str
    nickname: str


class UserCreate(UserBase):
    """사용자 생성 스키마"""

    password: str


class UserResponse(UserBase):
    """사용자 응답 스키마"""

    user_id: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Admin 모델 확장 함수 제거 (이제 app/__init__.py에서 처리)


class TouristAttractionResponse(BaseModel):
    """
    관광지 정보 응답 스키마
    사용처: weather-flick-back, weather-flick-admin-back
    """

    content_id: str
    region_code: str
    attraction_name: str
    category_code: str | None = None
    category_name: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    tel: str | None = None
    homepage: str | None = None
    description: str | None = None
    overview: str | None = None
    first_image: str | None = None
    data_quality_score: float | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
