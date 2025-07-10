from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..models import Destination, Region

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


@router.get("/")
def get_all_restaurants(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """음식점 목록 조회 (destinations 테이블의 음식점 데이터 사용)"""
    total = db.query(Destination).filter(Destination.category == '음식점').count()
    restaurants = (
        db.query(Destination)
        .filter(Destination.category == '음식점')
        .order_by(Destination.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "content_id": str(r.destination_id),
                "restaurant_name": r.name,
                "region_code": r.province,
                "cuisine_type": r.category,
                "address": None,  # destinations 테이블에는 address 없음
                "tel": r.amenities.get('tel') if r.amenities else None,
                "homepage": r.amenities.get('homepage') if r.amenities else None,
                "operating_hours": None,  # destinations 테이블에는 operating_hours 없음
                "specialty_dish": None,  # destinations 테이블에는 specialty_dish 없음
                "latitude": float(r.latitude) if r.latitude else None,
                "longitude": float(r.longitude) if r.longitude else None,
                "region_name": r.region,
                "image_url": r.image_url,
                "rating": r.rating,
                "amenities": r.amenities,
                "tags": r.tags,
                "created_at": r.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for r in restaurants
        ],
    }


@router.get("/{content_id}")
def get_restaurant(content_id: str, db: Session = Depends(get_db)):
    """음식점 상세 조회"""
    restaurant = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(Destination.category == '음식점')
        .first()
    )
    if not restaurant:
        raise HTTPException(status_code=404, detail="음식점을 찾을 수 없습니다.")
    return {
        "content_id": str(restaurant.destination_id),
        "restaurant_name": restaurant.name,
        "region_code": restaurant.province,
        "cuisine_type": restaurant.category,
        "address": None,  # destinations 테이블에는 address 없음
        "tel": restaurant.amenities.get('tel') if restaurant.amenities else None,
        "homepage": restaurant.amenities.get('homepage') if restaurant.amenities else None,
        "operating_hours": None,  # destinations 테이블에는 operating_hours 없음
        "specialty_dish": None,  # destinations 테이블에는 specialty_dish 없음
        "latitude": float(restaurant.latitude) if restaurant.latitude else None,
        "longitude": float(restaurant.longitude) if restaurant.longitude else None,
        "region_name": restaurant.region,
        "image_url": restaurant.image_url,
        "rating": restaurant.rating,
        "amenities": restaurant.amenities,
        "tags": restaurant.tags,
        "created_at": restaurant.created_at,
        "updated_at": None,  # destinations 테이블에는 updated_at 없음
    }


@router.get("/search/")
def search_restaurants(
    name: str = Query(None, description="음식점명"),
    region: str = Query(None, description="지역코드"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """음식점 검색"""
    query = db.query(Destination).filter(Destination.category == '음식점')
    if name:
        query = query.filter(Destination.name.ilike(f"%{name}%"))
    if region:
        query = query.filter(Destination.province == region)
    total = query.count()
    results = (
        query.order_by(Destination.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "content_id": str(r.destination_id),
                "restaurant_name": r.name,
                "region_code": r.province,
                "cuisine_type": r.category,
                "address": None,  # destinations 테이블에는 address 없음
                "tel": r.amenities.get('tel') if r.amenities else None,
                "homepage": r.amenities.get('homepage') if r.amenities else None,
                "operating_hours": None,  # destinations 테이블에는 operating_hours 없음
                "specialty_dish": None,  # destinations 테이블에는 specialty_dish 없음
                "latitude": float(r.latitude) if r.latitude else None,
                "longitude": float(r.longitude) if r.longitude else None,
                "region_name": r.region,
                "image_url": r.image_url,
                "rating": r.rating,
                "amenities": r.amenities,
                "tags": r.tags,
                "created_at": r.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for r in results
        ],
    }


@router.post("/", status_code=201)
def create_restaurant(
    restaurant_name: str = Body(...),
    province: str = Body(...),
    region: str = Body(None),
    tel: str = Body(None),
    homepage: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body({}),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    """음식점 등록 (destinations 테이블에 음식점 카테고리로 추가)"""
    # amenities에 연락처 정보 추가
    restaurant_amenities = amenities.copy()
    if tel:
        restaurant_amenities['tel'] = tel
    if homepage:
        restaurant_amenities['homepage'] = homepage
    
    new_restaurant = Destination(
        destination_id=uuid4(),
        name=restaurant_name,
        province=province,
        region=region,
        category='음식점',
        is_indoor=True,  # 음식점은 일반적으로 실내
        tags=['음식점', '맛집', '레스토랑'],
        latitude=latitude,
        longitude=longitude,
        amenities=restaurant_amenities,
        image_url=image_url,
    )
    db.add(new_restaurant)
    db.commit()
    db.refresh(new_restaurant)
    return {"content_id": str(new_restaurant.destination_id)}


@router.put("/{content_id}")
def update_restaurant(
    content_id: str,
    restaurant_name: str = Body(None),
    province: str = Body(None),
    region: str = Body(None),
    tel: str = Body(None),
    homepage: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body(None),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    """음식점 정보 수정"""
    restaurant = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(Destination.category == '음식점')
        .first()
    )
    if not restaurant:
        raise HTTPException(status_code=404, detail="음식점을 찾을 수 없습니다.")
    
    if restaurant_name is not None:
        restaurant.name = restaurant_name
    if province is not None:
        restaurant.province = province
    if region is not None:
        restaurant.region = region
    if latitude is not None:
        restaurant.latitude = latitude
    if longitude is not None:
        restaurant.longitude = longitude
    if image_url is not None:
        restaurant.image_url = image_url
    
    # amenities 업데이트
    if amenities is not None or tel is not None or homepage is not None:
        current_amenities = restaurant.amenities or {}
        if amenities is not None:
            current_amenities.update(amenities)
        if tel is not None:
            current_amenities['tel'] = tel
        if homepage is not None:
            current_amenities['homepage'] = homepage
        restaurant.amenities = current_amenities
    
    db.commit()
    db.refresh(restaurant)
    return {"content_id": str(restaurant.destination_id)}


@router.delete("/{content_id}", status_code=204)
def delete_restaurant(content_id: str, db: Session = Depends(get_db)):
    """음식점 삭제"""
    restaurant = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(Destination.category == '음식점')
        .first()
    )
    if not restaurant:
        raise HTTPException(status_code=404, detail="음식점을 찾을 수 없습니다.")
    db.delete(restaurant)
    db.commit()
    return None