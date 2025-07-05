from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth.router import router as auth_router
from app.admins.router import router as admins_router
from app.weather.router import router as weather_router
from app.users.router import router as users_router
from app.tourist_attractions.router import router as tourist_attractions_router
from app.config import settings
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

# 라우터 등록 (API prefix 통일)
app.include_router(auth_router, prefix="/api")
app.include_router(admins_router, prefix="/api")
app.include_router(weather_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(tourist_attractions_router, prefix="/api")
app.include_router(system_router, prefix="/api")

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


# 전역 에러 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"[GlobalError] {request.url}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류"})

@app.exception_handler(FastAPIRequestValidationError)
async def validation_exception_handler(request: Request, exc: FastAPIRequestValidationError):
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
