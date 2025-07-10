from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..models import Destination, Region

router = APIRouter(prefix="/shopping", tags=["Shopping"])


@router.get("/")
def get_all_shopping(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """쇼핑 시설 목록 조회 (destinations 테이블의 쇼핑/시장 데이터 사용)"""
    # 쇼핑 관련 키워드로 필터링
    shopping_filter = or_(
        Destination.name.ilike('%시장%'),
        Destination.name.ilike('%쇼핑%'),
        Destination.name.ilike('%마트%'),
        Destination.name.ilike('%마켓%'),
        Destination.name.ilike('%백화점%'),
        Destination.name.ilike('%상가%'),
        Destination.name.ilike('%아울렛%'),
        Destination.name.ilike('%플라자%'),
        Destination.name.ilike('%상점%'),
        Destination.name.ilike('%매장%'),
        # 태그나 카테고리 기반 검색도 추가
        Destination.tags.contains(['쇼핑']),
        Destination.tags.contains(['시장']),
        Destination.tags.contains(['상가'])
    )
    
    total = db.query(Destination).filter(shopping_filter).count()
    shopping_items = (
        db.query(Destination)
        .filter(shopping_filter)
        .order_by(Destination.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "content_id": str(shop.destination_id),
                "shop_name": shop.name,
                "region_code": shop.province,
                "shopping_type": _determine_shopping_type(shop.name),
                "address": None,  # destinations 테이블에는 address 없음
                "tel": shop.amenities.get('tel') if shop.amenities else None,
                "homepage": shop.amenities.get('homepage') if shop.amenities else None,
                "operating_hours": shop.amenities.get('operating_hours') if shop.amenities else None,
                "parking_info": shop.amenities.get('parking_info') if shop.amenities else None,
                "facilities": shop.amenities.get('facilities') if shop.amenities else None,
                "latitude": float(shop.latitude) if shop.latitude else None,
                "longitude": float(shop.longitude) if shop.longitude else None,
                "region_name": shop.region,
                "image_url": shop.image_url,
                "rating": shop.rating,
                "amenities": shop.amenities,
                "tags": shop.tags,
                "created_at": shop.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for shop in shopping_items
        ],
    }


@router.get("/{content_id}")
def get_shopping_detail(content_id: str, db: Session = Depends(get_db)):
    """쇼핑 시설 상세 조회"""
    shopping_filter = or_(
        Destination.name.ilike('%시장%'),
        Destination.name.ilike('%쇼핑%'),
        Destination.name.ilike('%마트%'),
        Destination.name.ilike('%마켓%'),
        Destination.name.ilike('%백화점%'),
        Destination.name.ilike('%상가%'),
        Destination.name.ilike('%아울렛%'),
        Destination.name.ilike('%플라자%'),
        Destination.name.ilike('%상점%'),
        Destination.name.ilike('%매장%'),
        Destination.tags.contains(['쇼핑']),
        Destination.tags.contains(['시장']),
        Destination.tags.contains(['상가'])
    )
    
    shopping_item = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(shopping_filter)
        .first()
    )
    if not shopping_item:
        raise HTTPException(status_code=404, detail="쇼핑 시설을 찾을 수 없습니다.")
    return {
        "content_id": str(shopping_item.destination_id),
        "shop_name": shopping_item.name,
        "region_code": shopping_item.province,
        "shopping_type": _determine_shopping_type(shopping_item.name),
        "address": None,  # destinations 테이블에는 address 없음
        "tel": shopping_item.amenities.get('tel') if shopping_item.amenities else None,
        "homepage": shopping_item.amenities.get('homepage') if shopping_item.amenities else None,
        "operating_hours": shopping_item.amenities.get('operating_hours') if shopping_item.amenities else None,
        "parking_info": shopping_item.amenities.get('parking_info') if shopping_item.amenities else None,
        "facilities": shopping_item.amenities.get('facilities') if shopping_item.amenities else None,
        "latitude": float(shopping_item.latitude) if shopping_item.latitude else None,
        "longitude": float(shopping_item.longitude) if shopping_item.longitude else None,
        "region_name": shopping_item.region,
        "image_url": shopping_item.image_url,
        "rating": shopping_item.rating,
        "amenities": shopping_item.amenities,
        "tags": shopping_item.tags,
        "created_at": shopping_item.created_at,
        "updated_at": None,  # destinations 테이블에는 updated_at 없음
    }


