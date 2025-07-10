from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..models import Destination, Region

router = APIRouter(prefix="/transportation", tags=["Transportation"])


@router.get("/")
def get_all_transportation(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """교통 시설 목록 조회 (destinations 테이블의 교통 관련 데이터 사용)"""
    # 교통 관련 키워드로 필터링
    transportation_filter = or_(
        Destination.name.ilike('%역%'),
        Destination.name.ilike('%터미널%'),
        Destination.name.ilike('%공항%'),
        Destination.name.ilike('%항구%'),
        Destination.name.ilike('%항만%'),
        Destination.name.ilike('%버스정류장%'),
        Destination.name.ilike('%지하철%'),
        Destination.name.ilike('%전철%'),
        Destination.name.ilike('%기차역%'),
        Destination.name.ilike('%KTX%'),
        Destination.name.ilike('%고속버스%'),
        Destination.name.ilike('%시외버스%'),
        Destination.name.ilike('%선착장%'),
        Destination.name.ilike('%여객터미널%'),
        Destination.name.ilike('%교통%'),
        Destination.name.ilike('%택시%'),
        Destination.name.ilike('%렌터카%'),
        # 태그나 카테고리 기반 검색도 추가
        Destination.tags.contains(['교통']),
        Destination.tags.contains(['역']),
        Destination.tags.contains(['터미널']),
        Destination.tags.contains(['공항']),
        Destination.tags.contains(['항구'])
    )
    
    total = db.query(Destination).filter(transportation_filter).count()
    transportation_items = (
        db.query(Destination)
        .filter(transportation_filter)
        .order_by(Destination.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "content_id": str(item.destination_id),
                "facility_name": item.name,
                "region_code": item.province,
                "transport_type": _determine_transport_type(item.name),
                "address": None,  # destinations 테이블에는 address 없음
                "tel": item.amenities.get('tel') if item.amenities else None,
                "homepage": item.amenities.get('homepage') if item.amenities else None,
                "operating_hours": item.amenities.get('operating_hours') if item.amenities else None,
                "route_info": item.amenities.get('route_info') if item.amenities else None,
                "fare_info": item.amenities.get('fare_info') if item.amenities else None,
                "parking_info": item.amenities.get('parking_info') if item.amenities else None,
                "accessibility": item.amenities.get('accessibility') if item.amenities else None,
                "transfer_info": item.amenities.get('transfer_info') if item.amenities else None,
                "latitude": float(item.latitude) if item.latitude else None,
                "longitude": float(item.longitude) if item.longitude else None,
                "region_name": item.region,
                "image_url": item.image_url,
                "rating": item.rating,
                "amenities": item.amenities,
                "tags": item.tags,
                "created_at": item.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for item in transportation_items
        ],
    }


@router.get("/{content_id}")
def get_transportation_detail(content_id: str, db: Session = Depends(get_db)):
    """교통 시설 상세 조회"""
    transportation_filter = or_(
        Destination.name.ilike('%역%'),
        Destination.name.ilike('%터미널%'),
        Destination.name.ilike('%공항%'),
        Destination.name.ilike('%항구%'),
        Destination.name.ilike('%항만%'),
        Destination.name.ilike('%버스정류장%'),
        Destination.name.ilike('%지하철%'),
        Destination.name.ilike('%전철%'),
        Destination.name.ilike('%기차역%'),
        Destination.name.ilike('%KTX%'),
        Destination.name.ilike('%고속버스%'),
        Destination.name.ilike('%시외버스%'),
        Destination.name.ilike('%선착장%'),
        Destination.name.ilike('%여객터미널%'),
        Destination.name.ilike('%교통%'),
        Destination.name.ilike('%택시%'),
        Destination.name.ilike('%렌터카%'),
        Destination.tags.contains(['교통']),
        Destination.tags.contains(['역']),
        Destination.tags.contains(['터미널']),
        Destination.tags.contains(['공항']),
        Destination.tags.contains(['항구'])
    )
    
    transportation_item = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(transportation_filter)
        .first()
    )
    if not transportation_item:
        raise HTTPException(status_code=404, detail="교통 시설을 찾을 수 없습니다.")
    return {
        "content_id": str(transportation_item.destination_id),
        "facility_name": transportation_item.name,
        "region_code": transportation_item.province,
        "transport_type": _determine_transport_type(transportation_item.name),
        "address": None,  # destinations 테이블에는 address 없음
        "tel": transportation_item.amenities.get('tel') if transportation_item.amenities else None,
        "homepage": transportation_item.amenities.get('homepage') if transportation_item.amenities else None,
        "operating_hours": transportation_item.amenities.get('operating_hours') if transportation_item.amenities else None,
        "route_info": transportation_item.amenities.get('route_info') if transportation_item.amenities else None,
        "fare_info": transportation_item.amenities.get('fare_info') if transportation_item.amenities else None,
        "parking_info": transportation_item.amenities.get('parking_info') if transportation_item.amenities else None,
        "accessibility": transportation_item.amenities.get('accessibility') if transportation_item.amenities else None,
        "transfer_info": transportation_item.amenities.get('transfer_info') if transportation_item.amenities else None,
        "latitude": float(transportation_item.latitude) if transportation_item.latitude else None,
        "longitude": float(transportation_item.longitude) if transportation_item.longitude else None,
        "region_name": transportation_item.region,
        "image_url": transportation_item.image_url,
        "rating": transportation_item.rating,
        "amenities": transportation_item.amenities,
        "tags": transportation_item.tags,
        "created_at": transportation_item.created_at,
        "updated_at": None,  # destinations 테이블에는 updated_at 없음
    }


