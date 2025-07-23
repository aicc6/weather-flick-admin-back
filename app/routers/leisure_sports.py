from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentAdmin, require_permission
from app.models import LeisureSport, Region
from app.schemas.leisure_sport_schemas import (
    LeisureSportCreate,
    LeisureSportListResponse,
    LeisureSportResponse,
    LeisureSportUpdate,
)

router = APIRouter(prefix="/leisure-sports", tags=["leisure_sports"])


@router.get("/")
@require_permission("content.read")
async def list_leisure_sports(
    current_admin: CurrentAdmin,
    skip: int = 0,
    limit: int = 50,
    region_code: str = Query(None),
    facility_name: str = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(LeisureSport)
    if region_code:
        # region_code 파라미터를 받으면 해당 지역의 레저스포츠 필터링
        # 프론트엔드에서 '1', '2', '3' 등을 보내면 DB의 '01', '02', '03' 형식과 매칭
        if len(region_code) == 1 and region_code.isdigit():
            # 한 자리 숫자인 경우 앞에 0을 붙여서 검색
            padded_code = region_code.zfill(2)
            # 시도 레벨과 시군구 레벨 모두 검색 (예: '01'로 시작하는 모든 region_code)
            query = query.filter(LeisureSport.region_code.like(f"{padded_code}%"))
        else:
            # 그 외의 경우 그대로 검색
            query = query.filter(LeisureSport.region_code == region_code)
    if facility_name:
        query = query.filter(LeisureSport.facility_name.ilike(f"%{facility_name}%"))
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    # 지역명 조회를 위한 region_codes 수집
    region_codes = list(set([item.region_code for item in items if item.region_code]))
    region_names = {}
    if region_codes:
        regions = db.query(Region).filter(Region.region_code.in_(region_codes)).all()
        region_names = {r.region_code: r.region_name for r in regions}
    
    # 각 아이템을 딕셔너리로 변환하고 region_name 추가
    result_items = []
    for item in items:
        item_dict = {
            "content_id": item.content_id,
            "facility_name": item.facility_name,
            "facility_type": getattr(item, 'facility_type', None),
            "region_code": item.region_code,
            "region_name": region_names.get(item.region_code, ""),
            "address": item.address,
            "tel": item.tel,
            "latitude": item.latitude,
            "longitude": item.longitude,
            "sports_type": item.sports_type,
            "admission_fee": item.admission_fee,
            "parking_info": item.parking_info,
            "operating_hours": item.operating_hours,
            "created_at": item.created_at,
            "updated_at": item.updated_at
        }
        result_items.append(item_dict)
    
    return {"items": result_items, "total": total}


@router.get("/{content_id}", response_model=LeisureSportResponse)
@require_permission("content.read")
async def get_leisure_sports(
    content_id: str, current_admin: CurrentAdmin, db: Session = Depends(get_db)
):
    item = db.query(LeisureSport).filter(LeisureSport.content_id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Leisure sports not found")
    return item


@router.post(
    "/", response_model=LeisureSportResponse, status_code=status.HTTP_201_CREATED
)
@require_permission("content.write")
async def create_leisure_sports(
    item: LeisureSportCreate, current_admin: CurrentAdmin, db: Session = Depends(get_db)
):
    # content_id 생성
    import uuid
    content_id = str(uuid.uuid4())[:20]  # 20자리로 제한
    
    db_item = LeisureSport(content_id=content_id, **item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{content_id}", response_model=LeisureSportResponse)
@require_permission("content.write")
async def update_leisure_sports(
    content_id: str,
    item: LeisureSportUpdate,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db),
):
    db_item = (
        db.query(LeisureSport).filter(LeisureSport.content_id == content_id).first()
    )
    if not db_item:
        raise HTTPException(status_code=404, detail="Leisure sports not found")
    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("content.delete")
async def delete_leisure_sports(
    content_id: str, current_admin: CurrentAdmin, db: Session = Depends(get_db)
):
    db_item = (
        db.query(LeisureSport).filter(LeisureSport.content_id == content_id).first()
    )
    if not db_item:
        raise HTTPException(status_code=404, detail="Leisure sports not found")
    db.delete(db_item)
    db.commit()
    return None


@router.get("/autocomplete/", response_model=list[str])
@require_permission("content.read")
async def autocomplete_facility_name(
    current_admin: CurrentAdmin, q: str = Query(...), db: Session = Depends(get_db)
):
    results = (
        db.query(LeisureSport.facility_name)
        .filter(LeisureSport.facility_name.ilike(f"%{q}%"))
        .distinct()
        .limit(10)
        .all()
    )
    return [r[0] for r in results]
