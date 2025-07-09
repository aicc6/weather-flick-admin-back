"""
공통 응답 스키마 정의
모든 API 응답에 사용할 표준 형식을 제공합니다.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """에러 상세 정보"""

    code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    field: str | None = Field(None, description="에러 관련 필드명")


class ErrorResponse(BaseModel):
    """에러 응답 형식"""

    code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    details: list[ErrorDetail] | None = Field(None, description="상세 에러 정보")


class MetaInfo(BaseModel):
    """메타 정보 (페이지네이션, 통계 등)"""

    total: int | None = Field(None, description="전체 항목 수")
    page: int | None = Field(None, description="현재 페이지")
    size: int | None = Field(None, description="페이지 크기")
    total_pages: int | None = Field(None, description="전체 페이지 수")


class BaseResponse(BaseModel, Generic[T]):
    """표준 API 응답 형식"""

    success: bool = Field(..., description="요청 성공 여부")
    data: T | None = Field(None, description="응답 데이터")
    message: str = Field(..., description="응답 메시지")
    error: ErrorResponse | None = Field(None, description="에러 정보")
    meta: MetaInfo | None = Field(None, description="메타 정보")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SuccessResponse(BaseResponse[T], Generic[T]):
    """성공 응답 헬퍼"""

    def __init__(
        self,
        data: T = None,
        message: str = "요청이 성공적으로 처리되었습니다.",
        meta: MetaInfo = None,
        timestamp: datetime = None,
    ):
        super().__init__(
            success=True,
            data=data,
            message=message,
            error=None,
            meta=meta,
            timestamp=timestamp or datetime.now(),
        )


class ErrorResponseModel(BaseResponse[None]):
    """에러 응답 헬퍼"""

    def __init__(
        self,
        error: ErrorResponse,
        message: str = "요청 처리 중 오류가 발생했습니다.",
        timestamp: datetime = None,
    ):
        super().__init__(
            success=False,
            data=None,
            message=message,
            error=error,
            meta=None,
            timestamp=timestamp or datetime.now(),
        )


# 페이지네이션 응답용 헬퍼
class PaginatedResponse(SuccessResponse[list[T]], Generic[T]):
    """페이지네이션 응답 헬퍼"""

    def __init__(
        self,
        items: list[T],
        total: int,
        page: int,
        size: int,
        message: str = "목록을 성공적으로 조회했습니다.",
        **kwargs,
    ):
        total_pages = (total + size - 1) // size if size > 0 else 0
        meta = MetaInfo(total=total, page=page, size=size, total_pages=total_pages)
        super().__init__(data=items, message=message, meta=meta, **kwargs)


# 자주 사용하는 응답 타입들
MessageResponse = SuccessResponse[dict[str, Any]]
EmptySuccessResponse = SuccessResponse[None]
