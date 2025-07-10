import enum
import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel,validator
from sqlalchemy import (
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
    Numeric,
    CHAR,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID, JSON
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class AdminStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"


# v3 ERD용 새로운 Enum 타입들
class SocialProvider(enum.Enum):
    GOOGLE = "GOOGLE"
    NAVER = "NAVER"
    KAKAO = "KAKAO"
    EMAIL = "EMAIL"


class TravelPlanStatus(enum.Enum):
    PLANNING = "PLANNING"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class WeatherDependency(enum.Enum):
    HIGH = "HIGH"  # 날씨에 크게 의존 (해변, 등산 등)
    MEDIUM = "MEDIUM"  # 보통 의존 (일반 관광지)
    LOW = "LOW"  # 낮은 의존 (박물관, 쇼핑몰 등)


class DestinationCategory(enum.Enum):
    TOURIST_ATTRACTION = "TOURIST_ATTRACTION"
    ACCOMMODATION = "ACCOMMODATION"
    RESTAURANT = "RESTAURANT"
    SHOPPING = "SHOPPING"
    CULTURAL_FACILITY = "CULTURAL_FACILITY"
    FESTIVAL_EVENT = "FESTIVAL_EVENT"


class UserRole(enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class User(Base):
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
    preferences = Column(JSONB)
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

    travel_plans = relationship("TravelPlan", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    activity_logs = relationship("UserActivityLog", back_populates="user")
    social_accounts = relationship("UserSocialAccount", back_populates="user")
    user_preferences = relationship("UserPreference", back_populates="user", uselist=False)


class Admin(Base):
    __tablename__ = "admins"
    admin_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String)
    phone = Column(String)
    status = Column(Enum(AdminStatus), default=AdminStatus.ACTIVE)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    roles = relationship("AdminRole", back_populates="admin")


class AdminActivityLog(Base):
    """관리자 활동 로그 모델"""
    __tablename__ = "admin_activity_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.admin_id"), nullable=False)
    action = Column(String, nullable=False)  # 수행된 작업 (예: USER_DELETE, USER_UPDATE)
    description = Column(Text, nullable=False)  # 작업 설명
    target_resource = Column(String, nullable=True)  # 대상 리소스 (예: user_id, plan_id)
    severity = Column(String, default="NORMAL")  # 심각도 (NORMAL, HIGH, CRITICAL)
    ip_address = Column(String, nullable=True)  # IP 주소
    user_agent = Column(String, nullable=True)  # 사용자 에이전트
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    admin = relationship("Admin", foreign_keys=[admin_id])

    def __repr__(self):
        return f"<AdminActivityLog(admin_id='{self.admin_id}', action='{self.action}', severity='{self.severity}')>"


class Role(Base):
    __tablename__ = "roles"
    role_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    display_name = Column(String)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    admins = relationship("AdminRole", back_populates="role")


class AdminRole(Base):
    __tablename__ = "admin_roles"
    admin_id = Column(Integer, ForeignKey("admins.admin_id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.role_id"), primary_key=True)
    assigned_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    admin = relationship("Admin", back_populates="roles")
    role = relationship("Role", back_populates="admins")


class Destination(Base):
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
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    amenities = Column(JSONB)
    image_url = Column(String)
    rating = Column(Float)
    recommendation_weight = Column(DECIMAL(3, 2))
    created_at = Column(DateTime, server_default=func.now())

    weather_data = relationship("WeatherData", back_populates="destination")
    reviews = relationship("Review", back_populates="destination")


class TravelPlan(Base):
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
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="travel_plans")
    reviews = relationship("Review", back_populates="travel_plan")


# 성능 개선을 위한 복합 인덱스
Index("idx_travel_plan_user_status", TravelPlan.user_id, TravelPlan.status)
Index("idx_travel_plan_dates", TravelPlan.start_date, TravelPlan.end_date)


