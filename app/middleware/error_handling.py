"""
관리자 백엔드용 통합 에러 처리 미들웨어
더 엄격한 에러 처리 및 상세한 로깅
"""
import traceback
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


class AdminErrorHandlingMiddleware(BaseHTTPMiddleware):
    """관리자용 에러 처리 미들웨어 (더 상세한 로깅)"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 요청 ID 생성 (추적용)
        request_id = str(uuid.uuid4())[:8]
        
        # 관리자 요청 로깅
        logger.info(
            f"Admin Request [{request_id}] {request.method} {request.url} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            
            # 성공 응답 로깅
            logger.info(
                f"Admin Response [{request_id}] {response.status_code}"
            )
            
            return response
            
        except HTTPException as exc:
            return await self._handle_http_exception(request, exc, request_id)
            
        except RequestValidationError as exc:
            return await self._handle_validation_error(request, exc, request_id)
            
        except SQLAlchemyError as exc:
            return await self._handle_database_error(request, exc, request_id)
            
        except Exception as exc:
            return await self._handle_unexpected_error(request, exc, request_id)
    
    async def _handle_http_exception(
        self, request: Request, exc: HTTPException, request_id: str
    ) -> JSONResponse:
        """HTTPException 처리 (관리자용 상세 로깅)"""
        logger.warning(
            f"Admin HTTP Exception [{request_id}] {request.method} {request.url}: "
            f"{exc.status_code} - {exc.detail}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "admin_http_error",
                    "code": exc.status_code,
                    "message": exc.detail,
                    "request_id": request_id,
                    "timestamp": str(uuid.uuid4()),
                }
            },
            headers=exc.headers or {},
        )
    
    async def _handle_validation_error(
        self, request: Request, exc: RequestValidationError, request_id: str
    ) -> JSONResponse:
        """요청 검증 오류 처리 (관리자용 상세 정보)"""
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input"),
            })
        
        logger.error(
            f"Admin Validation Error [{request_id}] {request.method} {request.url}: "
            f"{len(errors)} validation errors - {errors}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "admin_validation_error",
                    "code": 422,
                    "message": "관리자 요청 데이터 검증에 실패했습니다.",
                    "details": errors,
                    "request_id": request_id,
                }
            },
        )
    
    async def _handle_database_error(
        self, request: Request, exc: SQLAlchemyError, request_id: str
    ) -> JSONResponse:
        """데이터베이스 오류 처리 (관리자용 상세 로깅)"""
        error_details = {
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "request_path": str(request.url),
            "request_method": request.method,
        }
        
        logger.error(
            f"Admin Database Error [{request_id}]: {error_details}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "admin_database_error",
                    "code": 500,
                    "message": "관리자 데이터베이스 처리 중 오류가 발생했습니다.",
                    "request_id": request_id,
                    "details": error_details,  # 관리자에게는 상세 정보 제공
                }
            },
        )
    
    async def _handle_unexpected_error(
        self, request: Request, exc: Exception, request_id: str
    ) -> JSONResponse:
        """예상치 못한 오류 처리 (관리자용 전체 스택 트레이스)"""
        error_trace = traceback.format_exc()
        
        error_details = {
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "stack_trace": error_trace,
            "request_path": str(request.url),
            "request_method": request.method,
            "client_host": request.client.host if request.client else "unknown",
        }
        
        logger.critical(
            f"Admin Unexpected Error [{request_id}]: {error_details}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "admin_internal_error",
                    "code": 500,
                    "message": "관리자 서버 내부 오류가 발생했습니다.",
                    "request_id": request_id,
                    "details": error_details,  # 관리자에게는 전체 정보 제공
                }
            },
        )


class AdminTimeoutMiddleware(BaseHTTPMiddleware):
    """관리자용 타임아웃 처리 (더 긴 시간 허용)"""
    
    def __init__(self, app, timeout_seconds: int = 60):  # 관리자는 60초
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import asyncio
        
        try:
            return await asyncio.wait_for(
                call_next(request), timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Admin Request timeout: {request.method} {request.url} "
                f"(>{self.timeout_seconds}s)"
            )
            return JSONResponse(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                content={
                    "error": {
                        "type": "admin_timeout_error",
                        "code": 408,
                        "message": "관리자 요청 처리 시간이 초과되었습니다.",
                        "timeout": self.timeout_seconds,
                    }
                },
            )


class AdminHealthCheckMiddleware(BaseHTTPMiddleware):
    """관리자용 헬스체크 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 헬스체크 엔드포인트
        if request.url.path in ["/health", "/", "/api/health"]:
            try:
                # 데이터베이스 연결 확인
                from app.database import check_db_connection, get_pool_status
                
                db_ok, db_msg = check_db_connection()
                pool_status = get_pool_status()
                
                if not db_ok:
                    logger.warning(f"Admin health check database failure: {db_msg}")
                    return JSONResponse(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content={
                            "status": "unhealthy",
                            "database": db_msg,
                            "pool_status": pool_status,
                            "service": "weather-flick-admin"
                        }
                    )
                
                return JSONResponse(
                    content={
                        "status": "healthy",
                        "database": "connected",
                        "pool_status": pool_status,
                        "service": "weather-flick-admin"
                    }
                )
            except Exception as e:
                logger.error(f"Admin health check error: {e}")
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "unhealthy",
                        "error": str(e),
                        "service": "weather-flick-admin"
                    }
                )
        
        return await call_next(request)