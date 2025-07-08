from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import TravelCourse
from uuid import uuid4

router = APIRouter(prefix="/travel-courses", tags=["Travel Courses"])

@router.get("/")
def get_all_travel_courses(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    total = db.query(TravelCourse).count()
    courses = db.query(TravelCourse).order_by(TravelCourse.created_at.desc()).offset(offset).limit(limit).all()
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
                "latitude": float(c.latitude) if c.latitude else None,
                "longitude": float(c.longitude) if c.longitude else None,
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
                "raw_data_id": str(c.raw_data_id) if c.raw_data_id else None,
                "last_sync_at": c.last_sync_at,
                "data_quality_score": float(c.data_quality_score) if c.data_quality_score else None,
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

@router.get("/{content_id}")
def get_travel_course(content_id: str, db: Session = Depends(get_db)):
    c = db.query(TravelCourse).filter(TravelCourse.content_id == content_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다.")
    return c.__dict__

@router.post("/", status_code=201)
def create_travel_course(
    course: dict = Body(...),
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
    course: dict = Body(...),
    db: Session = Depends(get_db)
):
    c = db.query(TravelCourse).filter(TravelCourse.content_id == content_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다.")
    for key, value in course.items():
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
