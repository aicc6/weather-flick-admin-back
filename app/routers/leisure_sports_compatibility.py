"""레저 스포츠 호환성 라우터"""

import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict

from app.database import get_db
from app.models import LeisureSport, Region

router = APIRouter(prefix="/leisure-sports", tags=["leisure_sports_compatibility"])

async def leisure_sports_compatibility_logic(
    skip: int = 0,
    limit: int = 50,
    region_code: str = None,
    facility_name: str = None,
    db: Session = Depends(get_db)
):
    """레저 스포츠 호환성을 위한 공통 로직"""
    try:
        query = db.query(LeisureSport)
        if region_code:
            # region_code 파라미터를 받으면 해당 지역의 tour_api_area_code를 찾아서 필터링
            region = db.query(Region).filter(Region.region_code == region_code).first()
            if region and region.tour_api_area_code:
                query = query.filter(LeisureSport.region_code == region.tour_api_area_code)
            else:
                query = query.filter(LeisureSport.region_code == region_code)
        if facility_name:
            query = query.filter(LeisureSport.facility_name.ilike(f"%{facility_name}%"))
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        
        # 직렬화 가능한 형태로 변환
        serialized_items = []
        for item in items:
            item_dict = {
                "content_id": item.content_id,
                "facility_name": item.facility_name or "미상",
                "region_code": item.region_code,
                "address": item.address or "",
                "detail_address": item.detail_address or "",
                "tel": item.tel or "",
                "homepage": item.homepage or "",
                "overview": item.overview or "",
                "first_image": item.first_image or "",
                "first_image_small": item.first_image_small or "",
                "latitude": float(item.latitude) if item.latitude else 0.0,
                "longitude": float(item.longitude) if item.longitude else 0.0,
                "zipcode": item.zipcode or "",
                "sports_type": getattr(item, 'sports_type', None) or "",
                "category_code": getattr(item, 'category_code', None) or "",
                "operating_hours": getattr(item, 'operating_hours', None) or "",
                "reservation_info": getattr(item, 'reservation_info', None) or "",
                "admission_fee": getattr(item, 'admission_fee', None) or "",
                "parking_info": getattr(item, 'parking_info', None) or "",
                "rental_info": getattr(item, 'rental_info', None) or "",
                "capacity": getattr(item, 'capacity', None) or "",
                "created_at": item.created_at.isoformat() if item.created_at else "",
                "updated_at": item.updated_at.isoformat() if item.updated_at else "",
                "last_sync_at": getattr(item, 'last_sync_at', None) and item.last_sync_at.isoformat() if getattr(item, 'last_sync_at', None) else ""
            }
            serialized_items.append(item_dict)
        
        return {"items": serialized_items, "total": total}
    except Exception as e:
        logging.error(f"레저 스포츠 호환성 엔드포인트 오류: {e}")
        return {"items": [], "total": 0}


@router.get("/")
async def leisure_sports_compatibility_direct(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    region_code: str = Query(None),
    facility_name: str = Query(None),
    db: Session = Depends(get_db)
):
    """레저 스포츠 목록 조회 (직접 호출)"""
    return await leisure_sports_compatibility_logic(skip, limit, region_code, facility_name, db)


