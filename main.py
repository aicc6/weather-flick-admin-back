import logging
import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError as FastAPIRequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers.admins import router as admins_router

# 통합된 라우터들 사용
from app.routers.auth import router as auth_router
from app.routers.dashboard import router as dashboard_router
from app.routers.data_quality import router as data_quality_router
from app.routers.destinations import router as destinations_router
from app.routers.duplicates import router as duplicates_router
from app.routers.logs import router as logs_router
from app.routers.system import router as system_router
from app.routers.users import router as users_router
from app.routers.weather import router as weather_router
from app.routers.travel_courses import router as travel_courses_router
from app.routers import festivals_events
from app.routers import leisure_sports
from app.routers import travel_plans

# AI 관련 라우터들
from app.routers import ai_behavior
from app.routers import ai_ml_models
from app.routers import ai_notifications
from app.routers import ai_predictive
from app.routers import ai_recommendations
from app.routers import ai_trends

# 보안 미들웨어 임포트
from app.middleware import (
    setup_cors,
    create_rate_limiter,
    InputValidationMiddleware,
    SecurityHeadersMiddleware,
    RequestIdMiddleware,
    create_security_headers_config,
    SecurityConfig
)

app = FastAPI(
    title="Weather Flick Admin API",
    description="Weather Flick Admin Backend API",
    version="1.0.0",
)

# 환경 설정
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
REDIS_URL = os.getenv("REDIS_URL", None)

# 1. Request ID 미들웨어 (가장 먼저 실행)
app.add_middleware(RequestIdMiddleware)

# 2. 보안 헤더 미들웨어
security_headers_config = create_security_headers_config(ENVIRONMENT)
app.add_middleware(SecurityHeadersMiddleware, **security_headers_config)

# 3. Rate Limiting 미들웨어 (Redis 없이 메모리 기반으로)
rate_limiter = create_rate_limiter(
    redis_url=None,  # Redis 사용하지 않음
    default_limit=100,
    default_window=60
)
app.add_middleware(rate_limiter)

# 4. 입력 검증 미들웨어 (임시 비활성화)
# input_validation_config = SecurityConfig(
#     max_request_size=10 * 1024 * 1024,  # 10MB
#     check_sql_injection=True,
#     check_xss=True,
#     check_path_traversal=True
# )
# app.add_middleware(InputValidationMiddleware, config=input_validation_config)

# 5. CORS 설정 (보안 강화된 설정)
setup_cors(app, environment=ENVIRONMENT)

# 라우터 등록 (API prefix 통일) - Cursor 규칙에 따른 통합 구조
app.include_router(auth_router, prefix="/api")
app.include_router(admins_router, prefix="/api")
app.include_router(weather_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(destinations_router, prefix="/api")
app.include_router(duplicates_router, prefix="/api")  # 중복 관리 API
app.include_router(data_quality_router, prefix="/api")  # 데이터 품질 관리 API
app.include_router(system_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")  # 새로 추가된 대시보드 API
app.include_router(logs_router, prefix="/api")  # 새로 추가된 로그 관리 API
app.include_router(travel_courses_router)
app.include_router(festivals_events.router, prefix="/api")
app.include_router(leisure_sports.router)
app.include_router(travel_plans.router, prefix="/api")

# AI 라우터 등록 (관리자 전용)
app.include_router(ai_behavior.router, prefix="/api")
app.include_router(ai_ml_models.router, prefix="/api")
app.include_router(ai_notifications.router, prefix="/api")
app.include_router(ai_predictive.router, prefix="/api")
app.include_router(ai_recommendations.router, prefix="/api")
app.include_router(ai_trends.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Weather Flick Admin API is running!"}


@app.get("/health")
async def health_check():
    """확장된 헬스체크 - v3 DB 연결 및 필수 모델 검증"""
    try:
        from app.database import SessionLocal
        from app.models import Admin

        with SessionLocal() as session:
            # DB 연결 테스트
            admin_count = session.query(Admin).count()

            return {
                "status": "healthy",
                "version": settings.app_version,
                "database": "connected",
                "v3_schema": "active",
                "admin_accounts": admin_count,
            }
    except Exception as e:
        return {"status": "unhealthy", "version": settings.app_version, "error": str(e)}


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    print(f"🚀 {settings.app_name} v{settings.app_version} 시작")
    print("ℹ️  관리자 계정 생성이 필요한 경우:")
    print("   python scripts/create_admin.py")


# 전역 에러 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"[GlobalError] {request.url}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류"})


@app.exception_handler(FastAPIRequestValidationError)
async def validation_exception_handler(
    request: Request, exc: FastAPIRequestValidationError
):
    logging.error(f"[ValidationError] {request.url}: {exc}")
    return JSONResponse(status_code=422, content={"detail": str(exc)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app", host=settings.host, port=settings.port, reload=settings.debug
    )