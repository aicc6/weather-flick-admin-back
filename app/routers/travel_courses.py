from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import TravelCourse
from uuid import uuid4
from typing import Any
from pydantic import BaseModel
from datetime import datetime

def safe_float(val: Any) -> float | None:
    try:
        return float(val)
    except Exception:
        return None

class TravelCourseResponse(BaseModel):
    content_id: str
    region_code: str
    sigungu_code: str | None = None
    course_name: str
    category_code: str | None = None
    sub_category_code: str | None = None
    address: str | None = None
    detail_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    zipcode: str | None = None
    tel: str | None = None
    homepage: str | None = None
    overview: str | None = None
    first_image: str | None = None
    first_image_small: str | None = None
    course_theme: str | None = None
    course_distance: str | None = None
    required_time: str | None = None
    difficulty_level: str | None = None
    schedule: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    raw_data_id: str | None = None
    last_sync_at: datetime | None = None
    data_quality_score: float | None = None
    processing_status: str | None = None
    booktour: str | None = None
    createdtime: str | None = None
    modifiedtime: str | None = None
    telname: str | None = None
    faxno: str | None = None
    mlevel: int | None = None
    detail_intro_info: dict | None = None
    detail_additional_info: dict | None = None

    class Config:
        orm_mode = True

router = APIRouter(prefix="/travel-courses", tags=["Travel Courses"])

@router.get("/")
def get_all_travel_courses(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    course_name: str = Query(None),
    region: str = Query(None)
):
    query = db.query(TravelCourse)
    if course_name:
        query = query.filter(TravelCourse.course_name.ilike(f"%{course_name}%"))
    if region:
        query = query.filter(TravelCourse.region_code == region)
    total = query.count()
    courses = query.order_by(TravelCourse.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "content_id": c.content_id,
                "region_code": c.region_code,
                "sigungu_code": c.sigungu_code,
                "course_name": c.course_name,
                "category_code": c.category_code,
                "sub_category_code": c.sub_category_code,
                "address": c.address,
                "detail_address": c.detail_address,
                "latitude": safe_float(getattr(c, 'latitude', None)),
                "longitude": safe_float(getattr(c, 'longitude', None)),
                "zipcode": c.zipcode,
                "tel": c.tel,
                "homepage": c.homepage,
                "overview": c.overview,
                "first_image": c.first_image,
                "first_image_small": c.first_image_small,
                "course_theme": c.course_theme,
                "course_distance": c.course_distance,
                "required_time": c.required_time,
                "difficulty_level": c.difficulty_level,
                "schedule": c.schedule,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "raw_data_id": str(getattr(c, 'raw_data_id', None)) if getattr(c, 'raw_data_id', None) is not None else None,
                "last_sync_at": c.last_sync_at,
                "data_quality_score": safe_float(getattr(c, 'data_quality_score', None)),
                "processing_status": c.processing_status,
                "booktour": c.booktour,
                "createdtime": c.createdtime,
                "modifiedtime": c.modifiedtime,
                "telname": c.telname,
                "faxno": c.faxno,
                "mlevel": c.mlevel,
                "detail_intro_info": c.detail_intro_info,
                "detail_additional_info": c.detail_additional_info,
            }
            for c in courses
        ]
    }

@router.get("/region-count")
def get_region_count(db: Session = Depends(get_db)):
    regions = db.query(TravelCourse.region_code).distinct().all()
    # regions is a list of tuples like [(1,), (2,), ...]
    return {"region_count": len(regions)}

@router.get("/{content_id}", response_model=TravelCourseResponse)
def get_travel_course(content_id: str, db: Session = Depends(get_db)):
    c = db.query(TravelCourse).filter(TravelCourse.content_id == content_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다.")
    return c

@router.post("/", status_code=201)
def create_travel_course(
    course: dict[str, object] = Body(...),
    db: Session = Depends(get_db)
):
    course['content_id'] = course.get('content_id') or str(uuid4())[:20]
    new_course = TravelCourse(**course)
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return {"content_id": new_course.content_id}

@router.put("/{content_id}")
def update_travel_course(
    content_id: str,
    course: dict[str, object] = Body(...),
    db: Session = Depends(get_db)
):
    c = db.query(TravelCourse).filter(TravelCourse.content_id == content_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다.")
    for key, value in course.items():  # type: ignore
        if hasattr(c, key) and value is not None:
            setattr(c, key, value)
    db.commit()
    db.refresh(c)
    return {"content_id": c.content_id}

@router.delete("/{content_id}", status_code=204)
def delete_travel_course(content_id: str, db: Session = Depends(get_db)):
    c = db.query(TravelCourse).filter(TravelCourse.content_id == content_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다.")
    db.delete(c)
    db.commit()
    return None