@router.get("/{content_id}")
async def get_leisure_sport_detail(
    content_id: str,
    db: Session = Depends(get_db)
):
    """레저 스포츠 상세 정보 조회"""
    try:
        item = db.query(LeisureSport).filter(LeisureSport.content_id == content_id).first()
        if not item:
            return {"error": "레저 스포츠 시설을 찾을 수 없습니다"}
        
        # 직렬화 가능한 형태로 변환
        item_dict = {
            "content_id": item.content_id,
            "facility_name": item.facility_name or "미상",
            "region_code": item.region_code,
            "address": item.address or "",
            "detail_address": item.detail_address or "",
            "tel": item.tel or "",
            "homepage": item.homepage or "",
            "overview": item.overview or "",
            "first_image": item.first_image or "",
            "first_image_small": item.first_image_small or "",
            "latitude": float(item.latitude) if item.latitude else 0.0,
            "longitude": float(item.longitude) if item.longitude else 0.0,
            "zipcode": item.zipcode or "",
            "sports_type": getattr(item, 'sports_type', None) or "",
            "category_code": getattr(item, 'category_code', None) or "",
            "operating_hours": getattr(item, 'operating_hours', None) or "",
            "reservation_info": getattr(item, 'reservation_info', None) or "",
            "admission_fee": getattr(item, 'admission_fee', None) or "",
            "parking_info": getattr(item, 'parking_info', None) or "",
            "rental_info": getattr(item, 'rental_info', None) or "",
            "capacity": getattr(item, 'capacity', None) or "",
            "created_at": item.created_at.isoformat() if item.created_at else "",
            "updated_at": item.updated_at.isoformat() if item.updated_at else "",
            "last_sync_at": getattr(item, 'last_sync_at', None) and item.last_sync_at.isoformat() if getattr(item, 'last_sync_at', None) else ""
        }
        
        return item_dict
    except Exception as e:
        logging.error(f"레저 스포츠 상세 조회 오류: {e}")
        return {"error": "상세 정보를 불러올 수 없습니다"}


