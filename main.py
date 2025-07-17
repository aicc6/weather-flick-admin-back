import logging

from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.logging_config import setup_logging
from app.database import get_db
from sqlalchemy.orm import Session
from app.routers import festivals_events, travel_plans
from app.routers.admins import router as admins_router

# 통합된 라우터들 사용
from app.routers.auth import router as auth_router
from app.routers.batch import router as batch_router
from app.routers.dashboard import router as dashboard_router
from app.routers.destinations import router as destinations_router
from app.routers.logs import router as logs_router
from app.routers.regions import router as regions_router
from app.routers.system import router as system_router
from app.routers.travel_courses import router as travel_courses_router
from app.routers.users import router as users_router
from app.routers.weather import router as weather_router
from app.routers.rbac import router as rbac_router
from app.routers.contact import router as contact_router
from app.routers.admin_categories import router as admin_categories_router
from app.routers.leisure_sports_compatibility import router as leisure_sports_compatibility_router
from app.routers.travel_courses_compatibility import router as travel_courses_compatibility_router
from app.routers.accommodations import router as accommodations_router
from app.routers.restaurants import router as restaurants_router
from app.middleware.rbac_middleware import RBACMiddleware

# 로깅 설정 초기화
setup_logging(log_dir="logs", log_level="DEBUG" if settings.debug else "INFO")

app = FastAPI(
    title="Weather Flick Admin API",
    description="Weather Flick Admin Backend API",
    version="1.0.0"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RBAC 미들웨어 추가
app.add_middleware(RBACMiddleware)

# 요청 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start_time = time.time()

    # 요청 로깅
    logging.info(f"[REQUEST] {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # 응답 로깅
        logging.info(
            f"[RESPONSE] {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Time: {process_time:.3f}s"
        )

        return response
    except Exception as e:
        process_time = time.time() - start_time
        logging.error(
            f"[ERROR] {request.method} {request.url.path} - "
            f"Error: {str(e)} - Time: {process_time:.3f}s"
        )
        raise

# 라우터 등록 (API prefix 통일) - Cursor 규칙에 따른 통합 구조
app.include_router(auth_router, prefix="/api")
app.include_router(admins_router, prefix="/api")
app.include_router(weather_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(destinations_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")  # 새로 추가된 대시보드 API
app.include_router(logs_router, prefix="/api")  # 새로 추가된 로그 관리 API
app.include_router(travel_courses_router, prefix="/api")
app.include_router(festivals_events.router, prefix="/api")
app.include_router(travel_plans.router, prefix="/api")
app.include_router(batch_router, prefix="/api")  # 배치 작업 API 추가
app.include_router(regions_router, prefix="/api")  # 지역 관리 API 추가
app.include_router(rbac_router, prefix="/api")  # RBAC 관리 API 추가
app.include_router(contact_router, prefix="/api")  # 문의사항 API 추가
app.include_router(admin_categories_router, prefix="/api")  # 카테고리 관리 API 추가
app.include_router(leisure_sports_compatibility_router, prefix="/api")  # 레저 스포츠 호환성 API 추가
app.include_router(travel_courses_compatibility_router, prefix="/api")  # 여행 코스 호환성 API 추가
app.include_router(accommodations_router, prefix="/api")  # 숙박시설 API 추가
app.include_router(restaurants_router, prefix="/api")  # 음식점 API 추가


@app.get("/")
async def root():
    return {"message": "Weather Flick Admin API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.app_version}

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    logging.info(f"🚀 {settings.app_name} v{settings.app_version} 시작")
    logging.info(f"환경: {settings.environment}")
    logging.info(f"디버그 모드: {settings.debug}")
    logging.info(f"서버 주소: http://{settings.host}:{settings.port}")

    # 개발 환경에서만 자동으로 테이블 생성 및 초기 데이터 설정
    if settings.debug:
        try:
            from app.init_data import init_database
            logging.info("데이터베이스 초기화 시작...")
            init_database()
            logging.info("데이터베이스 초기화 완료")
        except Exception as e:
            logging.error(f"⚠️  초기화 중 오류 발생: {e}", exc_info=True)


# 전역 에러 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"[GlobalError] {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류"})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.error(f"[ValidationError] {request.url}: {exc}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
