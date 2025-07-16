from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FestivalEvent, Region
from app.schemas.festival_event_schemas import FestivalEventResponse
from app.dependencies import CurrentAdmin, require_permission

router = APIRouter(prefix="/festivals-events", tags=["festivals_events"])

class FestivalEventCreate(BaseModel):
    region_code: str
    raw_data_id: str | None = None
    event_name: str
    category_code: str | None = None
    event_start_date: date | None = None
    event_end_date: date | None = None
    event_place: str | None = None
    address: str | None = None
    detail_address: str | None = None
    zipcode: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    tel: str | None = None
    homepage: str | None = None
    event_program: str | None = None
    sponsor: str | None = None
    organizer: str | None = None
    play_time: str | None = None
    age_limit: str | None = None
    cost_info: str | None = None
    discount_info: str | None = None
    description: str | None = None
    overview: str | None = None
    first_image: str | None = None
    first_image_small: str | None = None
    booktour: str | None = None
    createdtime: str | None = None
    modifiedtime: str | None = None
    telname: str | None = None
    faxno: str | None = None
    mlevel: int | None = None
    detail_intro_info: dict[str, Any] | None = None
    detail_additional_info: dict[str, Any] | None = None
    data_quality_score: float | None = None
    processing_status: str | None = None
    last_sync_at: str | None = None

class FestivalEventUpdate(FestivalEventCreate):
    pass

class FestivalEventListResponse(BaseModel):
    items: list[FestivalEventResponse]
    total: int

@router.get("/", response_model=FestivalEventListResponse)
@require_permission("content.read")
async def list_festival_events(
    current_admin: CurrentAdmin,
    skip: int = 0,
    limit: int = 50,
    region_code: str = Query(None),
    event_name: str = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(FestivalEvent)
    if region_code:
        # region_code 파라미터를 받으면 해당 지역의 tour_api_area_code를 찾아서 필터링
        region = db.query(Region).filter(Region.region_code == region_code).first()
        if region and region.tour_api_area_code:
            query = query.filter(FestivalEvent.region_code == region.tour_api_area_code)
        else:
            query = query.filter(FestivalEvent.region_code == region_code)
    if event_name:
        query = query.filter(FestivalEvent.event_name.ilike(f"%{event_name}%"))
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"items": items, "total": total}

@router.get("/autocomplete/", response_model=list[str])
@require_permission("content.read")
async def autocomplete_event_name(
    current_admin: CurrentAdmin,
    q: str = Query(...),
    db: Session = Depends(get_db)
):
    results = (
        db.query(FestivalEvent.event_name)
        .filter(FestivalEvent.event_name.ilike(f"%{q}%"))
        .distinct()
        .limit(10)
        .all()
    )
    return [r[0] for r in results]

@router.get("/{content_id}", response_model=FestivalEventResponse)
@require_permission("content.read")
async def get_festival_event(
    content_id: str,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    event = db.query(FestivalEvent).filter(FestivalEvent.content_id == content_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Festival event not found")
    return event

@router.post("/", response_model=FestivalEventResponse, status_code=status.HTTP_201_CREATED)
@require_permission("content.write")
async def create_festival_event(
    event: FestivalEventCreate,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    db_event = FestivalEvent(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@router.put("/{content_id}", response_model=FestivalEventResponse)
@require_permission("content.write")
async def update_festival_event(
    content_id: str,
    event: FestivalEventUpdate,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    db_event = db.query(FestivalEvent).filter(FestivalEvent.content_id == content_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Festival event not found")
    for key, value in event.model_dump(exclude_unset=True).items():
        setattr(db_event, key, value)
    db.commit()
    db.refresh(db_event)
    return db_event

@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("content.delete")
async def delete_festival_event(
    content_id: str,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    db_event = db.query(FestivalEvent).filter(FestivalEvent.content_id == content_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Festival event not found")
    db.delete(db_event)
    db.commit()
    return None
