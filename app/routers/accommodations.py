"""
숙박시설 관리 API 라우터
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.database import get_db
from app.models import Accommodation
from app.schemas.accommodation_schemas import (
    AccommodationResponse,
    AccommodationCreate,
    AccommodationUpdate,
    AccommodationListResponse
)
from app.auth import get_current_admin

router = APIRouter(prefix="/accommodations", tags=["Accommodations"])


@router.get("/", response_model=AccommodationListResponse)
async def get_accommodations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    accommodation_name: Optional[str] = None,
    region_code: Optional[str] = None,
    accommodation_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """숙박시설 목록 조회"""
    query = db.query(Accommodation)
    
    # 필터링
    if accommodation_name:
        query = query.filter(Accommodation.accommodation_name.ilike(f"%{accommodation_name}%"))
    if region_code and region_code != "all":
        query = query.filter(Accommodation.region_code == region_code)
    if accommodation_type:
        query = query.filter(Accommodation.accommodation_type == accommodation_type)
    
    # 전체 개수
    total = query.count()
    
    # 페이지네이션
    accommodations = query.order_by(desc(Accommodation.created_at)).offset(skip).limit(limit).all()
    
    return AccommodationListResponse(
        items=accommodations,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{content_id}", response_model=AccommodationResponse)
async def get_accommodation(
    content_id: str,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """숙박시설 상세 조회"""
    accommodation = db.query(Accommodation).filter(Accommodation.content_id == content_id).first()
    if not accommodation:
        raise HTTPException(status_code=404, detail="숙박시설을 찾을 수 없습니다.")
    return accommodation


@router.post("/", response_model=AccommodationResponse)
async def create_accommodation(
    accommodation: AccommodationCreate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """숙박시설 생성"""
    # 중복 확인
    existing = db.query(Accommodation).filter(
        Accommodation.accommodation_name == accommodation.accommodation_name,
        Accommodation.region_code == accommodation.region_code
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="동일한 지역에 같은 이름의 숙박시설이 이미 존재합니다."
        )
    
    # content_id 생성 (임시로 timestamp 기반)
    import time
    content_id = f"ACC{int(time.time())}"
    
    db_accommodation = Accommodation(
        content_id=content_id,
        **accommodation.dict()
    )
    
    db.add(db_accommodation)
    db.commit()
    db.refresh(db_accommodation)
    
    return db_accommodation


@router.put("/{content_id}", response_model=AccommodationResponse)
async def update_accommodation(
    content_id: str,
    accommodation: AccommodationUpdate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """숙박시설 수정"""
    db_accommodation = db.query(Accommodation).filter(Accommodation.content_id == content_id).first()
    if not db_accommodation:
        raise HTTPException(status_code=404, detail="숙박시설을 찾을 수 없습니다.")
    
    # 업데이트
    update_data = accommodation.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_accommodation, field, value)
    
    db.commit()
    db.refresh(db_accommodation)
    
    return db_accommodation


@router.delete("/{content_id}")
async def delete_accommodation(
    content_id: str,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """숙박시설 삭제"""
    accommodation = db.query(Accommodation).filter(Accommodation.content_id == content_id).first()
    if not accommodation:
        raise HTTPException(status_code=404, detail="숙박시설을 찾을 수 없습니다.")
    
    db.delete(accommodation)
    db.commit()
    
    return {"message": "숙박시설이 삭제되었습니다."}


@router.get("/types/list")
async def get_accommodation_types(
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """숙박시설 유형 목록 조회"""
    # 한국관광공사 표준 숙박시설 유형
    types = [
        {"code": "B0201", "name": "관광호텔"},
        {"code": "B0202", "name": "수상관광호텔"},
        {"code": "B0203", "name": "전통호텔"},
        {"code": "B0204", "name": "가족호텔"},
        {"code": "B0205", "name": "호스텔"},
        {"code": "B0206", "name": "여관"},
        {"code": "B0207", "name": "모텔"},
        {"code": "B0208", "name": "민박"},
        {"code": "B0209", "name": "게스트하우스"},
        {"code": "B0210", "name": "홈스테이"},
        {"code": "B0211", "name": "서비스드레지던스"},
        {"code": "B0212", "name": "의료관광호텔"},
        {"code": "B0213", "name": "소형호텔"},
        {"code": "B0214", "name": "펜션"},
        {"code": "B0215", "name": "콘도미니엄"},
        {"code": "B0216", "name": "유스호스텔"},
        {"code": "B0217", "name": "야영장"},
        {"code": "B0218", "name": "한옥"}
    ]
    
    return types