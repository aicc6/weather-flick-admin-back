from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..models import Destination, Region

router = APIRouter(prefix="/cultural-facilities", tags=["Cultural Facilities"])


@router.get("/")
def get_all_cultural_facilities(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """문화시설 목록 조회 (destinations 테이블의 문화시설 데이터 사용)"""
    total = db.query(Destination).filter(Destination.category == '문화시설').count()
    cultural_facilities = (
        db.query(Destination)
        .filter(Destination.category == '문화시설')
        .order_by(Destination.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "content_id": str(cf.destination_id),
                "facility_name": cf.name,
                "region_code": cf.province,
                "facility_type": cf.category,
                "address": None,  # destinations 테이블에는 address 없음
                "tel": cf.amenities.get('tel') if cf.amenities else None,
                "homepage": cf.amenities.get('homepage') if cf.amenities else None,
                "operating_hours": None,  # destinations 테이블에는 operating_hours 없음
                "admission_fee": None,  # destinations 테이블에는 admission_fee 없음
                "parking_info": None,  # destinations 테이블에는 parking_info 없음
                "latitude": float(cf.latitude) if cf.latitude else None,
                "longitude": float(cf.longitude) if cf.longitude else None,
                "region_name": cf.region,
                "image_url": cf.image_url,
                "rating": cf.rating,
                "amenities": cf.amenities,
                "tags": cf.tags,
                "created_at": cf.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for cf in cultural_facilities
        ],
    }


@router.get("/{content_id}")
def get_cultural_facility(content_id: str, db: Session = Depends(get_db)):
    """문화시설 상세 조회"""
    cultural_facility = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(Destination.category == '문화시설')
        .first()
    )
    if not cultural_facility:
        raise HTTPException(status_code=404, detail="문화시설을 찾을 수 없습니다.")
    return {
        "content_id": str(cultural_facility.destination_id),
        "facility_name": cultural_facility.name,
        "region_code": cultural_facility.province,
        "facility_type": cultural_facility.category,
        "address": None,  # destinations 테이블에는 address 없음
        "tel": cultural_facility.amenities.get('tel') if cultural_facility.amenities else None,
        "homepage": cultural_facility.amenities.get('homepage') if cultural_facility.amenities else None,
        "operating_hours": None,  # destinations 테이블에는 operating_hours 없음
        "admission_fee": None,  # destinations 테이블에는 admission_fee 없음
        "parking_info": None,  # destinations 테이블에는 parking_info 없음
        "latitude": float(cultural_facility.latitude) if cultural_facility.latitude else None,
        "longitude": float(cultural_facility.longitude) if cultural_facility.longitude else None,
        "region_name": cultural_facility.region,
        "image_url": cultural_facility.image_url,
        "rating": cultural_facility.rating,
        "amenities": cultural_facility.amenities,
        "tags": cultural_facility.tags,
        "created_at": cultural_facility.created_at,
        "updated_at": None,  # destinations 테이블에는 updated_at 없음
    }


@router.get("/search/")
def search_cultural_facilities(
    name: str = Query(None, description="문화시설명"),
    region: str = Query(None, description="지역코드"),
    facility_type: str = Query(None, description="시설유형"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """문화시설 검색"""
    query = db.query(Destination).filter(Destination.category == '문화시설')
    if name:
        query = query.filter(Destination.name.ilike(f"%{name}%"))
    if region:
        query = query.filter(Destination.province == region)
    if facility_type:
        # facility_type으로 검색 시 태그나 이름을 통해 필터링
        query = query.filter(
            or_(
                Destination.name.ilike(f"%{facility_type}%"),
                Destination.tags.contains([facility_type])
            )
        )
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
                "content_id": str(cf.destination_id),
                "facility_name": cf.name,
                "region_code": cf.province,
                "facility_type": cf.category,
                "address": None,  # destinations 테이블에는 address 없음
                "tel": cf.amenities.get('tel') if cf.amenities else None,
                "homepage": cf.amenities.get('homepage') if cf.amenities else None,
                "operating_hours": None,  # destinations 테이블에는 operating_hours 없음
                "admission_fee": None,  # destinations 테이블에는 admission_fee 없음
                "parking_info": None,  # destinations 테이블에는 parking_info 없음
                "latitude": float(cf.latitude) if cf.latitude else None,
                "longitude": float(cf.longitude) if cf.longitude else None,
                "region_name": cf.region,
                "image_url": cf.image_url,
                "rating": cf.rating,
                "amenities": cf.amenities,
                "tags": cf.tags,
                "created_at": cf.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for cf in results
        ],
    }


