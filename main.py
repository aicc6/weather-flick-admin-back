import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.logging_config import setup_logging
from app.middleware.error_handling import (
    AdminErrorHandlingMiddleware,
    AdminHealthCheckMiddleware,
    AdminTimeoutMiddleware,
)
from app.middleware.json_encoder import setup_admin_json_encoding
from app.middleware.security import (
    AdminRateLimitMiddleware,
    AdminSecurityHeadersMiddleware,
)
from app.middleware.timezone_middleware import setup_admin_timezone_middleware
from app.routers import travel_plans
from app.routers.accommodations import router as accommodations_router
from app.routers.admin_categories import router as admin_categories_router
from app.routers.admins import router as admins_router

# 통합된 라우터들 사용
from app.routers.auth import router as auth_router
from app.routers.batch import router as batch_router
from app.routers.contacts import router as contacts_router  # 간단한 문의 시스템
from app.routers.dashboard import router as dashboard_router
from app.routers.destinations import router as destinations_router
from app.routers.festivals_events import router as festivals_events_router
from app.routers.leisure_sports_compatibility import (
    router as leisure_sports_compatibility_router,
)
from app.routers.logs import router as logs_router
from app.routers.rbac import router as rbac_router
from app.routers.regions import router as regions_router
from app.routers.restaurants import router as restaurants_router
from app.routers.system import router as system_router
from app.routers.travel_courses import router as travel_courses_router
from app.routers.travel_courses_compatibility import (
    router as travel_courses_compatibility_router,
)
from app.routers.users import router as users_router
from app.routers.weather import router as weather_router

# 로깅 설정 초기화
setup_logging(log_dir="logs", log_level="DEBUG" if settings.debug else "INFO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # Startup
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

    yield

    # Shutdown
    logging.info(f"🛑 {settings.app_name} 종료")


app = FastAPI(
    title="Weather Flick Admin API",
    description="Weather Flick Admin Backend API",
    version="1.0.0",
    lifespan=lifespan,
)

# 관리자용 미들웨어 추가 (순서 중요: 외부 → 내부)
app.add_middleware(AdminErrorHandlingMiddleware)  # 최상위 에러 처리 (상세 로깅)
app.add_middleware(AdminTimeoutMiddleware, timeout_seconds=60)  # 관리자용 긴 타임아웃
app.add_middleware(AdminHealthCheckMiddleware)  # 관리자용 헬스체크
app.add_middleware(AdminSecurityHeadersMiddleware)  # 관리자용 엄격한 보안
app.add_middleware(
    AdminRateLimitMiddleware, max_requests=60, window_seconds=60
)  # 관리자용 Rate limiting

# CORS 미들웨어 설정 (관리자용 제한적 설정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "https://wf-dev.seongjunlee.dev",
        "https://wf-admin-dev.seongjunlee.dev",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# RBAC 미들웨어 추가 (임시 비활성화)
# app.add_middleware(RBACMiddleware)

# JSON 직렬화 설정 적용
setup_admin_json_encoding(app)

# 관리자용 타임존 미들웨어 추가
setup_admin_timezone_middleware(app)


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
app.include_router(travel_plans.router, prefix="/api")
app.include_router(batch_router, prefix="/api")  # 배치 작업 API 추가
app.include_router(regions_router, prefix="/api")  # 지역 관리 API 추가
app.include_router(rbac_router, prefix="/api")  # RBAC 관리 API 추가
app.include_router(contacts_router, prefix="/api")  # 문의사항 API
app.include_router(admin_categories_router, prefix="/api")  # 카테고리 관리 API 추가
app.include_router(
    leisure_sports_compatibility_router, prefix="/api"
)  # 레저 스포츠 호환성 API 추가
app.include_router(
    travel_courses_compatibility_router, prefix="/api"
)  # 여행 코스 호환성 API 추가
app.include_router(accommodations_router, prefix="/api")  # 숙박시설 API 추가
app.include_router(restaurants_router, prefix="/api")  # 음식점 API 추가
app.include_router(festivals_events_router, prefix="/api")  # 축제 이벤트 API 추가


@app.get("/")
async def root():
    return {"message": "Weather Flick Admin API is running!"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.app_version}


# 한국어 필드명 매핑
FIELD_NAME_MAPPING = {
    "email": "이메일",
    "password": "비밀번호",
    "name": "이름",
    "phone": "전화번호",
    "username": "사용자명",
    "title": "제목",
    "content": "내용",
    "status": "상태",
}

# 한국어 오류 메시지 매핑
ERROR_MESSAGE_MAPPING = {
    "missing": "을(를) 입력해주세요",
    "string_too_short": "이(가) 너무 짧습니다",
    "string_too_long": "이(가) 너무 깁니다",
    "value_error": "형식이 올바르지 않습니다",
    "type_error": "형식이 올바르지 않습니다",
}


def get_korean_field_name(field: str) -> str:
    """필드명을 한국어로 변환"""
    return FIELD_NAME_MAPPING.get(field, field)


def get_korean_validation_message(field: str, error_type: str, msg: str) -> str:
    """검증 오류를 한국어 메시지로 변환"""
    korean_field = get_korean_field_name(field)

    # 받침에 따른 조사 선택
    def get_object_particle(word: str) -> str:
        """받침에 따라 을/를 선택"""
        if not word:
            return "을"
        last_char = word[-1]
        # 한글 완성형인지 확인
        if "가" <= last_char <= "힣":
            # 받침이 있는지 확인 (유니코드 계산)
            code = ord(last_char) - ord("가")
            final_consonant = code % 28
            return "을" if final_consonant != 0 else "를"
        else:
            # 한글이 아닌 경우 기본값
            return "을"

    if error_type == "missing":
        particle = get_object_particle(korean_field)
        return f"{korean_field}{particle} 입력해주세요"
    elif error_type in ["string_too_short", "string_too_long"]:
        return f"{korean_field}{ERROR_MESSAGE_MAPPING.get(error_type, '이(가) 올바르지 않습니다')}"
    elif "email" in msg.lower():
        return f"{korean_field} 형식이 올바르지 않습니다"
    else:
        return f"{korean_field} {ERROR_MESSAGE_MAPPING.get(error_type, '형식이 올바르지 않습니다')}"


# 전역 에러 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"[GlobalError] {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류"})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.error(f"[ValidationError] {request.url}: {exc}")

    # 검증 에러를 한국어로 변환
    error_messages = []
    for error in exc.errors():
        field = error["loc"][-1] if error["loc"] else "unknown"
        error_type = error["type"]
        msg = error["msg"]

        korean_message = get_korean_validation_message(field, error_type, msg)
        error_messages.append(korean_message)

    # 중복 제거하고 결합
    unique_messages = list(dict.fromkeys(error_messages))
    combined_message = " ".join(unique_messages)

    return JSONResponse(status_code=422, content={"detail": combined_message})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app", host=settings.host, port=settings.port, reload=settings.debug
    )
