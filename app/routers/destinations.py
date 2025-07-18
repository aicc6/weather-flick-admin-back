from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import TouristAttraction, Region, PetTourInfo
from ..dependencies import CurrentAdmin, require_permission
from ..utils.category_mapping import normalize_category_data, get_main_categories

router = APIRouter(prefix="/tourist-attractions", tags=["Tourist Attractions"])

@router.get("/")
@require_permission("destinations.read")
async def get_all_tourist_attractions(
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    region_code: Optional[str] = Query(None, description="지역 코드"),  # region_code 파라미터 추가
    pet_friendly: Optional[bool] = Query(None, description="반려동물 동반 가능 여부")
):
    query = db.query(TouristAttraction)
    if region_code:
        # region_code 파라미터를 받으면 해당 지역의 tour_api_area_code를 찾아서 필터링
        region = db.query(Region).filter(Region.region_code == region_code).first()
        if region and region.tour_api_area_code:
            query = query.filter(TouristAttraction.region_code == region.tour_api_area_code)
        else:
            query = query.filter(TouristAttraction.region_code == str(region_code))
    
    # 반려동물 동반 가능 필터
    if pet_friendly is True:
        pet_content_ids = db.query(PetTourInfo.content_id).filter(
            PetTourInfo.content_id.isnot(None)
        ).subquery()
        query = query.filter(TouristAttraction.content_id.in_(pet_content_ids))
    
    total = query.count()
    attractions = query.order_by(TouristAttraction.created_at.desc()).offset(offset).limit(limit).all()
    
    # 반려동물 정보 조회
    attraction_ids = [a.content_id for a in attractions]
    pet_info_dict = {}
    if attraction_ids:
        pet_infos = db.query(PetTourInfo).filter(PetTourInfo.content_id.in_(attraction_ids)).all()
        pet_info_dict = {p.content_id: p for p in pet_infos}
    
    return {
        "count": total,
        "next": None,
        "previous": None,
        "results": [
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
                "is_pet_friendly": a.content_id in pet_info_dict,
                # 카테고리 정보 정규화
                "category_info": normalize_category_data(a.category_code, a.category_name),
            }
            for a in attractions
        ]
    }

@router.get("/{content_id}")
@require_permission("destinations.read")
async def get_tourist_attraction(
    content_id: str,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
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
@require_permission("destinations.read")
async def search_tourist_attractions(
    current_admin: CurrentAdmin,
    name: str = Query(None, description="관광지명"),
    category: str = Query(None, description="카테고리명"),
    region: str = Query(None, description="지역코드"),
    pet_friendly: Optional[bool] = Query(None, description="반려동물 동반 가능 여부"),
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
    
    # 반려동물 동반 가능 필터
    if pet_friendly is True:
        pet_content_ids = db.query(PetTourInfo.content_id).filter(
            PetTourInfo.content_id.isnot(None)
        ).subquery()
        query = query.filter(TouristAttraction.content_id.in_(pet_content_ids))
    
    total = query.count()
    results = query.order_by(TouristAttraction.created_at.desc()).offset(offset).limit(limit).all()
    
    # 반려동물 정보 조회
    attraction_ids = [a.content_id for a in results]
    pet_info_dict = {}
    if attraction_ids:
        pet_infos = db.query(PetTourInfo).filter(PetTourInfo.content_id.in_(attraction_ids)).all()
        pet_info_dict = {p.content_id: p for p in pet_infos}
    
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
                "is_pet_friendly": a.content_id in pet_info_dict,
                # 카테고리 정보 정규화
                "category_info": normalize_category_data(a.category_code, a.category_name),
            }
            for a in results
        ]
    }

@router.post("/", status_code=201)
@require_permission("destinations.write")
async def create_tourist_attraction(
    current_admin: CurrentAdmin,
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
@require_permission("destinations.write")
async def update_tourist_attraction(
    content_id: str,
    current_admin: CurrentAdmin,
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
@require_permission("destinations.delete")
async def delete_tourist_attraction(
    content_id: str,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    attraction = db.query(TouristAttraction).filter(TouristAttraction.content_id == content_id).first()
    if not attraction:
        raise HTTPException(status_code=404, detail="관광지를 찾을 수 없습니다.")
    db.delete(attraction)
    db.commit()
    return None

@router.get("/categories/main")
@require_permission("destinations.read")
async def get_main_categories(
    current_admin: CurrentAdmin,
):
    """주요 카테고리 목록 조회"""
    return {
        "categories": get_main_categories(),
        "total_count": len(get_main_categories())
    }

