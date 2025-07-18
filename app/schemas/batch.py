"""
배치 작업 관련 Pydantic 스키마 정의
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class BatchJobType(str, Enum):
    """배치 작업 유형"""
    KTO_DATA_COLLECTION = "KTO_DATA_COLLECTION"  # 한국관광공사 데이터 수집
    WEATHER_DATA_COLLECTION = "WEATHER_DATA_COLLECTION"  # 기상청 날씨 데이터 수집
    RECOMMENDATION_CALCULATION = "RECOMMENDATION_CALCULATION"  # 추천 점수 계산
    DATA_QUALITY_CHECK = "DATA_QUALITY_CHECK"  # 데이터 품질 검사
    ARCHIVE_BACKUP = "ARCHIVE_BACKUP"  # 아카이빙 및 백업
    SYSTEM_HEALTH_CHECK = "SYSTEM_HEALTH_CHECK"  # 시스템 헬스체크
    WEATHER_CHANGE_NOTIFICATION = "WEATHER_CHANGE_NOTIFICATION"  # 날씨 변경 알림


class BatchJobStatus(str, Enum):
    """배치 작업 상태"""
    PENDING = "PENDING"  # 대기중
    RUNNING = "RUNNING"  # 실행중
    COMPLETED = "COMPLETED"  # 완료
    FAILED = "FAILED"  # 실패
    STOPPED = "STOPPED"  # 중단됨
    STOPPING = "STOPPING"  # 중단 중


class BatchJobLogLevel(str, Enum):
    """로그 레벨"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Request 스키마
class BatchJobExecuteRequest(BaseModel):
    """배치 작업 실행 요청"""
    parameters: dict[str, Any] | None = Field(
        default={},
        description="작업 실행 매개변수"
    )
    priority: int | None = Field(
        default=5,
        ge=1,
        le=10,
        description="작업 우선순위 (1-10, 10이 가장 높음)"
    )
    notification_email: str | None = Field(
        default=None,
        description="작업 완료 알림을 받을 이메일"
    )


# Response 스키마
class BatchJobResponse(BaseModel):
    """배치 작업 상세 정보"""
    id: str
    job_type: BatchJobType
    status: BatchJobStatus
    parameters: dict[str, Any]
    progress: float = Field(ge=0, le=100)
    current_step: str | None
    total_steps: int | None
    created_at: datetime
    created_by: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    error_message: str | None
    result_summary: dict[str, Any] | None

    model_config = ConfigDict(from_attributes=True)


class BatchJobListResponse(BaseModel):
    """배치 작업 목록 응답"""
    jobs: list[BatchJobResponse]
    total_count: int
    page: int
    limit: int
    total_pages: int


class BatchJobExecuteResponse(BaseModel):
    """배치 작업 실행 응답"""
    job_id: str
    message: str
    status: BatchJobStatus


class BatchJobStatusResponse(BaseModel):
    """배치 작업 상태 응답"""
    job_id: str
    job_type: BatchJobType
    status: BatchJobStatus
    progress: float
    current_step: str | None
    total_steps: int | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    result_summary: dict[str, Any] | None


class BatchJobLog(BaseModel):
    """배치 작업 로그 항목"""
    id: str
    timestamp: datetime
    level: BatchJobLogLevel
    message: str
    details: dict[str, Any] | None


class BatchJobLogResponse(BaseModel):
    """배치 작업 로그 응답"""
    job_id: str
    logs: list[BatchJobLog]
    total_count: int
    page: int
    limit: int


class BatchJobStopResponse(BaseModel):
    """배치 작업 중단 응답"""
    job_id: str
    message: str
    status: BatchJobStatus


class BatchJobStatistic(BaseModel):
    """작업 유형별 통계"""
    job_type: BatchJobType
    total_count: int
    completed_count: int
    failed_count: int
    stopped_count: int
    running_count: int
    average_duration_seconds: float | None
    success_rate: float


class BatchJobStatisticsResponse(BaseModel):
    """배치 작업 통계 응답"""
    start_date: datetime | None
    end_date: datetime | None
    total_jobs: int
    statistics_by_type: list[BatchJobStatistic]
    recent_failures: list[BatchJobResponse]
    currently_running: list[BatchJobResponse]