@router.get("/search/")
def search_transportation(
    name: str = Query(None, description="시설명"),
    region: str = Query(None, description="지역코드"),
    transport_type: str = Query(None, description="교통 수단 유형"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """교통 시설 검색"""
    # 기본 교통 필터
    transportation_filter = or_(
        Destination.name.ilike('%역%'),
        Destination.name.ilike('%터미널%'),
        Destination.name.ilike('%공항%'),
        Destination.name.ilike('%항구%'),
        Destination.name.ilike('%항만%'),
        Destination.name.ilike('%버스정류장%'),
        Destination.name.ilike('%지하철%'),
        Destination.name.ilike('%전철%'),
        Destination.name.ilike('%기차역%'),
        Destination.name.ilike('%KTX%'),
        Destination.name.ilike('%고속버스%'),
        Destination.name.ilike('%시외버스%'),
        Destination.name.ilike('%선착장%'),
        Destination.name.ilike('%여객터미널%'),
        Destination.name.ilike('%교통%'),
        Destination.name.ilike('%택시%'),
        Destination.name.ilike('%렌터카%'),
        Destination.tags.contains(['교통']),
        Destination.tags.contains(['역']),
        Destination.tags.contains(['터미널']),
        Destination.tags.contains(['공항']),
        Destination.tags.contains(['항구'])
    )
    
    query = db.query(Destination).filter(transportation_filter)
    
    if name:
        query = query.filter(Destination.name.ilike(f"%{name}%"))
    if region:
        query = query.filter(Destination.province == region)
    if transport_type:
        # transport_type으로 검색 시 태그나 이름을 통해 필터링
        query = query.filter(
            or_(
                Destination.name.ilike(f"%{transport_type}%"),
                Destination.tags.contains([transport_type])
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
                "content_id": str(item.destination_id),
                "facility_name": item.name,
                "region_code": item.province,
                "transport_type": _determine_transport_type(item.name),
                "address": None,  # destinations 테이블에는 address 없음
                "tel": item.amenities.get('tel') if item.amenities else None,
                "homepage": item.amenities.get('homepage') if item.amenities else None,
                "operating_hours": item.amenities.get('operating_hours') if item.amenities else None,
                "route_info": item.amenities.get('route_info') if item.amenities else None,
                "fare_info": item.amenities.get('fare_info') if item.amenities else None,
                "parking_info": item.amenities.get('parking_info') if item.amenities else None,
                "accessibility": item.amenities.get('accessibility') if item.amenities else None,
                "transfer_info": item.amenities.get('transfer_info') if item.amenities else None,
                "latitude": float(item.latitude) if item.latitude else None,
                "longitude": float(item.longitude) if item.longitude else None,
                "region_name": item.region,
                "image_url": item.image_url,
                "rating": item.rating,
                "amenities": item.amenities,
                "tags": item.tags,
                "created_at": item.created_at,
                "updated_at": None,  # destinations 테이블에는 updated_at 없음
            }
            for item in results
        ],
    }


@router.post("/", status_code=201)
def create_transportation(
    facility_name: str = Body(...),
    province: str = Body(...),
    region: str = Body(None),
    transport_type: str = Body(None),
    tel: str = Body(None),
    homepage: str = Body(None),
    operating_hours: str = Body(None),
    route_info: str = Body(None),
    fare_info: str = Body(None),
    parking_info: str = Body(None),
    accessibility: str = Body(None),
    transfer_info: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body({}),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    """교통 시설 등록 (destinations 테이블에 교통 시설로 추가)"""
    # amenities에 교통 관련 정보 추가
    facility_amenities = amenities.copy()
    if tel:
        facility_amenities['tel'] = tel
    if homepage:
        facility_amenities['homepage'] = homepage
    if operating_hours:
        facility_amenities['operating_hours'] = operating_hours
    if route_info:
        facility_amenities['route_info'] = route_info
    if fare_info:
        facility_amenities['fare_info'] = fare_info
    if parking_info:
        facility_amenities['parking_info'] = parking_info
    if accessibility:
        facility_amenities['accessibility'] = accessibility
    if transfer_info:
        facility_amenities['transfer_info'] = transfer_info
    
    # 교통 타입에 따른 카테고리 결정
    category = '교통시설' if transport_type else 'TOURIST_ATTRACTION'
    transport_tags = ['교통', '이동']
    
    if transport_type:
        if '역' in transport_type or '지하철' in transport_type or '전철' in transport_type:
            transport_tags.extend(['역', '지하철', '전철'])
        elif '터미널' in transport_type or '버스' in transport_type:
            transport_tags.extend(['터미널', '버스'])
        elif '공항' in transport_type:
            transport_tags.extend(['공항', '항공'])
        elif '항구' in transport_type or '항만' in transport_type:
            transport_tags.extend(['항구', '항만', '선박'])
        elif '택시' in transport_type:
            transport_tags.extend(['택시', '개인교통'])
        elif '렌터카' in transport_type:
            transport_tags.extend(['렌터카', '개인교통'])
        transport_tags.append(transport_type)
    
    new_transportation = Destination(
        destination_id=uuid4(),
        name=facility_name,
        province=province,
        region=region,
        category=category,
        is_indoor=_is_indoor_transport(facility_name, transport_type),
        tags=transport_tags,
        latitude=latitude,
        longitude=longitude,
        amenities=facility_amenities,
        image_url=image_url,
    )
    db.add(new_transportation)
    db.commit()
    db.refresh(new_transportation)
    return {"content_id": str(new_transportation.destination_id)}


@router.put("/{content_id}")
def update_transportation(
    content_id: str,
    facility_name: str = Body(None),
    province: str = Body(None),
    region: str = Body(None),
    transport_type: str = Body(None),
    tel: str = Body(None),
    homepage: str = Body(None),
    operating_hours: str = Body(None),
    route_info: str = Body(None),
    fare_info: str = Body(None),
    parking_info: str = Body(None),
    accessibility: str = Body(None),
    transfer_info: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body(None),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    """교통 시설 정보 수정"""
    transportation_filter = or_(
        Destination.name.ilike('%역%'),
        Destination.name.ilike('%터미널%'),
        Destination.name.ilike('%공항%'),
        Destination.name.ilike('%항구%'),
        Destination.name.ilike('%항만%'),
        Destination.name.ilike('%버스정류장%'),
        Destination.name.ilike('%지하철%'),
        Destination.name.ilike('%전철%'),
        Destination.name.ilike('%기차역%'),
        Destination.name.ilike('%KTX%'),
        Destination.name.ilike('%고속버스%'),
        Destination.name.ilike('%시외버스%'),
        Destination.name.ilike('%선착장%'),
        Destination.name.ilike('%여객터미널%'),
        Destination.name.ilike('%교통%'),
        Destination.name.ilike('%택시%'),
        Destination.name.ilike('%렌터카%'),
        Destination.tags.contains(['교통']),
        Destination.tags.contains(['역']),
        Destination.tags.contains(['터미널']),
        Destination.tags.contains(['공항']),
        Destination.tags.contains(['항구'])
    )
    
    transportation_item = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(transportation_filter)
        .first()
    )
    if not transportation_item:
        raise HTTPException(status_code=404, detail="교통 시설을 찾을 수 없습니다.")
    
    if facility_name is not None:
        transportation_item.name = facility_name
    if province is not None:
        transportation_item.province = province
    if region is not None:
        transportation_item.region = region
    if latitude is not None:
        transportation_item.latitude = latitude
    if longitude is not None:
        transportation_item.longitude = longitude
    if image_url is not None:
        transportation_item.image_url = image_url
    
    # amenities 업데이트
    if (amenities is not None or tel is not None or homepage is not None 
        or operating_hours is not None or route_info is not None
        or fare_info is not None or parking_info is not None
        or accessibility is not None or transfer_info is not None):
        current_amenities = transportation_item.amenities or {}
        if amenities is not None:
            current_amenities.update(amenities)
        if tel is not None:
            current_amenities['tel'] = tel
        if homepage is not None:
            current_amenities['homepage'] = homepage
        if operating_hours is not None:
            current_amenities['operating_hours'] = operating_hours
        if route_info is not None:
            current_amenities['route_info'] = route_info
        if fare_info is not None:
            current_amenities['fare_info'] = fare_info
        if parking_info is not None:
            current_amenities['parking_info'] = parking_info
        if accessibility is not None:
            current_amenities['accessibility'] = accessibility
        if transfer_info is not None:
            current_amenities['transfer_info'] = transfer_info
        transportation_item.amenities = current_amenities
    
    # 태그 업데이트 (transport_type이 제공된 경우)
    if transport_type is not None:
        current_tags = transportation_item.tags or []
        if transport_type not in current_tags:
            current_tags.append(transport_type)
        if '교통' not in current_tags:
            current_tags.append('교통')
        if '이동' not in current_tags:
            current_tags.append('이동')
        transportation_item.tags = current_tags
    
    # 실내/실외 여부 업데이트
    if facility_name is not None or transport_type is not None:
        transportation_item.is_indoor = _is_indoor_transport(
            facility_name or transportation_item.name, 
            transport_type
        )
    
    db.commit()
    db.refresh(transportation_item)
    return {"content_id": str(transportation_item.destination_id)}


@router.delete("/{content_id}", status_code=204)
def delete_transportation(content_id: str, db: Session = Depends(get_db)):
    """교통 시설 삭제"""
    transportation_filter = or_(
        Destination.name.ilike('%역%'),
        Destination.name.ilike('%터미널%'),
        Destination.name.ilike('%공항%'),
        Destination.name.ilike('%항구%'),
        Destination.name.ilike('%항만%'),
        Destination.name.ilike('%버스정류장%'),
        Destination.name.ilike('%지하철%'),
        Destination.name.ilike('%전철%'),
        Destination.name.ilike('%기차역%'),
        Destination.name.ilike('%KTX%'),
        Destination.name.ilike('%고속버스%'),
        Destination.name.ilike('%시외버스%'),
        Destination.name.ilike('%선착장%'),
        Destination.name.ilike('%여객터미널%'),
        Destination.name.ilike('%교통%'),
        Destination.name.ilike('%택시%'),
        Destination.name.ilike('%렌터카%'),
        Destination.tags.contains(['교통']),
        Destination.tags.contains(['역']),
        Destination.tags.contains(['터미널']),
        Destination.tags.contains(['공항']),
        Destination.tags.contains(['항구'])
    )
    
    transportation_item = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(transportation_filter)
        .first()
    )
    if not transportation_item:
        raise HTTPException(status_code=404, detail="교통 시설을 찾을 수 없습니다.")
    db.delete(transportation_item)
    db.commit()
    return None


@router.get("/autocomplete/")
def autocomplete_facility_name(q: str = Query(...), db: Session = Depends(get_db)):
    """시설명 자동완성"""
    transportation_filter = or_(
        Destination.name.ilike('%역%'),
        Destination.name.ilike('%터미널%'),
        Destination.name.ilike('%공항%'),
        Destination.name.ilike('%항구%'),
        Destination.name.ilike('%항만%'),
        Destination.name.ilike('%버스정류장%'),
        Destination.name.ilike('%지하철%'),
        Destination.name.ilike('%전철%'),
        Destination.name.ilike('%기차역%'),
        Destination.name.ilike('%KTX%'),
        Destination.name.ilike('%고속버스%'),
        Destination.name.ilike('%시외버스%'),
        Destination.name.ilike('%선착장%'),
        Destination.name.ilike('%여객터미널%'),
        Destination.name.ilike('%교통%'),
        Destination.name.ilike('%택시%'),
        Destination.name.ilike('%렌터카%'),
        Destination.tags.contains(['교통']),
        Destination.tags.contains(['역']),
        Destination.tags.contains(['터미널']),
        Destination.tags.contains(['공항']),
        Destination.tags.contains(['항구'])
    )
    
    results = (
        db.query(Destination.name)
        .filter(transportation_filter)
        .filter(Destination.name.ilike(f"%{q}%"))
        .distinct()
        .limit(10)
        .all()
    )
    return [r[0] for r in results]


def _determine_transport_type(name: str) -> str:
    """이름을 기반으로 교통 수단 유형 판단"""
    name_lower = name.lower()
    
    if '공항' in name_lower:
        return '공항'
    elif 'ktx' in name_lower or '고속철' in name_lower:
        return 'KTX역'
    elif '지하철' in name_lower or '전철' in name_lower:
        return '지하철역'
    elif '기차역' in name_lower or '철도역' in name_lower:
        return '기차역'
    elif '고속버스' in name_lower:
        return '고속버스터미널'
    elif '시외버스' in name_lower:
        return '시외버스터미널'
    elif '버스터미널' in name_lower or '버스정류장' in name_lower:
        return '버스터미널'
    elif '여객터미널' in name_lower or '선착장' in name_lower:
        return '여객터미널'
    elif '항구' in name_lower or '항만' in name_lower:
        return '항구'
    elif '택시' in name_lower:
        return '택시정류장'
    elif '렌터카' in name_lower:
        return '렌터카업체'
    elif '터미널' in name_lower:
        return '교통터미널'
    elif '역' in name_lower:
        return '기차역'
    else:
        return '기타교통시설'


def _is_indoor_transport(name: str, transport_type: str = None) -> bool:
    """교통 시설이 실내인지 판단"""
    name_lower = name.lower()
    type_lower = (transport_type or '').lower()
    
    # 실내 교통 시설 키워드
    indoor_keywords = [
        '공항', '터미널', '지하철', '전철', '렌터카',
        '여객터미널', '버스터미널'
    ]
    
    # 실외 교통 시설 키워드  
    outdoor_keywords = [
        '버스정류장', '택시정류장', '선착장'
    ]
    
    # 실내 키워드 확인
    for keyword in indoor_keywords:
        if keyword in name_lower or keyword in type_lower:
            return True
    
    # 실외 키워드 확인
    for keyword in outdoor_keywords:
        if keyword in name_lower or keyword in type_lower:
            return False
    
    # 기본값: 실내로 가정 (대부분의 교통시설은 건물 내부)
    return True