@router.post("/")
async def create_leisure_sport(
    data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """레저 스포츠 시설 생성"""
    try:
        # content_id 생성
        import uuid
        content_id = str(uuid.uuid4())[:20]  # 20자리로 제한
        
        # 새 레저 스포츠 시설 생성
        new_item = LeisureSport(
            content_id=content_id,
            facility_name=data.get('facility_name', '미상'),
            region_code=data.get('region_code', ''),
            sports_type=data.get('sports_type', ''),
            admission_fee=data.get('admission_fee', ''),
            parking_info=data.get('parking_info', ''),
            tel=data.get('tel', ''),
            homepage=data.get('homepage', ''),
            overview=data.get('overview', ''),
            first_image=data.get('first_image', ''),
            first_image_small=data.get('first_image_small', ''),
            operating_hours=data.get('operating_hours', ''),
            reservation_info=data.get('reservation_info', ''),
            rental_info=data.get('rental_info', ''),
            capacity=data.get('capacity', ''),
            address=data.get('address', ''),
            detail_address=data.get('detail_address', ''),
            zipcode=data.get('zipcode', ''),
            latitude=data.get('latitude', 0.0),
            longitude=data.get('longitude', 0.0),
        )
        
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        # 직렬화 가능한 형태로 변환
        item_dict = {
            "content_id": new_item.content_id,
            "facility_name": new_item.facility_name or "미상",
            "region_code": new_item.region_code,
            "address": new_item.address or "",
            "detail_address": new_item.detail_address or "",
            "tel": new_item.tel or "",
            "homepage": new_item.homepage or "",
            "overview": new_item.overview or "",
            "first_image": new_item.first_image or "",
            "first_image_small": new_item.first_image_small or "",
            "latitude": float(new_item.latitude) if new_item.latitude else 0.0,
            "longitude": float(new_item.longitude) if new_item.longitude else 0.0,
            "zipcode": new_item.zipcode or "",
            "sports_type": getattr(new_item, 'sports_type', None) or "",
            "category_code": getattr(new_item, 'category_code', None) or "",
            "operating_hours": getattr(new_item, 'operating_hours', None) or "",
            "reservation_info": getattr(new_item, 'reservation_info', None) or "",
            "admission_fee": getattr(new_item, 'admission_fee', None) or "",
            "parking_info": getattr(new_item, 'parking_info', None) or "",
            "rental_info": getattr(new_item, 'rental_info', None) or "",
            "capacity": getattr(new_item, 'capacity', None) or "",
            "created_at": new_item.created_at.isoformat() if new_item.created_at else "",
            "updated_at": new_item.updated_at.isoformat() if new_item.updated_at else "",
            "last_sync_at": getattr(new_item, 'last_sync_at', None) and new_item.last_sync_at.isoformat() if getattr(new_item, 'last_sync_at', None) else ""
        }
        
        return item_dict
    except Exception as e:
        logging.error(f"레저 스포츠 생성 오류: {e}")
        raise HTTPException(status_code=500, detail="생성 중 오류가 발생했습니다")


@router.put("/{content_id}")
async def update_leisure_sport(
    content_id: str,
    data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """레저 스포츠 시설 수정"""
    try:
        item = db.query(LeisureSport).filter(LeisureSport.content_id == content_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="레저 스포츠 시설을 찾을 수 없습니다")
        
        # 업데이트 가능한 필드만 수정
        updatable_fields = {
            'facility_name', 'region_code', 'sports_type', 'admission_fee', 
            'parking_info', 'tel', 'homepage', 'overview', 'first_image',
            'first_image_small', 'operating_hours', 'reservation_info',
            'rental_info', 'capacity', 'address', 'detail_address', 'zipcode',
            'latitude', 'longitude'
        }
        
        for key, value in data.items():
            if key in updatable_fields and hasattr(item, key):
                setattr(item, key, value)
        
        db.commit()
        db.refresh(item)
        
        # 직렬화 가능한 형태로 변환
        item_dict = {
            "content_id": item.content_id,
            "facility_name": item.facility_name or "미상",
            "region_code": item.region_code,
            "address": item.address or "",
            "detail_address": item.detail_address or "",
            "tel": item.tel or "",
            "homepage": item.homepage or "",
            "overview": item.overview or "",
            "first_image": item.first_image or "",
            "first_image_small": item.first_image_small or "",
            "latitude": float(item.latitude) if item.latitude else 0.0,
            "longitude": float(item.longitude) if item.longitude else 0.0,
            "zipcode": item.zipcode or "",
            "sports_type": getattr(item, 'sports_type', None) or "",
            "category_code": getattr(item, 'category_code', None) or "",
            "operating_hours": getattr(item, 'operating_hours', None) or "",
            "reservation_info": getattr(item, 'reservation_info', None) or "",
            "admission_fee": getattr(item, 'admission_fee', None) or "",
            "parking_info": getattr(item, 'parking_info', None) or "",
            "rental_info": getattr(item, 'rental_info', None) or "",
            "capacity": getattr(item, 'capacity', None) or "",
            "created_at": item.created_at.isoformat() if item.created_at else "",
            "updated_at": item.updated_at.isoformat() if item.updated_at else "",
            "last_sync_at": getattr(item, 'last_sync_at', None) and item.last_sync_at.isoformat() if getattr(item, 'last_sync_at', None) else ""
        }
        
        return item_dict
    except Exception as e:
        logging.error(f"레저 스포츠 수정 오류: {e}")
        raise HTTPException(status_code=500, detail="수정 중 오류가 발생했습니다")


@router.delete("/{content_id}")
async def delete_leisure_sport(
    content_id: str,
    db: Session = Depends(get_db)
):
    """레저 스포츠 시설 삭제"""
    try:
        item = db.query(LeisureSport).filter(LeisureSport.content_id == content_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="레저 스포츠 시설을 찾을 수 없습니다")
        
        db.delete(item)
        db.commit()
        
        return {"message": "레저 스포츠 시설이 삭제되었습니다"}
    except Exception as e:
        logging.error(f"레저 스포츠 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail="삭제 중 오류가 발생했습니다")


@router.get("/autocomplete/")
async def autocomplete_facility_name(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """시설명 자동완성"""
    try:
        results = (
            db.query(LeisureSport.facility_name)
            .filter(LeisureSport.facility_name.ilike(f"%{q}%"))
            .filter(LeisureSport.facility_name != "미상")
            .distinct()
            .limit(10)
            .all()
        )
        return [r[0] for r in results if r[0]]
    except Exception as e:
        logging.error(f"자동완성 오류: {e}")
        return []