class WeatherData(Base):
    __tablename__ = "weather_data"
    weather_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=True
    )
    # 기상청 격자 좌표
    grid_x = Column(Integer)  # nx: 예보지점 X 좌표
    grid_y = Column(Integer)  # ny: 예보지점 Y 좌표

    # 예보 날짜와 시간
    forecast_date = Column(Date, nullable=False)
    forecast_time = Column(String)  # 예보시간 (HHMM 형식)
    base_date = Column(Date)  # 발표일자
    base_time = Column(String)  # 발표시각

    # 기온 정보
    temperature = Column(Float)  # TMP: 1시간 기온 (℃)
    temperature_max = Column(Float)  # TMX: 일 최고기온 (℃)
    temperature_min = Column(Float)  # TMN: 일 최저기온 (℃)

    # 습도 및 강수 정보
    humidity = Column(Float)  # REH: 습도 (%)
    precipitation_probability = Column(Float)  # POP: 강수확률 (%)
    precipitation_type = Column(String)  # PTY: 강수형태 (없음/비/비눈/눈)

    # 하늘 상태
    sky_condition = Column(String)  # SKY: 하늘상태 (맑음/구름많음/흐림)
    weather_condition = Column(String)  # 종합 날씨 상태

    # 지역 정보
    region_name = Column(String)  # 지역명

    # 원본 데이터
    raw_data = Column(JSONB)  # 원본 API 응답 데이터

    created_at = Column(DateTime, server_default=func.now())

    destination = relationship("Destination", back_populates="weather_data")


# WeatherData 성능 최적화 인덱스
Index(
    "idx_weather_forecast_location",
    WeatherData.forecast_date,
    WeatherData.grid_x,
    WeatherData.grid_y,
)
Index(
    "idx_weather_destination_date",
    WeatherData.destination_id,
    WeatherData.forecast_date,
)


class Review(Base):
    __tablename__ = "reviews"
    review_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=False
    )
    travel_plan_id = Column(
        UUID(as_uuid=True), ForeignKey("travel_plans.plan_id"), nullable=True
    )
    rating = Column(Integer, nullable=False)
    content = Column(Text)
    photos = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="reviews")
    destination = relationship("Destination", back_populates="reviews")
    travel_plan = relationship("TravelPlan", back_populates="reviews")


# Review 성능 최적화 인덱스
Index("idx_review_destination_date", Review.destination_id, Review.created_at)
Index("idx_review_user_rating", Review.user_id, Review.rating)


class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"
    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    activity_type = Column(String, nullable=False)
    resource_type = Column(String)
    details = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="activity_logs")


class SystemLog(Base):
    __tablename__ = "system_logs"
    log_id = Column(Integer, primary_key=True, index=True)
    level = Column(String, nullable=False)
    source = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    context = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())


class EmailVerification(Base):
    __tablename__ = "email_verifications"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class FavoritePlace(Base):
    __tablename__ = "favorite_places"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    place_name = Column(String, nullable=False)
    place_type = Column(String, nullable=False)  # restaurant, accommodation, transport
    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())




class CityInfo(Base):
    __tablename__ = "city_info"
    id = Column(Integer, primary_key=True, index=True)
    city_name = Column(String, nullable=False, unique=True)
    region = Column(String, nullable=False)
    population = Column(Integer)
    area = Column(Float)
    description = Column(Text)
    attractions = Column(JSONB)
    weather_info = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())


# Pydantic 모델들
class WeatherRequest(BaseModel):
    city: str
    country: str | None = None


class WeatherCondition(BaseModel):
    temperature: float
    feels_like: float
    humidity: int
    pressure: float
    condition: str
    description: str
    icon: str
    wind_speed: float
    wind_direction: int
    visibility: float
    uv_index: float


class WeatherResponse(BaseModel):
    city: str
    country: str
    current: WeatherCondition
    timezone: str
    local_time: str


class ForecastDay(BaseModel):
    date: str
    temperature_max: float
    temperature_min: float
    condition: str
    description: str
    icon: str
    humidity: int
    wind_speed: float
    precipitation_chance: float


class ForecastResponse(BaseModel):
    city: str
    country: str
    forecast: list[ForecastDay]
    timezone: str


# 인증 관련 Pydantic 모델들
class TokenData(BaseModel):
    email: str | None = None
    role: str | None = None


