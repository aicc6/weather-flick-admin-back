from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from app.models import FestivalEvent, FestivalEventResponse
from app.database import get_db
from datetime import date
from pydantic import BaseModel

router = APIRouter(prefix="/api/festivals-events", tags=["festivals_events"])

class FestivalEventCreate(BaseModel):
    region_code: str
    raw_data_id: Optional[str] = None
    event_name: str
    category_code: Optional[str] = None
    event_start_date: Optional[date] = None
    event_end_date: Optional[date] = None
    event_place: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tel: Optional[str] = None
    homepage: Optional[str] = None
    event_program: Optional[str] = None
    sponsor: Optional[str] = None
    organizer: Optional[str] = None
    play_time: Optional[str] = None
    age_limit: Optional[str] = None
    cost_info: Optional[str] = None
    discount_info: Optional[str] = None
    description: Optional[str] = None
    overview: Optional[str] = None
    first_image: Optional[str] = None
    first_image_small: Optional[str] = None
    booktour: Optional[str] = None
    createdtime: Optional[str] = None
    modifiedtime: Optional[str] = None
    telname: Optional[str] = None
    faxno: Optional[str] = None
    mlevel: Optional[int] = None
    detail_intro_info: Optional[dict[str, Any]] = None
    detail_additional_info: Optional[dict[str, Any]] = None
    data_quality_score: Optional[float] = None
    processing_status: Optional[str] = None
    last_sync_at: Optional[str] = None

class FestivalEventUpdate(FestivalEventCreate):
    pass

class FestivalEventListResponse(BaseModel):
    items: list[FestivalEventResponse]
    total: int

@router.get("/", response_model=FestivalEventListResponse)
def list_festival_events(
    skip: int = 0,
    limit: int = 50,
    region_code: str = Query(None),
    event_name: str = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(FestivalEvent)
    if region_code:
        query = query.filter(FestivalEvent.region_code == region_code)
    if event_name:
        query = query.filter(FestivalEvent.event_name.ilike(f"%{event_name}%"))
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"items": items, "total": total}

@router.get("/autocomplete/", response_model=list[str])
def autocomplete_event_name(q: str = Query(...), db: Session = Depends(get_db)):
    results = (
        db.query(FestivalEvent.event_name)
        .filter(FestivalEvent.event_name.ilike(f"%{q}%"))
        .distinct()
        .limit(10)
        .all()
    )
    return [r[0] for r in results]

@router.get("/{content_id}", response_model=FestivalEventResponse)
def get_festival_event(content_id: str, db: Session = Depends(get_db)):
    event = db.query(FestivalEvent).filter(FestivalEvent.content_id == content_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Festival event not found")
    return event

@router.post("/", response_model=FestivalEventResponse, status_code=status.HTTP_201_CREATED)
def create_festival_event(event: FestivalEventCreate, db: Session = Depends(get_db)):
    db_event = FestivalEvent(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@router.put("/{content_id}", response_model=FestivalEventResponse)
def update_festival_event(content_id: str, event: FestivalEventUpdate, db: Session = Depends(get_db)):
    db_event = db.query(FestivalEvent).filter(FestivalEvent.content_id == content_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Festival event not found")
    for key, value in event.model_dump(exclude_unset=True).items():
        setattr(db_event, key, value)
    db.commit()
    db.refresh(db_event)
    return db_event

@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_festival_event(content_id: str, db: Session = Depends(get_db)):
    db_event = db.query(FestivalEvent).filter(FestivalEvent.content_id == content_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Festival event not found")
    db.delete(db_event)
    db.commit()
    return None
