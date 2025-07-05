"""
시스템 관련 응답 스키마
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class DatabaseStatus(BaseModel):
    """데이터베이스 상태"""
    
    status: str = Field(..., description="데이터베이스 연결 상태")
    response_time: str = Field(..., description="응답 시간")


class ExternalApiStatus(BaseModel):
    """외부 API 상태"""
    
    status: str = Field(..., description="API 상태")
    response_time: str = Field(..., description="응답 시간")


class ExternalApisStatus(BaseModel):
    """모든 외부 API 상태"""
    
    weather_api: ExternalApiStatus = Field(..., description="날씨 API 상태")
    tourism_api: ExternalApiStatus = Field(..., description="관광 API 상태")
    google_places: ExternalApiStatus = Field(..., description="구글 플레이스 API 상태")


class SystemStatusData(BaseModel):
    """시스템 상태 데이터"""
    
    service_status: str = Field(..., description="전체 서비스 상태")
    database: DatabaseStatus = Field(..., description="데이터베이스 상태")
    external_apis: ExternalApisStatus = Field(..., description="외부 API 상태")


class SystemLogOut(BaseModel):
    """시스템 로그 출력"""
    
    log_id: int
    level: str
    source: str
    message: str
    context: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class SystemLogTestRequest(BaseModel):
    """시스템 로그 테스트 요청"""
    
    message: str = Field(..., description="로그 메시지")
    level: str = Field("INFO", description="로그 레벨")
    source: Optional[str] = Field(None, description="로그 소스")
    context: Optional[dict] = Field(None, description="로그 컨텍스트")


class SystemLogTestResponse(BaseModel):
    """시스템 로그 테스트 응답"""
    
    log_id: int
    level: str
    source: str
    message: str
    created_at: datetime