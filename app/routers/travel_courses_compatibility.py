"""여행 코스 호환성 라우터 (레저 스포츠 지원)"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.leisure_sports_compatibility import leisure_sports_compatibility_logic

router = APIRouter(prefix="/travel-courses", tags=["travel_courses_compatibility"])


@router.get("/leisure-sports")
async def leisure_sports_compatibility_travel_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    region_code: str = Query(None),
    facility_name: str = Query(None),
    db: Session = Depends(get_db)
):
    """레저 스포츠 목록 조회 (여행 코스 경로를 통한 호환성)"""
    return await leisure_sports_compatibility_logic(skip, limit, region_code, facility_name, db)