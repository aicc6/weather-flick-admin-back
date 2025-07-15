from fastapi import FastAPI

from app.routers import leisure_sports, travel_plans

# FastAPI 앱 인스턴스 생성
app = FastAPI(
    title="Weather Flick Admin API",
    description="관리자용 Weather Flick API",
    version="1.0.0"
)

# 라우터 등록
app.include_router(leisure_sports.router)
app.include_router(travel_plans.router)
