"""
시스템 관련 응답 스키마
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SystemStatus(str, Enum):
    """시스템 상태 열거형"""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class ServiceStatus(str, Enum):
    """서비스 상태 열거형"""
    UP = "UP"
    DOWN = "DOWN"
    MAINTENANCE = "MAINTENANCE"
    PARTIAL = "PARTIAL"


class HealthLevel(str, Enum):
    """건강 상태 레벨"""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"
    SUCCESS = "SUCCESS"


class DatabaseStatus(BaseModel):
    """데이터베이스 상태"""

    status: ServiceStatus = Field(..., description="데이터베이스 연결 상태")
    response_time: float = Field(..., description="응답 시간 (밀리초)")
    message: str = Field("", description="상태 메시지")
    last_check: datetime = Field(..., description="마지막 체크 시간")


class ExternalApiStatus(BaseModel):
    """외부 API 상태"""

    status: ServiceStatus = Field(..., description="API 상태")
    response_time: float = Field(..., description="응답 시간 (밀리초)")
    message: str = Field("", description="상태 메시지")
    last_check: datetime = Field(..., description="마지막 체크 시간")


class ExternalApisStatus(BaseModel):
    """모든 외부 API 상태"""

    weather_api: ExternalApiStatus = Field(..., description="날씨 API 상태")
    tourism_api: ExternalApiStatus = Field(..., description="관광 API 상태")
    google_places: ExternalApiStatus = Field(..., description="구글 플레이스 API 상태")


class SystemStatusData(BaseModel):
    """시스템 상태 데이터"""

    overall_status: SystemStatus = Field(..., description="전체 시스템 상태")
    service_status: ServiceStatus = Field(..., description="서비스 상태")
    health_level: HealthLevel = Field(..., description="건강 상태 레벨")
    message: str = Field("", description="시스템 상태 메시지")
    last_check: datetime = Field(..., description="마지막 체크 시간")
    uptime_seconds: int = Field(..., description="가동 시간 (초)")
    database: DatabaseStatus = Field(..., description="데이터베이스 상태")
    external_apis: ExternalApisStatus = Field(..., description="외부 API 상태")
    details: dict = Field(default_factory=dict, description="상세 정보")


class SystemLogOut(BaseModel):
    """시스템 로그 출력"""

    log_id: int
    level: str
    source: str
    message: str
    context: dict | None
    created_at: datetime

    class Config:
        from_attributes = True


class SystemLogTestRequest(BaseModel):
    """시스템 로그 테스트 요청"""

    message: str = Field(..., description="로그 메시지")
    level: str = Field("INFO", description="로그 레벨")
    source: str | None = Field(None, description="로그 소스")
    context: dict | None = Field(None, description="로그 컨텍스트")


class SystemLogTestResponse(BaseModel):
    """시스템 로그 테스트 응답"""

    log_id: int
    level: str
    source: str
    message: str
    created_at: datetime
