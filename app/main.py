# FastAPI 앱 및 라우터 등록

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, admins, weather, users
from .database import engine
from . import models
from .init_db import init_db

# Create database tables and initialize data
models.Base.metadata.create_all(bind=engine)
init_db()

app = FastAPI(
    title="Weather Flick Admin API",
    description="관리자 페이지를 위한 FastAPI 기반 백엔드 애플리케이션",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(admins.router, prefix="/admins", tags=["admin management"])
app.include_router(weather.router, prefix="/weather", tags=["weather data"])
app.include_router(users.router, prefix="/users", tags=["user management"])


@app.get("/")
def read_root():
    return {"message": "Weather Flick Admin API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
