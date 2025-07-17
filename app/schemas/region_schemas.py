"""
지역 관리 스키마 정의
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator, ConfigDict
from datetime import datetime
from uuid import UUID


class RegionResponse(BaseModel):
    """지역 정보 응답 스키마"""
    region_id: UUID
    region_code: str
    region_name: str
    region_name_full: Optional[str] = None
    parent_region_code: Optional[str] = None
    region_level: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    grid_x: Optional[int] = None
    grid_y: Optional[int] = None
    is_active: bool
    api_mappings: Optional[Dict[str, Any]] = None
    coordinate_info: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RegionUpdateRequest(BaseModel):
    """지역 정보 업데이트 요청 스키마"""
    region_name: Optional[str] = Field(None, max_length=100)
    region_name_full: Optional[str] = Field(None, max_length=200)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    grid_x: Optional[int] = Field(None, ge=1, le=200)
    grid_y: Optional[int] = Field(None, ge=1, le=200)
    is_active: Optional[bool] = None
    api_mappings: Optional[Dict[str, Any]] = None
    coordinate_info: Optional[Dict[str, Any]] = None

    @validator('latitude')
    def validate_latitude_korea(cls, v):
        if v is not None and not (33.0 <= v <= 38.6):
            raise ValueError('위도는 한국 영역 내에 있어야 합니다 (33.0 ~ 38.6)')
        return v

    @validator('longitude')
    def validate_longitude_korea(cls, v):
        if v is not None and not (124.6 <= v <= 131.9):
            raise ValueError('경도는 한국 영역 내에 있어야 합니다 (124.6 ~ 131.9)')
        return v


class RegionCreateRequest(BaseModel):
    """지역 정보 생성 요청 스키마"""
    region_code: str = Field(..., max_length=20)
    region_name: str = Field(..., max_length=100)
    region_name_full: Optional[str] = Field(None, max_length=200)
    parent_region_code: Optional[str] = Field(None, max_length=20)
    region_level: int = Field(..., ge=1, le=2)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    grid_x: Optional[int] = Field(None, ge=1, le=200)
    grid_y: Optional[int] = Field(None, ge=1, le=200)
    is_active: bool = True
    api_mappings: Optional[Dict[str, Any]] = None
    coordinate_info: Optional[Dict[str, Any]] = None

    @validator('latitude')
    def validate_latitude_korea(cls, v):
        if v is not None and not (33.0 <= v <= 38.6):
            raise ValueError('위도는 한국 영역 내에 있어야 합니다 (33.0 ~ 38.6)')
        return v

    @validator('longitude')
    def validate_longitude_korea(cls, v):
        if v is not None and not (124.6 <= v <= 131.9):
            raise ValueError('경도는 한국 영역 내에 있어야 합니다 (124.6 ~ 131.9)')
        return v


class RegionStatsResponse(BaseModel):
    """지역 통계 응답 스키마"""
    total_regions: int
    active_regions: int
    inactive_regions: int
    provinces: int
    cities: int
    with_coordinates: int
    with_grid_coordinates: int
    with_api_mappings: int
    coordinate_coverage: float = Field(..., description="좌표 정보 보유율 (%)")
    grid_coverage: float = Field(..., description="격자 좌표 보유율 (%)")
    api_mapping_coverage: float = Field(..., description="API 매핑 보유율 (%)")


class CoordinateUpdateRequest(BaseModel):
    """좌표 정보 업데이트 요청 스키마"""
    region_code: str
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    grid_x: Optional[int] = Field(None, ge=1, le=200)
    grid_y: Optional[int] = Field(None, ge=1, le=200)

    @validator('latitude')
    def validate_latitude_korea(cls, v):
        if v is not None and not (33.0 <= v <= 38.6):
            raise ValueError('위도는 한국 영역 내에 있어야 합니다 (33.0 ~ 38.6)')
        return v

    @validator('longitude')
    def validate_longitude_korea(cls, v):
        if v is not None and not (124.6 <= v <= 131.9):
            raise ValueError('경도는 한국 영역 내에 있어야 합니다 (124.6 ~ 131.9)')
        return v


class RegionSearchRequest(BaseModel):
    """지역 검색 요청 스키마"""
    search_term: str = Field(..., min_length=1, max_length=100)
    region_level: Optional[int] = Field(None, ge=1, le=2)
    is_active: Optional[bool] = None
    has_coordinates: Optional[bool] = None
    has_api_mappings: Optional[bool] = None


class RegionHierarchyNode(BaseModel):
    """지역 계층 구조 노드 스키마"""
    region_code: str
    region_name: str
    region_level: int
    children: list['RegionHierarchyNode'] = []

    model_config = ConfigDict(from_attributes=True)


class RegionHierarchyResponse(BaseModel):
    """지역 계층 구조 응답 스키마"""
    tree: list[RegionHierarchyNode]
    total_provinces: int
    total_cities: int


class APICompatibilityIssue(BaseModel):
    """API 호환성 문제 스키마"""
    region_code: str
    region_name: str
    issue: str


class APICompatibilityReport(BaseModel):
    """API 호환성 보고서 스키마"""
    weather_api: Dict[str, Any]
    tour_api: Dict[str, Any]


class BulkUpdateResult(BaseModel):
    """일괄 업데이트 결과 스키마"""
    message: str
    updated_count: int
    failed_count: Optional[int] = 0
    errors: Optional[list[str]] = []


class CoordinateValidationResult(BaseModel):
    """좌표 유효성 검증 결과 스키마"""
    region_code: str
    valid: bool
    errors: list[str] = []


class CoordinateValidationSummary(BaseModel):
    """좌표 유효성 검증 요약 스키마"""
    total: int
    valid: int
    invalid: int


class CoordinateValidationResponse(BaseModel):
    """좌표 유효성 검증 응답 스키마"""
    validation_results: list[CoordinateValidationResult]
    summary: CoordinateValidationSummary


# 순환 참조 해결을 위한 모델 업데이트
RegionHierarchyNode.update_forward_refs()