class UserCreate(BaseModel):
    email: str
    password: str
    nickname: str


class UserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    nickname: str | None = None
    profile_image: str | None = None
    preferred_region: str | None = None
    preferred_theme: str | None = None
    bio: str | None = None
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_info: UserResponse


class UserUpdate(BaseModel):
    nickname: str | None = None
    profile_image: str | None = None
    preferences: list[str | None] = []
    preferred_region: str | None = None
    preferred_theme: str | None = None
    bio: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class GoogleLoginRequest(BaseModel):
    code: str
    redirect_uri: str


class GoogleLoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_info: UserResponse
    is_new_user: bool


class GoogleAuthUrlResponse(BaseModel):
    auth_url: str
    state: str


class GoogleAuthCodeRequest(BaseModel):
    auth_code: str


class EmailVerificationRequest(BaseModel):
    email: str
    nickname: str


class EmailVerificationConfirm(BaseModel):
    email: str
    code: str


class EmailVerificationResponse(BaseModel):
    message: str
    success: bool


class ResendVerificationRequest(BaseModel):
    email: str
    nickname: str


# 추천 및 여행 계획 관련 모델들
class StandardResponse(BaseModel):
    success: bool
    message: str
    data: dict[str, Any | None] = {}


class PaginationInfo(BaseModel):
    page: int
    page_size: int
    total_count: int
    total_pages: int


class DestinationCreate(BaseModel):
    name: str
    province: str
    region: str | None = None
    category: str | None = None
    is_indoor: bool | None = False
    tags: list[str | None] = []
    latitude: float | None = None
    longitude: float | None = None
    amenities: dict[str, Any | None] = {}
    image_url: str | None = None


class DestinationResponse(BaseModel):
    destination_id: uuid.UUID
    name: str
    province: str
    region: str | None = None
    category: str | None = None
    is_indoor: bool | None = None
    tags: list[str | None] = []
    latitude: float | None = None
    longitude: float | None = None
    amenities: dict[str, Any | None] = {}
    image_url: str | None = None
    rating: float | None = None
    recommendation_weight: float | None = None

    class Config:
        from_attributes = True


class RecommendationRequest(BaseModel):
    destination_types: list[str | None] = []
    budget_range: dict[str, float | None] = {}
    travel_dates: dict[str, str | None] = {}
    preferences: dict[str, Any | None] = {}


class RecommendationResponse(BaseModel):
    destinations: list[DestinationResponse]
    total_count: int
    recommendation_score: float


class TravelPlanCreate(BaseModel):
    title: str
    description: str | None = None
    start_date: str
    end_date: str
    budget: float | None = None
    itinerary: dict[str, list[dict[str, Any]]] | None = None
    participants: int | None = None
    transportation: str | None = None
    start_location: str | None = None  # 출발지 추가
    weather_info: dict[str, Any] | None = None  # 날씨 정보 추가


class TravelPlanUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    budget: float | None = None
    status: str | None = None
    itinerary: dict[str, list[dict[str, Any]]] | None = None
    participants: int | None = None
    transportation: str | None = None
    start_location: str | None = None
    weather_info: dict[str, Any] | None = None


class TravelPlanResponse(BaseModel):
    plan_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None = None
    start_date: date
    end_date: date
    budget: float | None = None
    status: str
    itinerary: dict[str, list[dict[str, Any]]] | None = None
    participants: int | None = None
    transportation: str | None = None
    start_location: str | None = None
    weather_info: dict[str, Any] | None = None
    created_at: datetime

    @validator('budget', pre=True)
    def decimal_to_float(cls, v):
        if v is None:
            return v
        try:
            return float(v)
        except Exception:
            return None

    class Config:
        from_attributes = True


# 지역 정보 관련 모델들
class SearchRequest(BaseModel):
    query: str
    category: str | None = None
    location: str | None = None
    limit: int | None = 10


class SearchResult(BaseModel):
    results: list[dict[str, Any]]
    total_count: int
    category: str








