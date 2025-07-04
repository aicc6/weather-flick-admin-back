import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Boolean,
    DateTime,
    Date,
    Enum,
    ForeignKey,
    DECIMAL,
    UniqueConstraint,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum


Base = declarative_base()


class AccountType(enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class AdminStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"


class TravelPlanStatus(enum.Enum):
    PLANNING = "PLANNING"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


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
    hashed_password = Column(String, nullable=False)
    nickname = Column(String)
    profile_image = Column(String)
    preferences = Column(JSONB)
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    last_login = Column(DateTime)
    login_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    preferred_region = Column(String, nullable=True)
    preferred_theme = Column(String, nullable=True)
    bio = Column(Text, nullable=True)

    # id 속성을 user_id의 별칭으로 추가
    @property
    def id(self):
        return self.user_id

    travel_plans = relationship("TravelPlan", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    activity_logs = relationship("UserActivityLog", back_populates="user")

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', email='{self.email}', nickname='{self.nickname}')>"


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
    # id 속성을 admin_id의 별칭으로 추가
    @property
    def id(self):
        return self.admin_id


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
    name = Column(String, nullable=False)
    region = Column(String)
    category = Column(String)
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
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
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="travel_plans")
    reviews = relationship("Review", back_populates="travel_plan")


class WeatherData(Base):
    __tablename__ = "weather_data"
    weather_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=False
    )
    forecast_date = Column(Date, nullable=False)
    temperature_max = Column(Float)
    temperature_min = Column(Float)
    humidity = Column(Float)
    weather_condition = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    destination = relationship("Destination", back_populates="weather_data")


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


class CityWeatherData(Base):
    __tablename__ = "city_weather_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    city_name = Column(String, nullable=False, index=True)
    nx = Column(Integer, nullable=False)  # 기상청 격자 X좌표
    ny = Column(Integer, nullable=False)  # 기상청 격자 Y좌표
    latitude = Column(DECIMAL(10, 8))     # 위도
    longitude = Column(DECIMAL(11, 8))    # 경도

    # 날씨 데이터
    temperature = Column(Float)           # 기온 (°C)
    humidity = Column(Integer)            # 습도 (%)
    precipitation = Column(Float)         # 강수량 (mm)
    wind_speed = Column(Float)           # 풍속 (m/s)
    wind_direction = Column(Integer)  # 풍향 (deg)
    sky_condition = Column(String)       # 하늘상태
    precipitation_type = Column(String)  # 강수형태
    weather_description = Column(String) # 날씨 설명

    # 메타데이터
    forecast_time = Column(DateTime, nullable=False)  # 예보 시각
    base_date = Column(String)           # 발표일자 (YYYYMMDD)
    base_time = Column(String)           # 발표시각 (HHMM)
    data_source = Column(String, default="KMA")  # 데이터 출처
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 유니크 제약 조건 (도시명 + 예보시각 조합으로 중복 방지)
    __table_args__ = (
        UniqueConstraint('city_name', 'forecast_time', name='_city_forecast_time_uc'),
    )


class TouristAttraction(Base):
    __tablename__ = "tourist_attractions"
    content_id = Column(String, primary_key=True, index=True)
    attraction_name = Column(String)
    description = Column(Text)
    address = Column(String)
    image_url = Column(String)
    latitude = Column(Numeric)
    longitude = Column(Numeric)
    category_code = Column(String)
    category_name = Column(String)
    region_code = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
