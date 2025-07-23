from uuid import uuid4
from typing import Optional
import time
import random
import string

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Restaurant, Region
from ..dependencies import CurrentAdmin, require_permission
from ..utils.category_mapping import normalize_category_data

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])

@router.get("/")
@require_permission("destinations.read")
async def get_all_restaurants(
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    restaurant_name: Optional[str] = Query(None, description="음식점명"),
    region_code: Optional[str] = Query(None, description="지역 코드")
):
    query = db.query(Restaurant)
    
    if restaurant_name:
        query = query.filter(Restaurant.restaurant_name.ilike(f"%{restaurant_name}%"))
    
    if region_code:
        # region_code 파라미터를 받으면 해당 지역의 음식점 필터링
        # 프론트엔드에서 '1', '2', '3' 등을 보내면 DB의 '01', '02', '03' 형식과 매칭
        if len(region_code) == 1 and region_code.isdigit():
            # 한 자리 숫자인 경우 앞에 0을 붙여서 검색
            padded_code = region_code.zfill(2)
            # 시도 레벨과 시군구 레벨 모두 검색 (예: '01'로 시작하는 모든 region_code)
            query = query.filter(Restaurant.region_code.like(f"{padded_code}%"))
        else:
            # 그 외의 경우 그대로 검색
            query = query.filter(Restaurant.region_code == region_code)
    
    total = query.count()
    restaurants = query.order_by(Restaurant.created_at.desc()).offset(offset).limit(limit).all()
    
    # 의미있는 데이터만 포함하여 응답 구성
    items = []
    # 지역명 조회를 위한 region_codes 수집
    region_codes = list(set([item.region_code for item in restaurants if item.region_code]))
    region_names = {}
    if region_codes:
        regions = db.query(Region).filter(Region.region_code.in_(region_codes)).all()
        region_names = {r.region_code: r.region_name for r in regions}

    for r in restaurants:
        item = {
            "content_id": r.content_id,
            "restaurant_name": r.restaurant_name,
            "address": r.address,
            "region_code": r.region_code,
            "region_name": region_names.get(r.region_code, ""),
            "created_at": r.created_at,
        }
        
        # 값이 있는 필드만 추가
        if r.overview:
            item["description"] = r.overview
        if r.first_image:
            item["image_url"] = r.first_image
        if r.tel:
            item["tel"] = r.tel
        if r.specialty_dish:
            item["menu"] = r.specialty_dish
        if r.operating_hours:
            item["business_hours"] = r.operating_hours
        if r.cuisine_type:
            item["cuisine_type"] = r.cuisine_type
        if r.parking:
            item["parking"] = r.parking
        if r.latitude:
            item["latitude"] = float(r.latitude)
        if r.longitude:
            item["longitude"] = float(r.longitude)
        if r.category_code:
            item["category_code"] = r.category_code
            # 카테고리 정보 정규화
            item["category_info"] = normalize_category_data(r.category_code, None)
        
        items.append(item)
    
    return {
        "total": total,
        "items": items
    }

@router.get("/{content_id}")
@require_permission("destinations.read")
async def get_restaurant(
    content_id: str,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    restaurant = db.query(Restaurant).filter(Restaurant.content_id == content_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="음식점을 찾을 수 없습니다.")
    return {
        "content_id": restaurant.content_id,
        "restaurant_name": restaurant.restaurant_name,
        "description": restaurant.overview,
        "address": restaurant.address,
        "image_url": restaurant.first_image,
        "latitude": float(restaurant.latitude) if restaurant.latitude else None,
        "longitude": float(restaurant.longitude) if restaurant.longitude else None,
        "menu": restaurant.specialty_dish,
        "business_hours": restaurant.operating_hours,
        "tel": restaurant.tel,
        "cuisine_type": restaurant.cuisine_type,
        "category_code": restaurant.category_code,
        "region_code": restaurant.region_code,
        "created_at": restaurant.created_at,
        "updated_at": restaurant.updated_at,
    }

@router.post("/", status_code=201)
@require_permission("destinations.write")
async def create_restaurant(
    current_admin: CurrentAdmin,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # 필수 필드 확인
        if not data.get('restaurant_name'):
            raise HTTPException(status_code=400, detail="음식점명은 필수입니다.")
        if not data.get('address'):
            raise HTTPException(status_code=400, detail="주소는 필수입니다.")
        if not data.get('region_code'):
            raise HTTPException(status_code=400, detail="지역 코드는 필수입니다.")
        
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
        
        new_restaurant = Restaurant(
            content_id=content_id,
            restaurant_name=data.get('restaurant_name'),
            overview=data.get('description'),
            address=data.get('address'),
            first_image=data.get('image_url'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            specialty_dish=data.get('menu'),
            operating_hours=data.get('business_hours'),
            tel=data.get('tel'),
            cuisine_type=data.get('cuisine_type'),
            category_code=data.get('category_code'),
            region_code=region_code,
        )
        db.add(new_restaurant)
        db.commit()
        db.refresh(new_restaurant)
        return {"content_id": new_restaurant.content_id}
    except Exception as e:
        db.rollback()
        print(f"Error creating restaurant: {str(e)}")
        raise HTTPException(status_code=500, detail=f"음식점 생성 중 오류가 발생했습니다: {str(e)}")

@router.put("/{content_id}")
@require_permission("destinations.write")
async def update_restaurant(
    content_id: str,
    current_admin: CurrentAdmin,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    restaurant = db.query(Restaurant).filter(Restaurant.content_id == content_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="음식점을 찾을 수 없습니다.")
    
    if data.get('restaurant_name') is not None:
        restaurant.restaurant_name = data.get('restaurant_name')
    if data.get('description') is not None:
        restaurant.overview = data.get('description')
    if data.get('address') is not None:
        restaurant.address = data.get('address')
    if data.get('image_url') is not None:
        restaurant.first_image = data.get('image_url')
    if data.get('latitude') is not None:
        restaurant.latitude = data.get('latitude')
    if data.get('longitude') is not None:
        restaurant.longitude = data.get('longitude')
    if data.get('menu') is not None:
        restaurant.specialty_dish = data.get('menu')
    if data.get('business_hours') is not None:
        restaurant.operating_hours = data.get('business_hours')
    if data.get('tel') is not None:
        restaurant.tel = data.get('tel')
    if data.get('cuisine_type') is not None:
        restaurant.cuisine_type = data.get('cuisine_type')
    if data.get('category_code') is not None:
        restaurant.category_code = data.get('category_code')
    if data.get('region_code') is not None:
        restaurant.region_code = data.get('region_code')
    
    db.commit()
    db.refresh(restaurant)
    return {"content_id": restaurant.content_id}

@router.delete("/{content_id}", status_code=204)
@require_permission("destinations.delete")
async def delete_restaurant(
    content_id: str,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    restaurant = db.query(Restaurant).filter(Restaurant.content_id == content_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="음식점을 찾을 수 없습니다.")
    db.delete(restaurant)
    db.commit()
    return None