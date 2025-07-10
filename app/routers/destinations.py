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
    attraction_name: str = Body(...),
    description: str = Body(None),
    address: str = Body(None),
    image_url: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    category_code: str = Body(None),
    category_name: str = Body(None),
    region_code: str = Body(None),
    db: Session = Depends(get_db),
):
    new_attraction = TouristAttraction(
        content_id=str(uuid4()),
        attraction_name=attraction_name,
        description=description,
        address=address,
        image_url=image_url,
        latitude=latitude,
        longitude=longitude,
        category_code=category_code,
        category_name=category_name,
        region_code=region_code,
    )
    db.add(new_attraction)
    db.commit()
    db.refresh(new_attraction)
    return {"content_id": new_attraction.content_id}


@router.put("/{content_id}")
def update_tourist_attraction(
    content_id: str,
    attraction_name: str = Body(None),
    description: str = Body(None),
    address: str = Body(None),
    image_url: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    category_code: str = Body(None),
    category_name: str = Body(None),
    region_code: str = Body(None),
    db: Session = Depends(get_db),
):
    attraction = (
        db.query(TouristAttraction)
        .filter(TouristAttraction.content_id == content_id)
        .first()
    )
    if not attraction:
        raise HTTPException(status_code=404, detail="관광지를 찾을 수 없습니다.")
    if attraction_name is not None:
        attraction.attraction_name = attraction_name
    if description is not None:
        attraction.description = description
    if address is not None:
        attraction.address = address
    if image_url is not None:
        attraction.image_url = image_url
    if latitude is not None:
        attraction.latitude = latitude
    if longitude is not None:
        attraction.longitude = longitude
    if category_code is not None:
        attraction.category_code = category_code
    if category_name is not None:
        attraction.category_name = category_name
    if region_code is not None:
        attraction.region_code = region_code
    db.commit()
    db.refresh(attraction)
    return {"content_id": attraction.content_id}


@router.delete("/{content_id}", status_code=204)
def delete_tourist_attraction(content_id: str, db: Session = Depends(get_db)):
    attraction = (
        db.query(TouristAttraction)
        .filter(TouristAttraction.content_id == content_id)
        .first()
    )
    if not attraction:
        raise HTTPException(status_code=404, detail="관광지를 찾을 수 없습니다.")
    db.delete(attraction)
    db.commit()
    return None
