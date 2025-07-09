from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.models import LeisureSports, LeisureSportsResponse
from app.database import get_db
from pydantic import BaseModel

router = APIRouter(prefix="/api/leisure-sports", tags=["leisure_sports"])

class LeisureSportsCreate(BaseModel):
    region_code: str
    facility_name: str
    category_code: Optional[str] = None
    sub_category_code: Optional[str] = None
    raw_data_id: Optional[str] = None
    sports_type: Optional[str] = None
    reservation_info: Optional[str] = None
    admission_fee: Optional[str] = None
    parking_info: Optional[str] = None
    rental_info: Optional[str] = None
    capacity: Optional[str] = None
    operating_hours: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tel: Optional[str] = None
    homepage: Optional[str] = None
    overview: Optional[str] = None
    first_image: Optional[str] = None
    first_image_small: Optional[str] = None
    data_quality_score: Optional[float] = None
    processing_status: Optional[str] = None
    booktour: Optional[str] = None
    createdtime: Optional[str] = None
    modifiedtime: Optional[str] = None
    telname: Optional[str] = None
    faxno: Optional[str] = None
    mlevel: Optional[int] = None
    detail_intro_info: Optional[dict] = None
    detail_additional_info: Optional[dict] = None
    sigungu_code: Optional[str] = None
    last_sync_at: Optional[str] = None

class LeisureSportsUpdate(LeisureSportsCreate):
    pass

class LeisureSportsListResponse(BaseModel):
    items: list[LeisureSportsResponse]
    total: int

@router.get("/", response_model=LeisureSportsListResponse)
def list_leisure_sports(
    skip: int = 0,
    limit: int = 50,
    region_code: str = Query(None),
    facility_name: str = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(LeisureSports)
    if region_code:
        query = query.filter(LeisureSports.region_code == region_code)
    if facility_name:
        query = query.filter(LeisureSports.facility_name.ilike(f"%{facility_name}%"))
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"items": items, "total": total}

@router.get("/{content_id}", response_model=LeisureSportsResponse)
def get_leisure_sports(content_id: str, db: Session = Depends(get_db)):
    item = db.query(LeisureSports).filter(LeisureSports.content_id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Leisure sports not found")
    return item

@router.post("/", response_model=LeisureSportsResponse, status_code=status.HTTP_201_CREATED)
def create_leisure_sports(item: LeisureSportsCreate, db: Session = Depends(get_db)):
    db_item = LeisureSports(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/{content_id}", response_model=LeisureSportsResponse)
def update_leisure_sports(content_id: str, item: LeisureSportsUpdate, db: Session = Depends(get_db)):
    db_item = db.query(LeisureSports).filter(LeisureSports.content_id == content_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Leisure sports not found")
    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_leisure_sports(content_id: str, db: Session = Depends(get_db)):
    db_item = db.query(LeisureSports).filter(LeisureSports.content_id == content_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Leisure sports not found")
    db.delete(db_item)
    db.commit()
    return None

@router.get("/autocomplete/", response_model=list[str])
def autocomplete_facility_name(q: str = Query(...), db: Session = Depends(get_db)):
    results = (
        db.query(LeisureSports.facility_name)
        .filter(LeisureSports.facility_name.ilike(f"%{q}%"))
        .distinct()
        .limit(10)
        .all()
    )
    return [r[0] for r in results]
