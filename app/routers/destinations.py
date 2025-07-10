from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..models import Destination, Region

router = APIRouter(prefix="/tourist-attractions", tags=["Tourist Attractions"])


@router.get("/")
def get_all_tourist_attractions(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total = db.query(Destination).count()
    destinations = (
        db.query(Destination)
        .order_by(Destination.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "content_id": str(d.destination_id),
                "attraction_name": d.name,
                "description": None,  # destinations 테이블에는 description 없음
                "address": None,  # destinations 테이블에는 address 없음  
                "image_url": d.image_url,
                "latitude": float(d.latitude) if d.latitude else None,
                "longitude": float(d.longitude) if d.longitude else None,
                "category_code": d.category,
                "category_name": d.category,
                "region_code": d.province,
                "region_name": d.region,
                "tags": d.tags,
                "amenities": d.amenities,
                "rating": d.rating,
                "created_at": d.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for d in destinations
        ],
    }


@router.get("/{content_id}")
def get_tourist_attraction(content_id: str, db: Session = Depends(get_db)):
    destination = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .first()
    )
    if not destination:
        raise HTTPException(status_code=404, detail="관광지를 찾을 수 없습니다.")
    return {
        "content_id": str(destination.destination_id),
        "attraction_name": destination.name,
        "description": None,  # destinations 테이블에는 description 없음
        "address": None,  # destinations 테이블에는 address 없음
        "image_url": destination.image_url,
        "latitude": float(destination.latitude) if destination.latitude else None,
        "longitude": float(destination.longitude) if destination.longitude else None,
        "category_code": destination.category,
        "category_name": destination.category,
        "region_code": destination.province,
        "region_name": destination.region,
        "tags": destination.tags,
        "amenities": destination.amenities,
        "rating": destination.rating,
        "created_at": destination.created_at,
        "updated_at": None,  # destinations 테이블에는 updated_at 없음
    }


@router.get("/search/")
def search_tourist_attractions(
    name: str = Query(None, description="관광지명"),
    category: str = Query(None, description="카테고리명"),
    region: str = Query(None, description="지역코드"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Destination)
    if name:
        query = query.filter(Destination.name.ilike(f"%{name}%"))
    if category:
        query = query.filter(Destination.category.ilike(f"%{category}%"))
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
                "content_id": str(d.destination_id),
                "attraction_name": d.name,
                "description": None,  # destinations 테이블에는 description 없음
                "address": None,  # destinations 테이블에는 address 없음
                "image_url": d.image_url,
                "latitude": float(d.latitude) if d.latitude else None,
                "longitude": float(d.longitude) if d.longitude else None,
                "category_code": d.category,
                "category_name": d.category,
                "region_code": d.province,
                "region_name": d.region,
                "tags": d.tags,
                "amenities": d.amenities,
                "rating": d.rating,
                "created_at": d.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for d in results
        ],
    }


@router.post("/", status_code=201)
def create_tourist_attraction(
    name: str = Body(...),
    province: str = Body(...),
    region: str = Body(None),
    category: str = Body(None),
    is_indoor: bool = Body(False),
    tags: list[str] = Body([]),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body({}),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    new_destination = Destination(
        destination_id=uuid4(),
        name=name,
        province=province,
        region=region,
        category=category,
        is_indoor=is_indoor,
        tags=tags,
        latitude=latitude,
        longitude=longitude,
        amenities=amenities,
        image_url=image_url,
    )
    db.add(new_destination)
    db.commit()
    db.refresh(new_destination)
    return {"content_id": str(new_destination.destination_id)}


@router.put("/{content_id}")
def update_tourist_attraction(
    content_id: str,
    name: str = Body(None),
    province: str = Body(None),
    region: str = Body(None),
    category: str = Body(None),
    is_indoor: bool = Body(None),
    tags: list[str] = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body(None),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    destination = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .first()
    )
    if not destination:
        raise HTTPException(status_code=404, detail="관광지를 찾을 수 없습니다.")
    if name is not None:
        destination.name = name
    if province is not None:
        destination.province = province
    if region is not None:
        destination.region = region
    if category is not None:
        destination.category = category
    if is_indoor is not None:
        destination.is_indoor = is_indoor
    if tags is not None:
        destination.tags = tags
    if latitude is not None:
        destination.latitude = latitude
    if longitude is not None:
        destination.longitude = longitude
    if amenities is not None:
        destination.amenities = amenities
    if image_url is not None:
        destination.image_url = image_url
    db.commit()
    db.refresh(destination)
    return {"content_id": str(destination.destination_id)}


@router.delete("/{content_id}", status_code=204)
def delete_tourist_attraction(content_id: str, db: Session = Depends(get_db)):
    destination = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .first()
    )
    if not destination:
        raise HTTPException(status_code=404, detail="관광지를 찾을 수 없습니다.")
    db.delete(destination)
    db.commit()
    return None
