from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..models import Destination, Region

router = APIRouter(prefix="/leisure-sports", tags=["Leisure Sports"])


@router.get("/")
def get_all_leisure_sports(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """레저/스포츠 시설 목록 조회 (destinations 테이블의 레저/스포츠 데이터 사용)"""
    # 레저/스포츠 관련 키워드로 필터링
    leisure_sports_filter = or_(
        Destination.name.ilike('%골프%'),
        Destination.name.ilike('%스포츠%'),
        Destination.name.ilike('%체육%'),
        Destination.name.ilike('%헬스%'),
        Destination.name.ilike('%수영%'),
        Destination.name.ilike('%테니스%'),
        Destination.name.ilike('%볼링%'),
        Destination.name.ilike('%당구%'),
        Destination.name.ilike('%배드민턴%'),
        Destination.name.ilike('%야구%'),
        Destination.name.ilike('%축구%'),
        Destination.name.ilike('%농구%'),
        Destination.name.ilike('%체육관%'),
        Destination.name.ilike('%운동%'),
        Destination.name.ilike('%레저%'),
        Destination.name.ilike('%리조트%'),
        Destination.name.ilike('%스키%'),
        Destination.name.ilike('%스케이트%'),
        # 태그나 카테고리 기반 검색도 추가
        Destination.tags.contains(['스포츠']),
        Destination.tags.contains(['레저']),
        Destination.tags.contains(['골프']),
        Destination.tags.contains(['체육'])
    )
    
    total = db.query(Destination).filter(leisure_sports_filter).count()
    leisure_sports_items = (
        db.query(Destination)
        .filter(leisure_sports_filter)
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
                "sports_type": _determine_sports_type(item.name),
                "address": None,  # destinations 테이블에는 address 없음
                "tel": item.amenities.get('tel') if item.amenities else None,
                "homepage": item.amenities.get('homepage') if item.amenities else None,
                "operating_hours": item.amenities.get('operating_hours') if item.amenities else None,
                "reservation_info": item.amenities.get('reservation_info') if item.amenities else None,
                "admission_fee": item.amenities.get('admission_fee') if item.amenities else None,
                "parking_info": item.amenities.get('parking_info') if item.amenities else None,
                "rental_info": item.amenities.get('rental_info') if item.amenities else None,
                "capacity": item.amenities.get('capacity') if item.amenities else None,
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
            for item in leisure_sports_items
        ],
    }


@router.get("/{content_id}")
def get_leisure_sports_detail(content_id: str, db: Session = Depends(get_db)):
    """레저/스포츠 시설 상세 조회"""
    leisure_sports_filter = or_(
        Destination.name.ilike('%골프%'),
        Destination.name.ilike('%스포츠%'),
        Destination.name.ilike('%체육%'),
        Destination.name.ilike('%헬스%'),
        Destination.name.ilike('%수영%'),
        Destination.name.ilike('%테니스%'),
        Destination.name.ilike('%볼링%'),
        Destination.name.ilike('%당구%'),
        Destination.name.ilike('%배드민턴%'),
        Destination.name.ilike('%야구%'),
        Destination.name.ilike('%축구%'),
        Destination.name.ilike('%농구%'),
        Destination.name.ilike('%체육관%'),
        Destination.name.ilike('%운동%'),
        Destination.name.ilike('%레저%'),
        Destination.name.ilike('%리조트%'),
        Destination.name.ilike('%스키%'),
        Destination.name.ilike('%스케이트%'),
        Destination.tags.contains(['스포츠']),
        Destination.tags.contains(['레저']),
        Destination.tags.contains(['골프']),
        Destination.tags.contains(['체육'])
    )
    
    leisure_sports_item = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(leisure_sports_filter)
        .first()
    )
    if not leisure_sports_item:
        raise HTTPException(status_code=404, detail="레저/스포츠 시설을 찾을 수 없습니다.")
    return {
        "content_id": str(leisure_sports_item.destination_id),
        "facility_name": leisure_sports_item.name,
        "region_code": leisure_sports_item.province,
        "sports_type": _determine_sports_type(leisure_sports_item.name),
        "address": None,  # destinations 테이블에는 address 없음
        "tel": leisure_sports_item.amenities.get('tel') if leisure_sports_item.amenities else None,
        "homepage": leisure_sports_item.amenities.get('homepage') if leisure_sports_item.amenities else None,
        "operating_hours": leisure_sports_item.amenities.get('operating_hours') if leisure_sports_item.amenities else None,
        "reservation_info": leisure_sports_item.amenities.get('reservation_info') if leisure_sports_item.amenities else None,
        "admission_fee": leisure_sports_item.amenities.get('admission_fee') if leisure_sports_item.amenities else None,
        "parking_info": leisure_sports_item.amenities.get('parking_info') if leisure_sports_item.amenities else None,
        "rental_info": leisure_sports_item.amenities.get('rental_info') if leisure_sports_item.amenities else None,
        "capacity": leisure_sports_item.amenities.get('capacity') if leisure_sports_item.amenities else None,
        "latitude": float(leisure_sports_item.latitude) if leisure_sports_item.latitude else None,
        "longitude": float(leisure_sports_item.longitude) if leisure_sports_item.longitude else None,
        "region_name": leisure_sports_item.region,
        "image_url": leisure_sports_item.image_url,
        "rating": leisure_sports_item.rating,
        "amenities": leisure_sports_item.amenities,
        "tags": leisure_sports_item.tags,
        "created_at": leisure_sports_item.created_at,
        "updated_at": None,  # destinations 테이블에는 updated_at 없음
    }