@router.post("/", status_code=201)
def create_cultural_facility(
    facility_name: str = Body(...),
    province: str = Body(...),
    region: str = Body(None),
    facility_type: str = Body(None),
    tel: str = Body(None),
    homepage: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body({}),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    """문화시설 등록 (destinations 테이블에 문화시설 카테고리로 추가)"""
    # amenities에 연락처 정보 추가
    facility_amenities = amenities.copy()
    if tel:
        facility_amenities['tel'] = tel
    if homepage:
        facility_amenities['homepage'] = homepage
    
    new_cultural_facility = Destination(
        destination_id=uuid4(),
        name=facility_name,
        province=province,
        region=region,
        category='문화시설',
        is_indoor=True,  # 문화시설은 일반적으로 실내
        tags=['문화', '시설', '박물관', '미술관', '도서관'],
        latitude=latitude,
        longitude=longitude,
        amenities=facility_amenities,
        image_url=image_url,
    )
    db.add(new_cultural_facility)
    db.commit()
    db.refresh(new_cultural_facility)
    return {"content_id": str(new_cultural_facility.destination_id)}


@router.put("/{content_id}")
def update_cultural_facility(
    content_id: str,
    facility_name: str = Body(None),
    province: str = Body(None),
    region: str = Body(None),
    facility_type: str = Body(None),
    tel: str = Body(None),
    homepage: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body(None),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    """문화시설 정보 수정"""
    cultural_facility = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(Destination.category == '문화시설')
        .first()
    )
    if not cultural_facility:
        raise HTTPException(status_code=404, detail="문화시설을 찾을 수 없습니다.")
    
    if facility_name is not None:
        cultural_facility.name = facility_name
    if province is not None:
        cultural_facility.province = province
    if region is not None:
        cultural_facility.region = region
    if latitude is not None:
        cultural_facility.latitude = latitude
    if longitude is not None:
        cultural_facility.longitude = longitude
    if image_url is not None:
        cultural_facility.image_url = image_url
    
    # amenities 업데이트
    if amenities is not None or tel is not None or homepage is not None:
        current_amenities = cultural_facility.amenities or {}
        if amenities is not None:
            current_amenities.update(amenities)
        if tel is not None:
            current_amenities['tel'] = tel
        if homepage is not None:
            current_amenities['homepage'] = homepage
        cultural_facility.amenities = current_amenities
    
    # 태그 업데이트 (facility_type이 제공된 경우)
    if facility_type is not None:
        current_tags = cultural_facility.tags or []
        if facility_type not in current_tags:
            current_tags.append(facility_type)
            cultural_facility.tags = current_tags
    
    db.commit()
    db.refresh(cultural_facility)
    return {"content_id": str(cultural_facility.destination_id)}


@router.delete("/{content_id}", status_code=204)
def delete_cultural_facility(content_id: str, db: Session = Depends(get_db)):
    """문화시설 삭제"""
    cultural_facility = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(Destination.category == '문화시설')
        .first()
    )
    if not cultural_facility:
        raise HTTPException(status_code=404, detail="문화시설을 찾을 수 없습니다.")
    db.delete(cultural_facility)
    db.commit()
    return None