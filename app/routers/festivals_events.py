from uuid import uuid4
from typing import Optional
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FestivalEvent, Region
from ..dependencies import CurrentAdmin, require_permission
from ..utils.category_mapping import normalize_category_data

router = APIRouter(prefix="/festivals-events", tags=["Festivals Events"])

@router.get("/")
@require_permission("destinations.read")
async def get_all_festival_events(
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    event_name: Optional[str] = Query(None, description="축제명"),
    region_code: Optional[str] = Query(None, description="지역 코드")
):
    query = db.query(FestivalEvent)
    
    if event_name:
        query = query.filter(FestivalEvent.event_name.ilike(f"%{event_name}%"))
    
    if region_code:
        # region_code 파라미터를 받으면 해당 지역의 축제/행사 필터링
        # 프론트엔드에서 '1', '2', '3' 등을 보내면 DB의 '01', '02', '03' 형식과 매칭
        if len(region_code) == 1 and region_code.isdigit():
            # 한 자리 숫자인 경우 앞에 0을 붙여서 검색
            padded_code = region_code.zfill(2)
            # 시도 레벨과 시군구 레벨 모두 검색 (예: '01'로 시작하는 모든 region_code)
            query = query.filter(FestivalEvent.region_code.like(f"{padded_code}%"))
        else:
            # 그 외의 경우 그대로 검색
            query = query.filter(FestivalEvent.region_code == region_code)
    
    total = query.count()
    festivals = query.order_by(FestivalEvent.created_at.desc()).offset(skip).limit(limit).all()
    
    # 의미있는 데이터만 포함하여 응답 구성
    items = []
    # 지역명 조회를 위한 region_codes 수집
    region_codes = list(set([item.region_code for item in festivals if item.region_code]))
    region_names = {}
    if region_codes:
        regions = db.query(Region).filter(Region.region_code.in_(region_codes)).all()
        region_names = {r.region_code: r.region_name for r in regions}

    for f in festivals:
        item = {
            "content_id": f.content_id,
            "event_name": f.event_name,
            "region_code": f.region_code,
            "region_name": region_names.get(f.region_code, ""),
            "created_at": f.created_at,
        }
        
        # 값이 있는 필드만 추가
        if f.event_start_date:
            item["event_start_date"] = f.event_start_date
        if f.event_end_date:
            item["event_end_date"] = f.event_end_date
        if f.event_place:
            item["event_place"] = f.event_place
        if f.address:
            item["address"] = f.address
        if f.tel:
            item["tel"] = f.tel
        if f.organizer:
            item["organizer"] = f.organizer
        if f.description:
            item["description"] = f.description
        if f.overview:
            item["overview"] = f.overview
        if f.first_image:
            item["image_url"] = f.first_image
        if f.latitude:
            item["latitude"] = float(f.latitude)
        if f.longitude:
            item["longitude"] = float(f.longitude)
        if f.category_code:
            item["category_code"] = f.category_code
            # 카테고리 정보 정규화
            item["category_info"] = normalize_category_data(f.category_code, None)
        
        items.append(item)
    
    return {
        "total": total,
        "items": items
    }