@router.get("/search/")
def search_leisure_sports(
    name: str = Query(None, description="시설명"),
    region: str = Query(None, description="지역코드"),
    sports_type: str = Query(None, description="스포츠 유형"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """레저/스포츠 시설 검색"""
    # 기본 레저/스포츠 필터
    leisure_sports_filter = or_(
        Destination.name.ilike('%골프%'),
        Destination.name.ilike('%스포츠%'),
        Destination.name.ilike('%체육%'),
        Destination.name.ilike('%헬스%'),
        Destination.name.ilike('%수영%'),
        Destination.name.ilike('%테니스%'),
        Destination.name.ilike('%볼링%'),
        Destination.name.ilike('%당구%'),
        Destination.name.ilike('%배드민턴%'),
        Destination.name.ilike('%야구%'),
        Destination.name.ilike('%축구%'),
        Destination.name.ilike('%농구%'),
        Destination.name.ilike('%체육관%'),
        Destination.name.ilike('%운동%'),
        Destination.name.ilike('%레저%'),
        Destination.name.ilike('%리조트%'),
        Destination.name.ilike('%스키%'),
        Destination.name.ilike('%스케이트%'),
        Destination.tags.contains(['스포츠']),
        Destination.tags.contains(['레저']),
        Destination.tags.contains(['골프']),
        Destination.tags.contains(['체육'])
    )
    
    query = db.query(Destination).filter(leisure_sports_filter)
    
    if name:
        query = query.filter(Destination.name.ilike(f"%{name}%"))
    if region:
        query = query.filter(Destination.province == region)
    if sports_type:
        # sports_type으로 검색 시 태그나 이름을 통해 필터링
        query = query.filter(
            or_(
                Destination.name.ilike(f"%{sports_type}%"),
                Destination.tags.contains([sports_type])
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
                "sports_type": _determine_sports_type(item.name),
                "address": None,  # destinations 테이블에는 address 없음
                "tel": item.amenities.get('tel') if item.amenities else None,
                "homepage": item.amenities.get('homepage') if item.amenities else None,
                "operating_hours": item.amenities.get('operating_hours') if item.amenities else None,
                "reservation_info": item.amenities.get('reservation_info') if item.amenities else None,
                "admission_fee": item.amenities.get('admission_fee') if item.amenities else None,
                "parking_info": item.amenities.get('parking_info') if item.amenities else None,
                "rental_info": item.amenities.get('rental_info') if item.amenities else None,
                "capacity": item.amenities.get('capacity') if item.amenities else None,
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
def create_leisure_sports(
    facility_name: str = Body(...),
    province: str = Body(...),
    region: str = Body(None),
    sports_type: str = Body(None),
    tel: str = Body(None),
    homepage: str = Body(None),
    operating_hours: str = Body(None),
    reservation_info: str = Body(None),
    admission_fee: str = Body(None),
    parking_info: str = Body(None),
    rental_info: str = Body(None),
    capacity: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body({}),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    """레저/스포츠 시설 등록 (destinations 테이블에 레저/스포츠 시설로 추가)"""
    # amenities에 레저/스포츠 관련 정보 추가
    facility_amenities = amenities.copy()
    if tel:
        facility_amenities['tel'] = tel
    if homepage:
        facility_amenities['homepage'] = homepage
    if operating_hours:
        facility_amenities['operating_hours'] = operating_hours
    if reservation_info:
        facility_amenities['reservation_info'] = reservation_info
    if admission_fee:
        facility_amenities['admission_fee'] = admission_fee
    if parking_info:
        facility_amenities['parking_info'] = parking_info
    if rental_info:
        facility_amenities['rental_info'] = rental_info
    if capacity:
        facility_amenities['capacity'] = capacity
    
    # 스포츠 타입에 따른 카테고리 결정
    category = '레저스포츠' if sports_type else 'TOURIST_ATTRACTION'
    sports_tags = ['레저', '스포츠']
    
    if sports_type:
        if '골프' in sports_type:
            sports_tags.extend(['골프', '골프장'])
        elif '수영' in sports_type:
            sports_tags.extend(['수영', '수영장'])
        elif '테니스' in sports_type:
            sports_tags.extend(['테니스', '테니스장'])
        elif '체육' in sports_type or '헬스' in sports_type:
            sports_tags.extend(['체육관', '헬스장'])
        elif '스키' in sports_type:
            sports_tags.extend(['스키', '스키장'])
        sports_tags.append(sports_type)
    
    new_leisure_sports = Destination(
        destination_id=uuid4(),
        name=facility_name,
        province=province,
        region=region,
        category=category,
        is_indoor=_is_indoor_sports(facility_name, sports_type),
        tags=sports_tags,
        latitude=latitude,
        longitude=longitude,
        amenities=facility_amenities,
        image_url=image_url,
    )
    db.add(new_leisure_sports)
    db.commit()
    db.refresh(new_leisure_sports)
    return {"content_id": str(new_leisure_sports.destination_id)}


@router.put("/{content_id}")
def update_leisure_sports(
    content_id: str,
    facility_name: str = Body(None),
    province: str = Body(None),
    region: str = Body(None),
    sports_type: str = Body(None),
    tel: str = Body(None),
    homepage: str = Body(None),
    operating_hours: str = Body(None),
    reservation_info: str = Body(None),
    admission_fee: str = Body(None),
    parking_info: str = Body(None),
    rental_info: str = Body(None),
    capacity: str = Body(None),
    latitude: float = Body(None),
    longitude: float = Body(None),
    amenities: dict = Body(None),
    image_url: str = Body(None),
    db: Session = Depends(get_db),
):
    """레저/스포츠 시설 정보 수정"""
    leisure_sports_filter = or_(
        Destination.name.ilike('%골프%'),
        Destination.name.ilike('%스포츠%'),
        Destination.name.ilike('%체육%'),
        Destination.name.ilike('%헬스%'),
        Destination.name.ilike('%수영%'),
        Destination.name.ilike('%테니스%'),
        Destination.name.ilike('%볼링%'),
        Destination.name.ilike('%당구%'),
        Destination.name.ilike('%배드민턴%'),
        Destination.name.ilike('%야구%'),
        Destination.name.ilike('%축구%'),
        Destination.name.ilike('%농구%'),
        Destination.name.ilike('%체육관%'),
        Destination.name.ilike('%운동%'),
        Destination.name.ilike('%레저%'),
        Destination.name.ilike('%리조트%'),
        Destination.name.ilike('%스키%'),
        Destination.name.ilike('%스케이트%'),
        Destination.tags.contains(['스포츠']),
        Destination.tags.contains(['레저']),
        Destination.tags.contains(['골프']),
        Destination.tags.contains(['체육'])
    )
    
    leisure_sports_item = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(leisure_sports_filter)
        .first()
    )
    if not leisure_sports_item:
        raise HTTPException(status_code=404, detail="레저/스포츠 시설을 찾을 수 없습니다.")
    
    if facility_name is not None:
        leisure_sports_item.name = facility_name
    if province is not None:
        leisure_sports_item.province = province
    if region is not None:
        leisure_sports_item.region = region
    if latitude is not None:
        leisure_sports_item.latitude = latitude
    if longitude is not None:
        leisure_sports_item.longitude = longitude
    if image_url is not None:
        leisure_sports_item.image_url = image_url
    
    # amenities 업데이트
    if (amenities is not None or tel is not None or homepage is not None 
        or operating_hours is not None or reservation_info is not None
        or admission_fee is not None or parking_info is not None
        or rental_info is not None or capacity is not None):
        current_amenities = leisure_sports_item.amenities or {}
        if amenities is not None:
            current_amenities.update(amenities)
        if tel is not None:
            current_amenities['tel'] = tel
        if homepage is not None:
            current_amenities['homepage'] = homepage
        if operating_hours is not None:
            current_amenities['operating_hours'] = operating_hours
        if reservation_info is not None:
            current_amenities['reservation_info'] = reservation_info
        if admission_fee is not None:
            current_amenities['admission_fee'] = admission_fee
        if parking_info is not None:
            current_amenities['parking_info'] = parking_info
        if rental_info is not None:
            current_amenities['rental_info'] = rental_info
        if capacity is not None:
            current_amenities['capacity'] = capacity
        leisure_sports_item.amenities = current_amenities
    
    # 태그 업데이트 (sports_type이 제공된 경우)
    if sports_type is not None:
        current_tags = leisure_sports_item.tags or []
        if sports_type not in current_tags:
            current_tags.append(sports_type)
        if '레저' not in current_tags:
            current_tags.append('레저')
        if '스포츠' not in current_tags:
            current_tags.append('스포츠')
        leisure_sports_item.tags = current_tags
    
    # 실내/실외 여부 업데이트
    if facility_name is not None or sports_type is not None:
        leisure_sports_item.is_indoor = _is_indoor_sports(
            facility_name or leisure_sports_item.name, 
            sports_type
        )
    
    db.commit()
    db.refresh(leisure_sports_item)
    return {"content_id": str(leisure_sports_item.destination_id)}


@router.delete("/{content_id}", status_code=204)
def delete_leisure_sports(content_id: str, db: Session = Depends(get_db)):
    """레저/스포츠 시설 삭제"""
    leisure_sports_filter = or_(
        Destination.name.ilike('%골프%'),
        Destination.name.ilike('%스포츠%'),
        Destination.name.ilike('%체육%'),
        Destination.name.ilike('%헬스%'),
        Destination.name.ilike('%수영%'),
        Destination.name.ilike('%테니스%'),
        Destination.name.ilike('%볼링%'),
        Destination.name.ilike('%당구%'),
        Destination.name.ilike('%배드민턴%'),
        Destination.name.ilike('%야구%'),
        Destination.name.ilike('%축구%'),
        Destination.name.ilike('%농구%'),
        Destination.name.ilike('%체육관%'),
        Destination.name.ilike('%운동%'),
        Destination.name.ilike('%레저%'),
        Destination.name.ilike('%리조트%'),
        Destination.name.ilike('%스키%'),
        Destination.name.ilike('%스케이트%'),
        Destination.tags.contains(['스포츠']),
        Destination.tags.contains(['레저']),
        Destination.tags.contains(['골프']),
        Destination.tags.contains(['체육'])
    )
    
    leisure_sports_item = (
        db.query(Destination)
        .filter(Destination.destination_id == content_id)
        .filter(leisure_sports_filter)
        .first()
    )
    if not leisure_sports_item:
        raise HTTPException(status_code=404, detail="레저/스포츠 시설을 찾을 수 없습니다.")
    db.delete(leisure_sports_item)
    db.commit()
    return None


@router.get("/autocomplete/")
def autocomplete_facility_name(q: str = Query(...), db: Session = Depends(get_db)):
    """시설명 자동완성"""
    leisure_sports_filter = or_(
        Destination.name.ilike('%골프%'),
        Destination.name.ilike('%스포츠%'),
        Destination.name.ilike('%체육%'),
        Destination.name.ilike('%헬스%'),
        Destination.name.ilike('%수영%'),
        Destination.name.ilike('%테니스%'),
        Destination.name.ilike('%볼링%'),
        Destination.name.ilike('%당구%'),
        Destination.name.ilike('%배드민턴%'),
        Destination.name.ilike('%야구%'),
        Destination.name.ilike('%축구%'),
        Destination.name.ilike('%농구%'),
        Destination.name.ilike('%체육관%'),
        Destination.name.ilike('%운동%'),
        Destination.name.ilike('%레저%'),
        Destination.name.ilike('%리조트%'),
        Destination.name.ilike('%스키%'),
        Destination.name.ilike('%스케이트%'),
        Destination.tags.contains(['스포츠']),
        Destination.tags.contains(['레저']),
        Destination.tags.contains(['골프']),
        Destination.tags.contains(['체육'])
    )
    
    results = (
        db.query(Destination.name)
        .filter(leisure_sports_filter)
        .filter(Destination.name.ilike(f"%{q}%"))
        .distinct()
        .limit(10)
        .all()
    )
    return [r[0] for r in results]


def _determine_sports_type(name: str) -> str:
    """이름을 기반으로 스포츠 시설 유형 판단"""
    name_lower = name.lower()
    
    if '골프' in name_lower:
        if '스크린' in name_lower:
            return '스크린골프'
        elif '연습' in name_lower:
            return '골프연습장'
        else:
            return '골프장'
    elif '수영' in name_lower:
        return '수영장'
    elif '테니스' in name_lower:
        return '테니스장'
    elif '체육관' in name_lower or '헬스' in name_lower:
        if '헬스' in name_lower:
            return '헬스장'
        else:
            return '체육관'
    elif '볼링' in name_lower:
        return '볼링장'
    elif '당구' in name_lower:
        return '당구장'
    elif '배드민턴' in name_lower:
        return '배드민턴장'
    elif '야구' in name_lower:
        return '야구장'
    elif '축구' in name_lower:
        return '축구장'
    elif '농구' in name_lower:
        return '농구장'
    elif '스키' in name_lower:
        return '스키장'
    elif '스케이트' in name_lower:
        return '스케이트장'
    elif '리조트' in name_lower:
        return '레저리조트'
    elif '스포츠' in name_lower:
        if '센터' in name_lower:
            return '스포츠센터'
        else:
            return '종합스포츠시설'
    else:
        return '기타레저스포츠'


def _is_indoor_sports(name: str, sports_type: str = None) -> bool:
    """스포츠 시설이 실내인지 판단"""
    name_lower = name.lower()
    type_lower = (sports_type or '').lower()
    
    # 실내 스포츠 키워드
    indoor_keywords = [
        '헬스', '볼링', '당구', '체육관', '수영장', '스크린골프',
        '배드민턴', '탁구', '스포츠센터'
    ]
    
    # 실외 스포츠 키워드  
    outdoor_keywords = [
        '골프장', '축구장', '야구장', '테니스장', '스키장'
    ]
    
    # 실내 키워드 확인
    for keyword in indoor_keywords:
        if keyword in name_lower or keyword in type_lower:
            return True
    
    # 실외 키워드 확인
    for keyword in outdoor_keywords:
        if keyword in name_lower or keyword in type_lower:
            return False
    
    # 기본값: 실내로 가정
    return True