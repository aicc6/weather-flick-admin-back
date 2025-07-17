"""
음식점 관리 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.auth import get_current_admin
from app.database import get_db
from app.models import Restaurant
from app.schemas.restaurant_schemas import (
    RestaurantCreate,
    RestaurantListResponse,
    RestaurantResponse,
    RestaurantUpdate,
)

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


@router.get("/", response_model=RestaurantListResponse)
async def get_restaurants(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    restaurant_name: str | None = None,
    region_code: str | None = None,
    cuisine_type: str | None = None,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """음식점 목록 조회"""
    query = db.query(Restaurant)

    # 필터링
    if restaurant_name:
        query = query.filter(Restaurant.restaurant_name.ilike(f"%{restaurant_name}%"))
    if region_code and region_code != "all":
        query = query.filter(Restaurant.region_code == region_code)
    if cuisine_type:
        query = query.filter(Restaurant.cuisine_type == cuisine_type)

    # 전체 개수
    total = query.count()

    # 페이지네이션
    restaurants = (
        query.order_by(desc(Restaurant.created_at)).offset(skip).limit(limit).all()
    )

    return RestaurantListResponse(
        items=restaurants, total=total, skip=skip, limit=limit
    )


@router.get("/{content_id}", response_model=RestaurantResponse)
async def get_restaurant(
    content_id: str,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """음식점 상세 조회"""
    restaurant = (
        db.query(Restaurant).filter(Restaurant.content_id == content_id).first()
    )
    if not restaurant:
        raise HTTPException(status_code=404, detail="음식점을 찾을 수 없습니다.")
    return restaurant


@router.post("/", response_model=RestaurantResponse)
async def create_restaurant(
    restaurant: RestaurantCreate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """음식점 생성"""
    # 중복 확인
    existing = (
        db.query(Restaurant)
        .filter(
            Restaurant.restaurant_name == restaurant.restaurant_name,
            Restaurant.region_code == restaurant.region_code,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="동일한 지역에 같은 이름의 음식점이 이미 존재합니다.",
        )

    # content_id 생성 (임시로 timestamp 기반)
    import time

    content_id = f"RST{int(time.time())}"

    db_restaurant = Restaurant(content_id=content_id, **restaurant.dict())

    db.add(db_restaurant)
    db.commit()
    db.refresh(db_restaurant)

    return db_restaurant


@router.put("/{content_id}", response_model=RestaurantResponse)
async def update_restaurant(
    content_id: str,
    restaurant: RestaurantUpdate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """음식점 수정"""
    db_restaurant = (
        db.query(Restaurant).filter(Restaurant.content_id == content_id).first()
    )
    if not db_restaurant:
        raise HTTPException(status_code=404, detail="음식점을 찾을 수 없습니다.")

    # 업데이트
    update_data = restaurant.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_restaurant, field, value)

    db.commit()
    db.refresh(db_restaurant)

    return db_restaurant


@router.delete("/{content_id}")
async def delete_restaurant(
    content_id: str,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """음식점 삭제"""
    restaurant = (
        db.query(Restaurant).filter(Restaurant.content_id == content_id).first()
    )
    if not restaurant:
        raise HTTPException(status_code=404, detail="음식점을 찾을 수 없습니다.")

    db.delete(restaurant)
    db.commit()

    return {"message": "음식점이 삭제되었습니다."}


@router.get("/cuisine-types/list")
async def get_cuisine_types(
    db: Session = Depends(get_db), current_admin: dict = Depends(get_current_admin)  # noqa: ARG001
):
    """음식 종류 목록 조회"""
    # 한국관광공사 표준 음식점 카테고리
    types = [
        {"code": "A0502", "name": "음식점"},
        {"code": "A0503", "name": "카페/디저트"},
        {"code": "A0504", "name": "술집"},
        {"code": "A0505", "name": "한식"},
        {"code": "A0506", "name": "서양식"},
        {"code": "A0507", "name": "일식"},
        {"code": "A0508", "name": "중식"},
        {"code": "A0509", "name": "아시아식"},
        {"code": "A0510", "name": "패스트푸드"},
        {"code": "A0511", "name": "간식"},
        {"code": "A0512", "name": "분식"},
        {"code": "A0513", "name": "뷔페"},
        {"code": "A0514", "name": "민속주점"},
        {"code": "A0515", "name": "이색음식점"},
    ]

    return types