class CityInfoResponse(BaseModel):
    city_name: str
    region: str
    population: int | None = None
    area: float | None = None
    description: str | None = None
    attractions: list[str | None] = []
    weather_info: dict[str, Any | None] = {}


class FavoritePlaceResponse(BaseModel):
    id: int
    place_name: str
    place_type: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    destination_id: uuid.UUID
    travel_plan_id: uuid.UUID | None = None
    rating: int
    content: str | None = None
    photos: list[str | None] = []


class ReviewResponse(BaseModel):
    review_id: uuid.UUID
    user_id: uuid.UUID
    destination_id: uuid.UUID
    travel_plan_id: uuid.UUID | None = None
    rating: int
    content: str | None = None
    photos: list[str | None] = []
    created_at: datetime

    class Config:
        from_attributes = True


# 사용자 활동 로그 테이블 (이미 UserActivityLog가 있으므로 별칭으로 사용)
UserActivity = UserActivityLog


# ===========================================
# 실제 데이터베이스 테이블에 대응하는 ORM 모델들
# ===========================================











class TravelCourse(Base):
    __tablename__ = "travel_courses"

    content_id = Column(String(20), primary_key=True, index=True)
    region_code = Column(String(10), nullable=False)
    sigungu_code = Column(String(10))
    course_name = Column(String(300), nullable=False)
    category_code = Column(String(10))
    sub_category_code = Column(String(10))
    address = Column(String(300))
    detail_address = Column(String(300))
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    zipcode = Column(String(10))
    tel = Column(String(500))
    homepage = Column(String(500))
    overview = Column(Text)
    first_image = Column(String(500))
    first_image_small = Column(String(500))
    course_theme = Column(String(100))
    course_distance = Column(String(50))
    required_time = Column(String(100))
    difficulty_level = Column(String(20))
    schedule = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    raw_data_id = Column(UUID(as_uuid=True))
    last_sync_at = Column(DateTime, default=datetime.utcnow)
    data_quality_score = Column(Numeric(5, 2))
    processing_status = Column(String(20), default='processed')
    booktour = Column(CHAR(1))
    createdtime = Column(String(14))
    modifiedtime = Column(String(14))
    telname = Column(String(100))
    faxno = Column(String(50))
    mlevel = Column(Integer)
    detail_intro_info = Column(JSON)
    detail_additional_info = Column(JSON)


# RestaurantNew 클래스 제거 - 기존 Restaurant 클래스에 통합됨


# AccommodationNew 클래스 제거 - 기존 Accommodation 클래스에 통합됨




class PetTourInfo(Base):
    """반려동물 관광정보 테이블"""

    __tablename__ = "pet_tour_info"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Unique 필드
    content_id = Column(String(50), unique=True)

    # Foreign Keys
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    content_type_id = Column(String)
    title = Column(String)

    # 주소 및 위치 정보
    address = Column(String)
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    area_code = Column(String)
    sigungu_code = Column(String)

    # 연락처 정보
    tel = Column(String)
    homepage = Column(Text)

    # 설명 및 이미지
    overview = Column(Text)
    first_image = Column(Text)
    first_image2 = Column(Text)

    # 카테고리
    cat1 = Column(String)
    cat2 = Column(String)
    cat3 = Column(String)

    # 반려동물 관련 정보
    pet_acpt_abl = Column(String)  # 반려동물 수용 가능 여부
    pet_info = Column(Text)  # 반려동물 관련 상세 정보

    # 메타데이터
    data_quality_score = Column(DECIMAL(5, 2))
    processing_status = Column(String(20), default="processed")
    last_sync_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UnifiedRegionNew(Base):
    """통합 지역정보 테이블 (기존 UnifiedRegion 클래스와 구분)"""

    __tablename__ = "unified_regions"
    __table_args__ = {"extend_existing": True, "autoload_replace": False}

    # Primary Key
    region_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )

    # Unique 필드
    region_code = Column(String(20), unique=True, index=True)

    # Foreign Keys (자기 참조)
    parent_region_id = Column(
        UUID(as_uuid=True),
        ForeignKey("unified_regions.region_id"),
        nullable=True,
        index=True,
    )

    # 기본 정보
    region_name = Column(String, nullable=False)
    region_name_full = Column(String)
    region_name_en = Column(String)
    region_level = Column(Integer)

    # 좌표 정보
    center_latitude = Column(String)
    center_longitude = Column(String)
    boundary_data = Column(JSONB)

    # 행정 정보
    administrative_code = Column(String)
    is_active = Column(Boolean, default=True)

    # 메타데이터
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정 (자기 참조) - 임시 주석 처리
    # children = relationship("UnifiedRegionNew", back_populates="parent")
    # parent = relationship("UnifiedRegionNew", remote_side=[region_id], back_populates="children")


