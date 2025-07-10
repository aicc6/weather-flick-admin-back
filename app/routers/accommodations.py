from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..models import Destination, Region

router = APIRouter(prefix="/accommodations", tags=["Accommodations"])


@router.get("/")
def get_all_accommodations(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """숙박시설 목록 조회 (destinations 테이블의 숙박 데이터 사용)"""
    total = db.query(Destination).filter(Destination.category == '숙박').count()
    accommodations = (
        db.query(Destination)
        .filter(Destination.category == '숙박')
        .order_by(Destination.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "content_id": str(a.destination_id),
                "name": a.name,
                "type": a.category,
                "address": None,  # destinations 테이블에는 address 없음
                "phone": a.amenities.get('tel') if a.amenities else None,
                "rating": a.rating,
                "price_range": None,  # destinations 테이블에는 price_range 없음
                "amenities": a.amenities,
                "latitude": float(a.latitude) if a.latitude else None,
                "longitude": float(a.longitude) if a.longitude else None,
                "region_code": a.province,
                "region_name": a.region,
                "image_url": a.image_url,
                "created_at": a.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for a in accommodations
        ],
    }


@router.get("/{content_id}")
def get_accommodation(content_id: str, db: Session = Depends(get_db)):
    """숙박시설 상세 조회"""
    accommodation = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(Destination.category == '숙박')
        .first()
    )
    if not accommodation:
        raise HTTPException(status_code=404, detail="숙박시설을 찾을 수 없습니다.")
    return {
        "content_id": str(accommodation.destination_id),
        "name": accommodation.name,
        "type": accommodation.category,
        "address": None,  # destinations 테이블에는 address 없음
        "phone": accommodation.amenities.get('tel') if accommodation.amenities else None,
        "rating": accommodation.rating,
        "price_range": None,  # destinations 테이블에는 price_range 없음
        "amenities": accommodation.amenities,
        "latitude": float(accommodation.latitude) if accommodation.latitude else None,
        "longitude": float(accommodation.longitude) if accommodation.longitude else None,
        "region_code": accommodation.province,
        "region_name": accommodation.region,
        "image_url": accommodation.image_url,
        "created_at": accommodation.created_at,
        "updated_at": None,  # destinations 테이블에는 updated_at 없음
    }


@router.get("/search/")
def search_accommodations(
    name: str = Query(None, description="숙박시설명"),
    region: str = Query(None, description="지역코드"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """숙박시설 검색"""
    query = db.query(Destination).filter(Destination.category == '숙박')
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
                "content_id": str(a.destination_id),
                "name": a.name,
                "type": a.category,
                "address": None,  # destinations 테이블에는 address 없음
                "phone": a.amenities.get('tel') if a.amenities else None,
                "rating": a.rating,
                "price_range": None,  # destinations 테이블에는 price_range 없음
                "amenities": a.amenities,
                "latitude": float(a.latitude) if a.latitude else None,
                "longitude": float(a.longitude) if a.longitude else None,
                "region_code": a.province,
                "region_name": a.region,
                "image_url": a.image_url,
                "created_at": a.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for a in results
        ],
    }


@router.post("/", status_code=201)
def create_accommodation(
    name: str = Body(...),
    province: str = Body(...),
    region: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body({}),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    """숙박시설 등록 (destinations 테이블에 숙박 카테고리로 추가)"""
    new_accommodation = Destination(
        destination_id=uuid4(),
        name=name,
        province=province,
        region=region,
        category='숙박',
        is_indoor=True,  # 숙박시설은 일반적으로 실내
        tags=['숙박', '호텔', '펜션'],
        latitude=latitude,
        longitude=longitude,
        amenities=amenities,
        image_url=image_url,
    )
    db.add(new_accommodation)
    db.commit()
    db.refresh(new_accommodation)
    return {"content_id": str(new_accommodation.destination_id)}


@router.put("/{content_id}")
def update_accommodation(
    content_id: str,
    name: str = Body(None),
    province: str = Body(None),
    region: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body(None),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    """숙박시설 정보 수정"""
    accommodation = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(Destination.category == '숙박')
        .first()
    )
    if not accommodation:
        raise HTTPException(status_code=404, detail="숙박시설을 찾을 수 없습니다.")
    if name is not None:
        accommodation.name = name
    if province is not None:
        accommodation.province = province
    if region is not None:
        accommodation.region = region
    if latitude is not None:
        accommodation.latitude = latitude
    if longitude is not None:
        accommodation.longitude = longitude
    if amenities is not None:
        accommodation.amenities = amenities
    if image_url is not None:
        accommodation.image_url = image_url
    db.commit()
    db.refresh(accommodation)
    return {"content_id": str(accommodation.destination_id)}


@router.delete("/{content_id}", status_code=204)
def delete_accommodation(content_id: str, db: Session = Depends(get_db)):
    """숙박시설 삭제"""
    accommodation = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(Destination.category == '숙박')
        .first()
    )
    if not accommodation:
        raise HTTPException(status_code=404, detail="숙박시설을 찾을 수 없습니다.")
    db.delete(accommodation)
    db.commit()
    return None