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


@router.get("/", response_model=LeisureSportListResponse)
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
        # region_code 파라미터를 받으면 해당 지역의 tour_api_area_code를 찾아서 필터링
        region = db.query(Region).filter(Region.region_code == region_code).first()
        if region and region.tour_api_area_code:
            query = query.filter(LeisureSport.region_code == region.tour_api_area_code)
        else:
            query = query.filter(LeisureSport.region_code == region_code)
    if facility_name:
        query = query.filter(LeisureSport.facility_name.ilike(f"%{facility_name}%"))
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"items": items, "total": total}


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
    db_item = LeisureSport(**item.model_dump())
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