# 성능 최적화를 위한 인덱스들
Index(
    "idx_unified_regions_code_level",
    UnifiedRegionNew.region_code,
    UnifiedRegionNew.region_level,
)


class Region(Base):
    __tablename__ = "regions"
    region_code = Column(String, primary_key=True)
    region_name = Column(String, nullable=False)
    parent_region_code = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    region_level = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# UnifiedRegion 클래스 제거 - UnifiedRegionNew와 중복으로 인한 테이블 생성 오류 해결
# 기능은 UnifiedRegionNew 클래스에서 제공
# 임시 비밀번호 관련 스키마
class ForgotPasswordRequest(BaseModel):
    """비밀번호 찾기 요청"""

    email: str

    class Config:
        json_schema_extra = {"example": {"email": "user@example.com"}}


class ForgotPasswordResponse(BaseModel):
    """비밀번호 찾기 응답"""

    message: str
    success: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "message": "임시 비밀번호가 이메일로 전송되었습니다.",
                "success": True,
            }
        }


# 회원탈퇴 관련 스키마
class WithdrawRequest(BaseModel):
    """회원탈퇴 요청"""

    password: str | None = None  # 소셜 로그인 사용자는 비밀번호 불필요
    reason: str | None = None  # 탈퇴 사유 (선택사항)

    class Config:
        json_schema_extra = {
            "example": {
                "password": "current_password",
                "reason": "서비스 이용이 불필요해짐",
            }
        }


class WithdrawResponse(BaseModel):
    """회원탈퇴 응답"""

    message: str
    success: bool = True

    class Config:
        json_schema_extra = {
            "example": {"message": "회원탈퇴가 완료되었습니다.", "success": True}
        }


# ===========================================
# 새로 추가된 모델들에 대한 Pydantic 스키마
# ===========================================










# RestaurantNewResponse와 AccommodationNewResponse는 기존 RestaurantResponse와 AccommodationResponse로 대체됨
# 기존 스키마가 새로운 데이터 구조를 지원하도록 업데이트 필요






class UnifiedRegionResponse(BaseModel):
    """통합 지역정보 응답 스키마"""

    region_id: uuid.UUID
    region_code: str | None = None
    region_name: str
    region_name_full: str | None = None
    region_name_en: str | None = None
    region_level: int | None = None
    center_latitude: str | None = None
    center_longitude: str | None = None
    administrative_code: str | None = None
    is_active: bool | None = True
    created_at: datetime | None = None

    class Config:
        from_attributes = True


# v3 ERD 핵심 모델들 추가
class UserSocialAccount(Base):
    """소셜 로그인 계정 정보"""

    __tablename__ = "user_social_accounts"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    provider = Column(Enum(SocialProvider), nullable=False)
    social_id = Column(String, nullable=False)  # 소셜 플랫폼에서의 ID
    email = Column(String)
    name = Column(String)
    profile_image_url = Column(String)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 복합 유니크 제약조건
    __table_args__ = (
        Index("idx_user_social_provider", "user_id", "provider"),
        Index("idx_social_provider_id", "provider", "social_id"),
        {"extend_existing": True},
    )

    # 관계 설정
    user = relationship("User", back_populates="social_accounts")


