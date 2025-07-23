from uuid import uuid4
from typing import Optional
import time
import random
import string

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
        # region_code 파라미터를 받으면 해당 지역의 관광지 필터링
        # 프론트엔드에서 '1', '2', '3' 등을 보내면 DB의 '01', '02', '03' 형식과 매칭
        if len(region_code) == 1 and region_code.isdigit():
            # 한 자리 숫자인 경우 앞에 0을 붙여서 검색
            padded_code = region_code.zfill(2)
            # 시도 레벨과 시군구 레벨 모두 검색 (예: '01'로 시작하는 모든 region_code)
            query = query.filter(TouristAttraction.region_code.like(f"{padded_code}%"))
        else:
            # 그 외의 경우 그대로 검색
            query = query.filter(TouristAttraction.region_code == region_code)
    
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
    
    # 의미있는 데이터만 포함하여 응답 구성
    items = []
    # 지역명 조회를 위한 region_codes 수집
    region_codes = list(set([item.region_code for item in attractions if item.region_code]))
    region_names = {}
    if region_codes:
        regions = db.query(Region).filter(Region.region_code.in_(region_codes)).all()
        region_names = {r.region_code: r.region_name for r in regions}

    for a in attractions:
        item = {
            "content_id": a.content_id,
            "attraction_name": a.attraction_name,
            "address": a.address,
            "region_code": a.region_code,
            "region_name": region_names.get(a.region_code, ""),
            "created_at": a.created_at,
        }
        
        # 값이 있는 필드만 추가
        if a.description:
            item["description"] = a.description
        if a.image_url:
            item["image_url"] = a.image_url
        if a.latitude:
            item["latitude"] = float(a.latitude)
        if a.longitude:
            item["longitude"] = float(a.longitude)
        if a.category_code:
            item["category_code"] = a.category_code
        if a.category_name:
            item["category_name"] = a.category_name
            # 카테고리 정보 정규화
            item["category_info"] = normalize_category_data(a.category_code, a.category_name)
        if a.updated_at:
            item["updated_at"] = a.updated_at
        
        # 반려동물 친화 정보
        if a.content_id in pet_info_dict:
            item["is_pet_friendly"] = True
        
        items.append(item)
    
    return {
        "total": total,
        "items": items
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
    
    # 지역명 조회
    region_name = ""
    if attraction.region_code:
        region = db.query(Region).filter(Region.region_code == attraction.region_code).first()
        if region:
            region_name = region.region_name
    
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
        "region_name": region_name,
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
        # 프론트엔드에서 '1', '2', '3' 등을 보내면 DB의 '01', '02', '03' 형식과 매칭
        if len(region) == 1 and region.isdigit():
            # 한 자리 숫자인 경우 앞에 0을 붙여서 검색
            padded_code = region.zfill(2)
            query = query.filter(TouristAttraction.region_code == padded_code)
        else:
            # 그 외의 경우 그대로 검색
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
    
    # 지역명 조회를 위한 region_codes 수집
    region_codes = list(set([item.region_code for item in results if item.region_code]))
    region_names = {}
    if region_codes:
        regions = db.query(Region).filter(Region.region_code.in_(region_codes)).all()
        region_names = {r.region_code: r.region_name for r in regions}
    
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
                "region_name": region_names.get(a.region_code, ""),
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
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # region_code 처리: 한 자리 숫자인 경우 앞에 0을 붙임
        region_code = data.get('region_code')
        if region_code is not None:
            # region_code를 문자열로 변환하고 숫자인 경우 처리
            region_code_str = str(region_code)
            if region_code_str.isdigit():
                if len(region_code_str) == 1:
                    region_code = region_code_str.zfill(2)
                else:
                    region_code = region_code_str
            else:
                region_code = region_code_str
        
        # 20자 제한에 맞는 고유 ID 생성 (타임스탬프 + 랜덤 문자열)
        timestamp = str(int(time.time()))[-10:]  # 마지막 10자리
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        content_id = f"{timestamp}{random_str}"[:20]  # 20자로 제한
        
        new_attraction = TouristAttraction(
            content_id=content_id,
            attraction_name=data.get('attraction_name'),
            description=data.get('description'),
            address=data.get('address'),
            image_url=data.get('image_url'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            category_code=data.get('category_code'),
            category_name=data.get('category_name'),
            region_code=region_code,
        )
        db.add(new_attraction)
        db.commit()
        db.refresh(new_attraction)
        return {"content_id": new_attraction.content_id}
    except Exception as e:
        db.rollback()
        print(f"Error creating tourist attraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"관광지 생성 중 오류가 발생했습니다: {str(e)}")

@router.put("/{content_id}")
@require_permission("destinations.write")
async def update_tourist_attraction(
    content_id: str,
    current_admin: CurrentAdmin,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    attraction = db.query(TouristAttraction).filter(TouristAttraction.content_id == content_id).first()
    if not attraction:
        raise HTTPException(status_code=404, detail="관광지를 찾을 수 없습니다.")
    if data.get('attraction_name') is not None:
        attraction.attraction_name = data.get('attraction_name')
    if data.get('description') is not None:
        attraction.description = data.get('description')
    if data.get('address') is not None:
        attraction.address = data.get('address')
    if data.get('image_url') is not None:
        attraction.image_url = data.get('image_url')
    if data.get('latitude') is not None:
        attraction.latitude = data.get('latitude')
    if data.get('longitude') is not None:
        attraction.longitude = data.get('longitude')
    if data.get('category_code') is not None:
        attraction.category_code = data.get('category_code')
    if data.get('category_name') is not None:
        attraction.category_name = data.get('category_name')
    if data.get('region_code') is not None:
        attraction.region_code = data.get('region_code')
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