@router.get("/{content_id}/")
@require_permission("destinations.read")
async def get_festival_event(
    content_id: str,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    festival = db.query(FestivalEvent).filter(FestivalEvent.content_id == content_id).first()
    if not festival:
        raise HTTPException(status_code=404, detail="축제를 찾을 수 없습니다.")
    
    item = {
        "content_id": festival.content_id,
        "event_name": festival.event_name,
        "region_code": festival.region_code,
        "created_at": festival.created_at,
    }
    
    # 값이 있는 필드만 추가
    if festival.event_start_date:
        item["event_start_date"] = festival.event_start_date
    if festival.event_end_date:
        item["event_end_date"] = festival.event_end_date
    if festival.play_time:
        item["play_time"] = festival.play_time
    if festival.event_place:
        item["event_place"] = festival.event_place
    if festival.address:
        item["address"] = festival.address
    if festival.detail_address:
        item["detail_address"] = festival.detail_address
    if festival.zipcode:
        item["zipcode"] = festival.zipcode
    if festival.tel:
        item["tel"] = festival.tel
    if festival.telname:
        item["telname"] = festival.telname
    if festival.homepage:
        item["homepage"] = festival.homepage
    if festival.sponsor:
        item["sponsor"] = festival.sponsor
    if festival.organizer:
        item["organizer"] = festival.organizer
    if festival.description:
        item["description"] = festival.description
    if festival.overview:
        item["overview"] = festival.overview
    if festival.event_program:
        item["event_program"] = festival.event_program
    if festival.first_image:
        item["image_url"] = festival.first_image
    if festival.first_image_small:
        item["image_url_small"] = festival.first_image_small
    if festival.latitude:
        item["latitude"] = float(festival.latitude)
    if festival.longitude:
        item["longitude"] = float(festival.longitude)
    if festival.category_code:
        item["category_code"] = festival.category_code
        item["category_info"] = normalize_category_data(festival.category_code, None)
    if festival.updated_at:
        item["updated_at"] = festival.updated_at
    
    return item

@router.post("/", status_code=201)
@require_permission("destinations.write")
async def create_festival_event(
    current_admin: CurrentAdmin,
    event_name: str = Body(...),
    event_start_date: Optional[date] = Body(None),
    event_end_date: Optional[date] = Body(None),
    event_place: str = Body(None),
    address: str = Body(None),
    tel: str = Body(None),
    organizer: str = Body(None),
    description: str = Body(None),
    overview: str = Body(None),
    image_url: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    category_code: str = Body(None),
    region_code: str = Body(None),
    db: Session = Depends(get_db)
):
    new_festival = FestivalEvent(
        content_id=str(uuid4()),
        event_name=event_name,
        event_start_date=event_start_date,
        event_end_date=event_end_date,
        event_place=event_place,
        address=address,
        tel=tel,
        organizer=organizer,
        description=description,
        overview=overview,
        first_image=image_url,
        latitude=latitude,
        longitude=longitude,
        category_code=category_code,
        region_code=region_code,
    )
    db.add(new_festival)
    db.commit()
    db.refresh(new_festival)
    return {"content_id": new_festival.content_id}

@router.put("/{content_id}/", status_code=200)
@require_permission("destinations.write")
async def update_festival_event(
    content_id: str,
    current_admin: CurrentAdmin,
    event_name: str = Body(None),
    event_start_date: Optional[date] = Body(None),
    event_end_date: Optional[date] = Body(None),
    event_place: str = Body(None),
    address: str = Body(None),
    tel: str = Body(None),
    organizer: str = Body(None),
    description: str = Body(None),
    overview: str = Body(None),
    image_url: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    category_code: str = Body(None),
    region_code: str = Body(None),
    db: Session = Depends(get_db)
):
    festival = db.query(FestivalEvent).filter(FestivalEvent.content_id == content_id).first()
    if not festival:
        raise HTTPException(status_code=404, detail="축제를 찾을 수 없습니다.")
    
    if event_name is not None:
        festival.event_name = event_name
    if event_start_date is not None:
        festival.event_start_date = event_start_date
    if event_end_date is not None:
        festival.event_end_date = event_end_date
    if event_place is not None:
        festival.event_place = event_place
    if address is not None:
        festival.address = address
    if tel is not None:
        festival.tel = tel
    if organizer is not None:
        festival.organizer = organizer
    if description is not None:
        festival.description = description
    if overview is not None:
        festival.overview = overview
    if image_url is not None:
        festival.first_image = image_url
    if latitude is not None:
        festival.latitude = latitude
    if longitude is not None:
        festival.longitude = longitude
    if category_code is not None:
        festival.category_code = category_code
    if region_code is not None:
        festival.region_code = region_code
    
    db.commit()
    db.refresh(festival)
    return {"content_id": festival.content_id}

@router.delete("/{content_id}/", status_code=204)
@require_permission("destinations.delete")
async def delete_festival_event(
    content_id: str,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    festival = db.query(FestivalEvent).filter(FestivalEvent.content_id == content_id).first()
    if not festival:
        raise HTTPException(status_code=404, detail="축제를 찾을 수 없습니다.")
    db.delete(festival)
    db.commit()
    return None

@router.get("/autocomplete/")
@require_permission("destinations.read")
async def autocomplete_festival_names(
    current_admin: CurrentAdmin,
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """축제명 자동완성"""
    festivals = db.query(FestivalEvent.event_name).filter(
        FestivalEvent.event_name.ilike(f"%{q}%")
    ).distinct().limit(10).all()
    
    return [f[0] for f in festivals]