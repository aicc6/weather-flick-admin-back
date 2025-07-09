from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import TravelPlanCreate, TravelPlanUpdate, TravelPlanResponse
from app.services import travel_plans as service
from typing import List
from uuid import UUID
import json

router = APIRouter(prefix="/travel-plans", tags=["travel_plans"])

@router.get("/", response_model=List[TravelPlanResponse])
def list_travel_plans(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    plans = service.get_travel_plans(db, skip=skip, limit=limit)
    result = []
    for plan in plans:
        # itinerary가 str이면 dict로 변환
        if isinstance(plan.itinerary, str):
            try:
                plan.itinerary = json.loads(plan.itinerary)
            except Exception:
                plan.itinerary = None
        result.append(TravelPlanResponse.model_validate(plan))
    return result

@router.get("/{plan_id}", response_model=TravelPlanResponse)
def get_travel_plan(plan_id: UUID, db: Session = Depends(get_db)):
    plan = service.get_travel_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found")
    if isinstance(plan.itinerary, str):
        try:
            plan.itinerary = json.loads(plan.itinerary)
        except Exception:
            plan.itinerary = None
    return TravelPlanResponse.model_validate(plan)

@router.post("/", response_model=TravelPlanResponse, status_code=status.HTTP_201_CREATED)
def create_travel_plan(travel_plan: TravelPlanCreate, db: Session = Depends(get_db)):
    # user_id는 인증에서 받아야 하지만, 데모용으로 임시 user_id 사용
    user_id = travel_plan.user_id if hasattr(travel_plan, 'user_id') else None
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    return service.create_travel_plan(db, travel_plan, user_id)

@router.put("/{plan_id}", response_model=TravelPlanResponse)
def update_travel_plan(plan_id: UUID, plan_update: TravelPlanUpdate, db: Session = Depends(get_db)):
    try:
        return service.update_travel_plan(db, plan_id, plan_update)
    except Exception:
        raise HTTPException(status_code=404, detail="Travel plan not found")

@router.delete("/{plan_id}", response_model=TravelPlanResponse)
def delete_travel_plan(plan_id: UUID, db: Session = Depends(get_db)):
    try:
        return service.delete_travel_plan(db, plan_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Travel plan not found")