class UserPreference(Base):
    """사용자 선호 설정"""

    __tablename__ = "user_preferences"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    preferred_regions = Column(JSONB)  # ["서울", "부산", "제주"]
    preferred_themes = Column(JSONB)  # ["문화관광", "자연관광", "음식여행"]
    preferred_activities = Column(JSONB)  # ["등산", "쇼핑", "사진촬영"]
    weather_preferences = Column(
        JSONB
    )  # {"min_temp": 15, "max_temp": 25, "no_rain": true}
    accessibility_needs = Column(JSONB)  # {"wheelchair": true, "parking": true}
    budget_range = Column(String)  # "BUDGET", "STANDARD", "PREMIUM"
    travel_style = Column(String)  # "RELAXED", "ACTIVE", "CULTURAL"
    notification_settings = Column(JSONB)  # 알림 설정
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    user = relationship("User", back_populates="user_preferences")


class TravelDay(Base):
    """여행 계획의 일별 상세"""

    __tablename__ = "travel_days"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    travel_plan_id = Column(
        UUID(as_uuid=True), ForeignKey("travel_plans.plan_id"), nullable=False
    )
    day_number = Column(Integer, nullable=False)  # 1일차, 2일차 등
    date = Column(Date, nullable=False)
    title = Column(String, nullable=False)  # "서울 도심 탐방"
    description = Column(Text)
    total_budget = Column(DECIMAL(10, 2))
    weather_forecast = Column(JSONB)  # 해당 날짜 날씨 예보
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_travel_plan_day", "travel_plan_id", "day_number"),
        {"extend_existing": True},
    )

    # 관계 설정
    travel_plan = relationship("TravelPlan", back_populates="travel_days")
    destinations = relationship("TravelDayDestination", back_populates="travel_day")


class TravelDayDestination(Base):
    """일별 여행지 방문 계획"""

    __tablename__ = "travel_day_destinations"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    travel_day_id = Column(
        UUID(as_uuid=True), ForeignKey("travel_days.id"), nullable=False
    )
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=False
    )
    visit_order = Column(Integer, nullable=False)  # 방문 순서 (1, 2, 3...)
    planned_arrival_time = Column(DateTime)
    planned_departure_time = Column(DateTime)
    planned_duration_minutes = Column(Integer)  # 예상 체류 시간 (분)
    planned_budget = Column(DECIMAL(10, 2))
    transportation_method = Column(String)  # "CAR", "PUBLIC", "WALK"
    notes = Column(Text)  # 개인 메모
    weather_dependency = Column(Enum(WeatherDependency))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_travel_day_order", "travel_day_id", "visit_order"),
        {"extend_existing": True},
    )

    # 관계 설정
    travel_day = relationship("TravelDay", back_populates="destinations")
    destination = relationship("Destination", back_populates="travel_day_destinations")


# Destination 모델에 travel_day_destinations 관계 추가
Destination.travel_day_destinations = relationship("TravelDayDestination", back_populates="destination")

# TravelPlan 모델에 travel_days 관계 추가
TravelPlan.travel_days = relationship("TravelDay", back_populates="travel_plan")


class WeatherSnapshot(Base):
    """특정 시점의 날씨 데이터"""

    __tablename__ = "weather_snapshots"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    weather_region_id = Column(
        UUID(as_uuid=True), ForeignKey("weather_regions.id"), nullable=False
    )
    forecast_date = Column(Date, nullable=False)
    forecast_datetime = Column(DateTime, nullable=False)
    temperature = Column(Float)  # 온도 (°C)
    feels_like = Column(Float)  # 체감온도 (°C)
    humidity = Column(Integer)  # 습도 (%)
    precipitation = Column(Float)  # 강수량 (mm)
    precipitation_probability = Column(Integer)  # 강수 확률 (%)
    wind_speed = Column(Float)  # 풍속 (m/s)
    wind_direction = Column(String)  # 풍향
    weather_main = Column(String)  # "Clear", "Clouds", "Rain" 등
    weather_description = Column(String)  # 상세 날씨 설명
    visibility = Column(Integer)  # 가시거리 (m)
    uv_index = Column(Float)  # 자외선 지수
    air_quality_index = Column(Integer)  # 대기질 지수
    data_source = Column(String, nullable=False)  # "KMA", "OPENWEATHER" 등
    collected_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_weather_region_date", "weather_region_id", "forecast_date"),
        Index("idx_forecast_datetime", "forecast_datetime"),
        {"extend_existing": True},
    )

    # 관계 설정
    weather_region = relationship("WeatherRegion", back_populates="weather_snapshots")


