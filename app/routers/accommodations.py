from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Accommodation, Region
from ..dependencies import CurrentAdmin, require_permission
from ..utils.category_mapping import normalize_category_data

router = APIRouter(prefix="/accommodations", tags=["Accommodations"])

@router.get("/")
@require_permission("destinations.read")
async def get_all_accommodations(
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    accommodation_name: Optional[str] = Query(None, description="숙박시설명"),
    region_code: Optional[str] = Query(None, description="지역 코드")
):
    query = db.query(Accommodation)
    
    if accommodation_name:
        query = query.filter(Accommodation.accommodation_name.ilike(f"%{accommodation_name}%"))
    
    if region_code:
        # region_code 파라미터를 받으면 해당 지역의 숙박시설 필터링
        # 프론트엔드에서 '1', '2', '3' 등을 보내면 DB의 '01', '02', '03' 형식과 매칭
        if len(region_code) == 1 and region_code.isdigit():
            # 한 자리 숫자인 경우 앞에 0을 붙여서 검색
            padded_code = region_code.zfill(2)
            # 시도 레벨과 시군구 레벨 모두 검색 (예: '01'로 시작하는 모든 region_code)
            query = query.filter(Accommodation.region_code.like(f"{padded_code}%"))
        else:
            # 그 외의 경우 그대로 검색
            query = query.filter(Accommodation.region_code == region_code)
    
    total = query.count()
    accommodations = query.order_by(Accommodation.created_at.desc()).offset(offset).limit(limit).all()
    
    # 의미있는 데이터만 포함하여 응답 구성
    items = []
    # 지역명 조회를 위한 region_codes 수집
    region_codes = list(set([item.region_code for item in accommodations if item.region_code]))
    region_names = {}
    if region_codes:
        regions = db.query(Region).filter(Region.region_code.in_(region_codes)).all()
        region_names = {r.region_code: r.region_name for r in regions}

    for a in accommodations:
        item = {
            "content_id": a.content_id,
            "accommodation_name": a.accommodation_name,
            "address": a.address,
            "region_code": a.region_code,
            "region_name": region_names.get(a.region_code, ""),
            "created_at": a.created_at,
        }
        
        # 값이 있는 필드만 추가
        if a.accommodation_type:
            item["room_type"] = a.accommodation_type
        if a.tel:
            item["tel"] = a.tel
        if a.parking:
            item["parking"] = a.parking
        if a.latitude:
            item["latitude"] = float(a.latitude)
        if a.longitude:
            item["longitude"] = float(a.longitude)
        if a.category_code:
            item["category_code"] = a.category_code
            # 카테고리 정보 정규화
            item["category_info"] = normalize_category_data(a.category_code, None)
        
        items.append(item)
    
    return {
        "total": total,
        "items": items
    }

@router.get("/{content_id}")
@require_permission("destinations.read")
async def get_accommodation(
    content_id: str,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    accommodation = db.query(Accommodation).filter(Accommodation.content_id == content_id).first()
    if not accommodation:
        raise HTTPException(status_code=404, detail="숙박시설을 찾을 수 없습니다.")
    return {
        "content_id": accommodation.content_id,
        "accommodation_name": accommodation.accommodation_name,
        "description": None,
        "address": accommodation.address,
        "image_url": None,
        "latitude": float(accommodation.latitude) if accommodation.latitude else None,
        "longitude": float(accommodation.longitude) if accommodation.longitude else None,
        "room_type": accommodation.accommodation_type,
        "check_in_time": None,
        "check_out_time": None,
        "price_range": None,
        "category_code": accommodation.category_code,
        "category_name": None,
        "region_code": accommodation.region_code,
        "tel": accommodation.tel,
        "parking": accommodation.parking,
        "created_at": accommodation.created_at,
        "updated_at": None,
    }

@router.post("/", status_code=201)
@require_permission("destinations.write")
async def create_accommodation(
    current_admin: CurrentAdmin,
    accommodation_name: str = Body(...),
    accommodation_type: str = Body(None),
    address: str = Body(None),
    tel: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    parking: str = Body(None),
    category_code: str = Body(None),
    region_code: str = Body(None),
    db: Session = Depends(get_db)
):
    new_accommodation = Accommodation(
        content_id=str(uuid4()),
        accommodation_name=accommodation_name,
        accommodation_type=accommodation_type,
        address=address,
        tel=tel,
        latitude=latitude,
        longitude=longitude,
        parking=parking,
        category_code=category_code,
        region_code=region_code,
    )
    db.add(new_accommodation)
    db.commit()
    db.refresh(new_accommodation)
    return {"content_id": new_accommodation.content_id}

@router.put("/{content_id}")
@require_permission("destinations.write")
async def update_accommodation(
    content_id: str,
    current_admin: CurrentAdmin,
    accommodation_name: str = Body(None),
    accommodation_type: str = Body(None),
    address: str = Body(None),
    tel: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    parking: str = Body(None),
    category_code: str = Body(None),
    region_code: str = Body(None),
    db: Session = Depends(get_db)
):
    accommodation = db.query(Accommodation).filter(Accommodation.content_id == content_id).first()
    if not accommodation:
        raise HTTPException(status_code=404, detail="숙박시설을 찾을 수 없습니다.")
    
    if accommodation_name is not None:
        accommodation.accommodation_name = accommodation_name
    if accommodation_type is not None:
        accommodation.accommodation_type = accommodation_type
    if address is not None:
        accommodation.address = address
    if tel is not None:
        accommodation.tel = tel
    if latitude is not None:
        accommodation.latitude = latitude
    if longitude is not None:
        accommodation.longitude = longitude
    if parking is not None:
        accommodation.parking = parking
    if category_code is not None:
        accommodation.category_code = category_code
    if region_code is not None:
        accommodation.region_code = region_code
    
    db.commit()
    db.refresh(accommodation)
    return {"content_id": accommodation.content_id}

@router.delete("/{content_id}", status_code=204)
@require_permission("destinations.delete")
async def delete_accommodation(
    content_id: str,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    accommodation = db.query(Accommodation).filter(Accommodation.content_id == content_id).first()
    if not accommodation:
        raise HTTPException(status_code=404, detail="숙박시설을 찾을 수 없습니다.")
    db.delete(accommodation)
    db.commit()
    return None