@router.get("/search/")
def search_shopping(
    name: str = Query(None, description="쇼핑 시설명"),
    region: str = Query(None, description="지역코드"),
    shopping_type: str = Query(None, description="쇼핑 시설 유형"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """쇼핑 시설 검색"""
    # 기본 쇼핑 필터
    shopping_filter = or_(
        Destination.name.ilike('%시장%'),
        Destination.name.ilike('%쇼핑%'),
        Destination.name.ilike('%마트%'),
        Destination.name.ilike('%마켓%'),
        Destination.name.ilike('%백화점%'),
        Destination.name.ilike('%상가%'),
        Destination.name.ilike('%아울렛%'),
        Destination.name.ilike('%플라자%'),
        Destination.name.ilike('%상점%'),
        Destination.name.ilike('%매장%'),
        Destination.tags.contains(['쇼핑']),
        Destination.tags.contains(['시장']),
        Destination.tags.contains(['상가'])
    )
    
    query = db.query(Destination).filter(shopping_filter)
    
    if name:
        query = query.filter(Destination.name.ilike(f"%{name}%"))
    if region:
        query = query.filter(Destination.province == region)
    if shopping_type:
        # shopping_type으로 검색 시 태그나 이름을 통해 필터링
        query = query.filter(
            or_(
                Destination.name.ilike(f"%{shopping_type}%"),
                Destination.tags.contains([shopping_type])
            )
        )
    
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
                "content_id": str(shop.destination_id),
                "shop_name": shop.name,
                "region_code": shop.province,
                "shopping_type": _determine_shopping_type(shop.name),
                "address": None,  # destinations 테이블에는 address 없음
                "tel": shop.amenities.get('tel') if shop.amenities else None,
                "homepage": shop.amenities.get('homepage') if shop.amenities else None,
                "operating_hours": shop.amenities.get('operating_hours') if shop.amenities else None,
                "parking_info": shop.amenities.get('parking_info') if shop.amenities else None,
                "facilities": shop.amenities.get('facilities') if shop.amenities else None,
                "latitude": float(shop.latitude) if shop.latitude else None,
                "longitude": float(shop.longitude) if shop.longitude else None,
                "region_name": shop.region,
                "image_url": shop.image_url,
                "rating": shop.rating,
                "amenities": shop.amenities,
                "tags": shop.tags,
                "created_at": shop.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for shop in results
        ],
    }