class WeatherRegion(Base):
    """날씨 예보 지역"""

    __tablename__ = "weather_regions"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_code = Column(String, unique=True, nullable=False)  # 기상청 지역코드
    region_name = Column(String, nullable=False)  # "서울특별시 강남구"
    parent_region = Column(String)  # 상위 지역 "서울특별시"
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timezone = Column(String, default="Asia/Seoul")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    weather_snapshots = relationship("WeatherSnapshot", back_populates="weather_region")


class ContentApproval(Base):
    """콘텐츠 승인 관리"""

    __tablename__ = "content_approvals"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_type = Column(String, nullable=False)  # "DESTINATION", "REVIEW", "IMAGE"
    content_id = Column(UUID(as_uuid=True), nullable=False)  # 관련 콘텐츠 ID
    status = Column(
        String, nullable=False, default="PENDING"
    )  # "PENDING", "APPROVED", "REJECTED"
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    reviewed_by = Column(Integer, ForeignKey("admins.admin_id"))
    review_notes = Column(Text)  # 승인/거부 사유
    submitted_at = Column(DateTime, server_default=func.now())
    reviewed_at = Column(DateTime)

    # 인덱스
    __table_args__ = (
        Index("idx_content_approval_status", "content_type", "status"),
        Index("idx_content_approval_submitted", "submitted_at"),
        {"extend_existing": True},
    )

    # 관계 설정
    submitter = relationship("User", foreign_keys=[submitted_by])
    reviewer = relationship("Admin", foreign_keys=[reviewed_by])


# 관리자용 데이터 소스 및 확장성 관리
class DataSource(Base):
    """외부 데이터 소스 관리"""

    __tablename__ = "data_sources"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(
        String, nullable=False, unique=True
    )  # "한국관광공사", "기상청", "구글맵"
    api_endpoint = Column(String)
    api_key_name = Column(String)  # 환경변수명
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime)
    sync_frequency_hours = Column(Integer, default=24)  # 동기화 주기
    rate_limit_per_hour = Column(Integer)  # 시간당 요청 제한
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ExternalDestination(Base):
    """외부 수집 여행지 데이터 (승인 전)"""

    __tablename__ = "external_destinations"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_source_id = Column(
        UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False
    )
    external_id = Column(String, nullable=False)  # 외부 시스템의 ID
    raw_data = Column(JSONB)  # 원본 JSON 데이터
    parsed_data = Column(JSONB)  # 파싱된 구조화 데이터

    # 관리자 승인 상태
    approval_status = Column(
        String, default="PENDING"
    )  # PENDING, APPROVED, REJECTED, MERGED
    approved_by = Column(Integer, ForeignKey("admins.admin_id"))
    approved_at = Column(DateTime)
    merged_to_destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id")
    )

    # 메타데이터
    quality_score = Column(Float, default=0.0)
    duplicate_check_status = Column(
        String, default="UNCHECKED"
    )  # UNCHECKED, UNIQUE, DUPLICATE
    duplicate_of = Column(UUID(as_uuid=True), ForeignKey("external_destinations.id"))

    collected_at = Column(DateTime, server_default=func.now())
    last_processed_at = Column(DateTime)

    # 인덱스
    __table_args__ = (
        Index("idx_external_dest_source", "data_source_id", "external_id"),
        Index("idx_external_dest_approval", "approval_status"),
        {"extend_existing": True},
    )

    # 관계 설정
    data_source = relationship("DataSource")
    approver = relationship("Admin", foreign_keys=[approved_by])
    merged_destination = relationship(
        "Destination", foreign_keys=[merged_to_destination_id]
    )


# 기존 Destination 모델에 추가 필드들
# (확장성과 관리자 관리를 위한 필드 추가)
