from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import TouristAttraction
from uuid import uuid4

router = APIRouter(prefix="/tourist-attractions", tags=["Tourist Attractions"])

@router.get("/")
def get_all_tourist_attractions(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    total = db.query(TouristAttraction).count()
    attractions = db.query(TouristAttraction).order_by(TouristAttraction.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "content_id": a.content_id,
                "attraction_name": a.attraction_name,
                "description": a.description,
                "address": a.address,
                "image_url": a.image_url,
                "latitude": float(a.latitude) if a.latitude else None,
                "longitude": float(a.longitude) if a.longitude else None,
                "category_code": a.category_code,
                "category_name": a.category_name,
                "region_code": a.region_code,
                "created_at": a.created_at,
                "updated_at": a.updated_at,
            }
            for a in attractions
        ]
    }

@router.get("/{content_id}")
def get_tourist_attraction(content_id: str, db: Session = Depends(get_db)):
    attraction = db.query(TouristAttraction).filter(TouristAttraction.content_id == content_id).first()
    if not attraction:
        raise HTTPException(status_code=404, detail="관광지를 찾을 수 없습니다.")
    return {
        "content_id": attraction.content_id,
        "attraction_name": attraction.attraction_name,
        "description": attraction.description,
        "address": attraction.address,
        "image_url": attraction.image_url,
        "latitude": float(attraction.latitude) if attraction.latitude else None,
        "longitude": float(attraction.longitude) if attraction.longitude else None,
        "category_code": attraction.category_code,
        "category_name": attraction.category_name,
        "region_code": attraction.region_code,
        "created_at": attraction.created_at,
        "updated_at": attraction.updated_at,
    }

@router.get("/search/")
def search_tourist_attractions(
    name: str = Query(None, description="관광지명"),
    category: str = Query(None, description="카테고리명"),
    region: str = Query(None, description="지역코드"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(TouristAttraction)
    if name:
        query = query.filter(TouristAttraction.attraction_name.ilike(f"%{name}%"))
    if category:
        query = query.filter(TouristAttraction.category_name.ilike(f"%{category}%"))
    if region:
        query = query.filter(TouristAttraction.region_code == region)
    total = query.count()
    results = query.order_by(TouristAttraction.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "content_id": a.content_id,
                "attraction_name": a.attraction_name,
                "description": a.description,
                "address": a.address,
                "image_url": a.image_url,
                "latitude": float(a.latitude) if a.latitude else None,
                "longitude": float(a.longitude) if a.longitude else None,
                "category_code": a.category_code,
                "category_name": a.category_name,
                "region_code": a.region_code,
                "created_at": a.created_at,
                "updated_at": a.updated_at,
            }
            for a in results
        ]
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
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
):
    attraction = db.query(TouristAttraction).filter(TouristAttraction.content_id == content_id).first()
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
    attraction = db.query(TouristAttraction).filter(TouristAttraction.content_id == content_id).first()
    if not attraction:
        raise HTTPException(status_code=404, detail="관광지를 찾을 수 없습니다.")
    db.delete(attraction)
    db.commit()
    return None