@router.post("/", status_code=201)
def create_shopping(
    shop_name: str = Body(...),
    province: str = Body(...),
    region: str = Body(None),
    shopping_type: str = Body(None),
    tel: str = Body(None),
    homepage: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body({}),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    """쇼핑 시설 등록 (destinations 테이블에 쇼핑 시설로 추가)"""
    # amenities에 쇼핑 관련 정보 추가
    shop_amenities = amenities.copy()
    if tel:
        shop_amenities['tel'] = tel
    if homepage:
        shop_amenities['homepage'] = homepage
    
    # 쇼핑 타입에 따른 카테고리 결정
    category = '쇼핑' if shopping_type else 'TOURIST_ATTRACTION'
    shopping_tags = ['쇼핑', '상가']
    
    if shopping_type:
        if '시장' in shopping_type:
            shopping_tags.extend(['시장', '전통시장'])
        elif '백화점' in shopping_type:
            shopping_tags.extend(['백화점', '대형쇼핑몰'])
        elif '아울렛' in shopping_type:
            shopping_tags.extend(['아울렛', '할인매장'])
        elif '마트' in shopping_type:
            shopping_tags.extend(['마트', '대형마트'])
        shopping_tags.append(shopping_type)
    
    new_shopping = Destination(
        destination_id=uuid4(),
        name=shop_name,
        province=province,
        region=region,
        category=category,
        is_indoor=True,  # 쇼핑 시설은 일반적으로 실내
        tags=shopping_tags,
        latitude=latitude,
        longitude=longitude,
        amenities=shop_amenities,
        image_url=image_url,
    )
    db.add(new_shopping)
    db.commit()
    db.refresh(new_shopping)
    return {"content_id": str(new_shopping.destination_id)}


@router.put("/{content_id}")
def update_shopping(
    content_id: str,
    shop_name: str = Body(None),
    province: str = Body(None),
    region: str = Body(None),
    shopping_type: str = Body(None),
    tel: str = Body(None),
    homepage: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body(None),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    """쇼핑 시설 정보 수정"""
    shopping_filter = or_(
        Destination.name.ilike('%시장%'),
        Destination.name.ilike('%쇼핑%'),
        Destination.name.ilike('%마트%'),
        Destination.name.ilike('%마켓%'),
        Destination.name.ilike('%백화점%'),
        Destination.name.ilike('%상가%'),
        Destination.name.ilike('%아울렛%'),
        Destination.name.ilike('%플라자%'),
        Destination.name.ilike('%상점%'),
        Destination.name.ilike('%매장%'),
        Destination.tags.contains(['쇼핑']),
        Destination.tags.contains(['시장']),
        Destination.tags.contains(['상가'])
    )
    
    shopping_item = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(shopping_filter)
        .first()
    )
    if not shopping_item:
        raise HTTPException(status_code=404, detail="쇼핑 시설을 찾을 수 없습니다.")
    
    if shop_name is not None:
        shopping_item.name = shop_name
    if province is not None:
        shopping_item.province = province
    if region is not None:
        shopping_item.region = region
    if latitude is not None:
        shopping_item.latitude = latitude
    if longitude is not None:
        shopping_item.longitude = longitude
    if image_url is not None:
        shopping_item.image_url = image_url
    
    # amenities 업데이트
    if amenities is not None or tel is not None or homepage is not None:
        current_amenities = shopping_item.amenities or {}
        if amenities is not None:
            current_amenities.update(amenities)
        if tel is not None:
            current_amenities['tel'] = tel
        if homepage is not None:
            current_amenities['homepage'] = homepage
        shopping_item.amenities = current_amenities
    
    # 태그 업데이트 (shopping_type이 제공된 경우)
    if shopping_type is not None:
        current_tags = shopping_item.tags or []
        if shopping_type not in current_tags:
            current_tags.append(shopping_type)
        if '쇼핑' not in current_tags:
            current_tags.append('쇼핑')
        shopping_item.tags = current_tags
    
    db.commit()
    db.refresh(shopping_item)
    return {"content_id": str(shopping_item.destination_id)}


@router.delete("/{content_id}", status_code=204)
def delete_shopping(content_id: str, db: Session = Depends(get_db)):
    """쇼핑 시설 삭제"""
    shopping_filter = or_(
        Destination.name.ilike('%시장%'),
        Destination.name.ilike('%쇼핑%'),
        Destination.name.ilike('%마트%'),
        Destination.name.ilike('%마켓%'),
        Destination.name.ilike('%백화점%'),
        Destination.name.ilike('%상가%'),
        Destination.name.ilike('%아울렛%'),
        Destination.name.ilike('%플라자%'),
        Destination.name.ilike('%상점%'),
        Destination.name.ilike('%매장%'),
        Destination.tags.contains(['쇼핑']),
        Destination.tags.contains(['시장']),
        Destination.tags.contains(['상가'])
    )
    
    shopping_item = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(shopping_filter)
        .first()
    )
    if not shopping_item:
        raise HTTPException(status_code=404, detail="쇼핑 시설을 찾을 수 없습니다.")
    db.delete(shopping_item)
    db.commit()
    return None


def _determine_shopping_type(name: str) -> str:
    """이름을 기반으로 쇼핑 시설 유형 판단"""
    name_lower = name.lower()
    
    if '시장' in name_lower:
        if '전통' in name_lower or '재래' in name_lower:
            return '전통시장'
        elif '수산' in name_lower or '어시장' in name_lower:
            return '수산시장'
        else:
            return '시장'
    elif '백화점' in name_lower:
        return '백화점'
    elif '아울렛' in name_lower:
        return '아울렛'
    elif '마트' in name_lower or '마켓' in name_lower:
        if '대형' in name_lower or '하이퍼' in name_lower:
            return '대형마트'
        else:
            return '마트'
    elif '쇼핑몰' in name_lower or '몰' in name_lower:
        return '쇼핑몰'
    elif '상가' in name_lower:
        return '상가'
    elif '플라자' in name_lower:
        return '플라자'
    else:
        return '기타쇼핑시설'