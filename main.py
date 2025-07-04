from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth.router import router as auth_router
from app.weather.router import router as weather_router
from app.users.router import router as users_router
from app.config import settings
from tourlist.tourist_attractions import router as tourist_attractions_router
import psutil
import time
from sqlalchemy import text
from app.database import engine
import requests
from collections import deque
import logging
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import RequestValidationError
from fastapi.exceptions import RequestValidationError as FastAPIRequestValidationError
from app.routers.system import router as system_router

app = FastAPI(
    title="Weather Flick Admin API",
    description="Weather Flick Admin Backend API",
    version="1.0.0"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(weather_router)
app.include_router(users_router)
app.include_router(tourist_attractions_router)
app.include_router(system_router)

# 서버 시작 시간 기록
start_time = time.time()

# 최근 에러 기록 (메모리, 최대 1000개)
ERROR_LOG = deque(maxlen=1000)

# 외부 API 헬스체크 함수
def check_api_health(url, headers=None):
    try:
        resp = requests.head(url, timeout=3, headers=headers)
        if resp.status_code < 400:
            return '정상'
        return f'오류({resp.status_code})'
    except Exception as e:
        return '점검중'

@app.get("/")
async def root():
    return {"message": "Weather Flick Admin API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.app_version}

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    print(f"🚀 {settings.app_name} v{settings.app_version} 시작")

    # 개발 환경에서만 자동으로 테이블 생성 및 초기 데이터 설정
    if settings.debug:
        try:
            from app.init_data import init_database
            init_database()
        except Exception as e:
            print(f"⚠️  초기화 중 오류 발생: {e}")

# 시스템 리소스 상태 API (실제 데이터)
@app.get("/api/v1/admin/system/status")
async def get_system_status():
    # 서버 리소스
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent

    # DB 상태
    db_status = "연결됨"
    db_response = "-"
    try:
        t0 = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_response = f"{(time.time() - t0) * 1000:.0f}ms"
    except Exception as e:
        db_status = "끊김"
        db_response = "-"
        ERROR_LOG.append(time.time())

    # 서버 상태/업타임
    uptime_seconds = time.time() - start_time
    uptime_hours = uptime_seconds // 3600
    uptime_str = f"{int(uptime_hours)}시간 {int((uptime_seconds%3600)//60)}분"
    server_status = "정상"

    # API 성능 (샘플: DB 응답시간 사용)
    avg_response = db_response if db_response != '-' else "-"

    # 외부 API 상태
    external = {
        "weather": check_api_health(settings.weather_api_url),
        "tour": check_api_health(settings.korea_tourism_api_url),
        "map": check_api_health(settings.google_places_url),
        "payment": check_api_health("https://api.iamport.kr/")
    }

    # 에러율 (최근 24시간 내 에러 비율, 샘플: 전체 요청수 대신 10000으로 가정)
    now = time.time()
    error_24h = [t for t in ERROR_LOG if now - t < 86400]
    error_rate = f"{len(error_24h)/10000*100:.2f}%" if error_24h else "0.00%"

    return {
        "server": {"status": server_status, "uptime": uptime_str},
        "db": {"status": db_status, "response": db_response},
        "api": {"avgResponse": avg_response},
        "error": {"rate": error_rate},
        "resource": {"cpu": cpu, "memory": memory, "disk": disk},
        "external": external,
    }

# 전역 에러 핸들러에서 ERROR_LOG에 기록 (예시)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    ERROR_LOG.append(time.time())
    logging.error(f"[GlobalError] {request.url}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류"})

@app.exception_handler(FastAPIRequestValidationError)
async def validation_exception_handler(request: Request, exc: FastAPIRequestValidationError):
    ERROR_LOG.append(time.time())
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
