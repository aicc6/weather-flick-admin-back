from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..models import Destination, Region

router = APIRouter(prefix="/festivals-events", tags=["Festivals & Events"])


@router.get("/")
def get_all_festivals_events(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """축제/행사 목록 조회 (destinations 테이블의 축제/행사 데이터 사용)"""
    total = db.query(Destination).filter(Destination.category == '축제/행사').count()
    festivals_events = (
        db.query(Destination)
        .filter(Destination.category == '축제/행사')
        .order_by(Destination.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "content_id": str(fe.destination_id),
                "event_name": fe.name,
                "region_code": fe.province,
                "event_place": fe.region,
                "address": None,  # destinations 테이블에는 address 없음
                "tel": fe.amenities.get('tel') if fe.amenities else None,
                "homepage": fe.amenities.get('homepage') if fe.amenities else None,
                "event_start_date": None,  # destinations 테이블에는 날짜 정보 없음
                "event_end_date": None,
                "event_program": None,  # destinations 테이블에는 프로그램 정보 없음
                "latitude": float(fe.latitude) if fe.latitude else None,
                "longitude": float(fe.longitude) if fe.longitude else None,
                "region_name": fe.region,
                "image_url": fe.image_url,
                "rating": fe.rating,
                "amenities": fe.amenities,
                "tags": fe.tags,
                "created_at": fe.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for fe in festivals_events
        ],
    }


@router.get("/{content_id}")
def get_festival_event(content_id: str, db: Session = Depends(get_db)):
    """축제/행사 상세 조회"""
    festival_event = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(Destination.category == '축제/행사')
        .first()
    )
    if not festival_event:
        raise HTTPException(status_code=404, detail="축제/행사를 찾을 수 없습니다.")
    return {
        "content_id": str(festival_event.destination_id),
        "event_name": festival_event.name,
        "region_code": festival_event.province,
        "event_place": festival_event.region,
        "address": None,  # destinations 테이블에는 address 없음
        "tel": festival_event.amenities.get('tel') if festival_event.amenities else None,
        "homepage": festival_event.amenities.get('homepage') if festival_event.amenities else None,
        "event_start_date": None,  # destinations 테이블에는 날짜 정보 없음
        "event_end_date": None,
        "event_program": None,  # destinations 테이블에는 프로그램 정보 없음
        "latitude": float(festival_event.latitude) if festival_event.latitude else None,
        "longitude": float(festival_event.longitude) if festival_event.longitude else None,
        "region_name": festival_event.region,
        "image_url": festival_event.image_url,
        "rating": festival_event.rating,
        "amenities": festival_event.amenities,
        "tags": festival_event.tags,
        "created_at": festival_event.created_at,
        "updated_at": None,  # destinations 테이블에는 updated_at 없음
    }


@router.get("/search/")
def search_festivals_events(
    name: str = Query(None, description="축제/행사명"),
    region: str = Query(None, description="지역코드"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """축제/행사 검색"""
    query = db.query(Destination).filter(Destination.category == '축제/행사')
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
                "content_id": str(fe.destination_id),
                "event_name": fe.name,
                "region_code": fe.province,
                "event_place": fe.region,
                "address": None,  # destinations 테이블에는 address 없음
                "tel": fe.amenities.get('tel') if fe.amenities else None,
                "homepage": fe.amenities.get('homepage') if fe.amenities else None,
                "event_start_date": None,  # destinations 테이블에는 날짜 정보 없음
                "event_end_date": None,
                "event_program": None,  # destinations 테이블에는 프로그램 정보 없음
                "latitude": float(fe.latitude) if fe.latitude else None,
                "longitude": float(fe.longitude) if fe.longitude else None,
                "region_name": fe.region,
                "image_url": fe.image_url,
                "rating": fe.rating,
                "amenities": fe.amenities,
                "tags": fe.tags,
                "created_at": fe.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for fe in results
        ],
    }


@router.post("/", status_code=201)
def create_festival_event(
    event_name: str = Body(...),
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
    """축제/행사 등록 (destinations 테이블에 축제/행사 카테고리로 추가)"""
    # amenities에 연락처 정보 추가
    event_amenities = amenities.copy()
    if tel:
        event_amenities['tel'] = tel
    if homepage:
        event_amenities['homepage'] = homepage
    
    new_festival_event = Destination(
        destination_id=uuid4(),
        name=event_name,
        province=province,
        region=region,
        category='축제/행사',
        is_indoor=False,  # 축제/행사는 일반적으로 야외
        tags=['축제', '행사', '이벤트', '문화'],
        latitude=latitude,
        longitude=longitude,
        amenities=event_amenities,
        image_url=image_url,
    )
    db.add(new_festival_event)
    db.commit()
    db.refresh(new_festival_event)
    return {"content_id": str(new_festival_event.destination_id)}


@router.put("/{content_id}")
def update_festival_event(
    content_id: str,
    event_name: str = Body(None),
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
    """축제/행사 정보 수정"""
    festival_event = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(Destination.category == '축제/행사')
        .first()
    )
    if not festival_event:
        raise HTTPException(status_code=404, detail="축제/행사를 찾을 수 없습니다.")
    
    if event_name is not None:
        festival_event.name = event_name
    if province is not None:
        festival_event.province = province
    if region is not None:
        festival_event.region = region
    if latitude is not None:
        festival_event.latitude = latitude
    if longitude is not None:
        festival_event.longitude = longitude
    if image_url is not None:
        festival_event.image_url = image_url
    
    # amenities 업데이트
    if amenities is not None or tel is not None or homepage is not None:
        current_amenities = festival_event.amenities or {}
        if amenities is not None:
            current_amenities.update(amenities)
        if tel is not None:
            current_amenities['tel'] = tel
        if homepage is not None:
            current_amenities['homepage'] = homepage
        festival_event.amenities = current_amenities
    
    db.commit()
    db.refresh(festival_event)
    return {"content_id": str(festival_event.destination_id)}


@router.delete("/{content_id}", status_code=204)
def delete_festival_event(content_id: str, db: Session = Depends(get_db)):
    """축제/행사 삭제"""
    festival_event = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(Destination.category == '축제/행사')
        .first()
    )
    if not festival_event:
        raise HTTPException(status_code=404, detail="축제/행사를 찾을 수 없습니다.")
    db.delete(festival_event)
    db.commit()
    return None