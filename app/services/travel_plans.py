from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from app.models import TravelPlan
from app.schemas.travel_plan_schemas import TravelPlanCreate, TravelPlanUpdate

# 목록 조회

def get_travel_plans(db: Session, skip: int = 0, limit: int = 20):
    return db.query(TravelPlan).order_by(TravelPlan.created_at.desc()).offset(skip).limit(limit).all()

# 단건 조회

def get_travel_plan(db: Session, plan_id):
    return db.query(TravelPlan).filter(TravelPlan.plan_id == plan_id).first()

# 생성

def create_travel_plan(db: Session, travel_plan: TravelPlanCreate, user_id):
    db_plan = TravelPlan(**travel_plan.dict(), user_id=user_id)
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan

# 수정

def update_travel_plan(db: Session, plan_id, plan_update: TravelPlanUpdate):
    db_plan = db.query(TravelPlan).filter(TravelPlan.plan_id == plan_id).first()
    if not db_plan:
        raise NoResultFound
    for k, v in plan_update.dict(exclude_unset=True).items():
        setattr(db_plan, k, v)
    db.commit()
    db.refresh(db_plan)
    return db_plan

# 삭제

def delete_travel_plan(db: Session, plan_id):
    db_plan = db.query(TravelPlan).filter(TravelPlan.plan_id == plan_id).first()
    if not db_plan:
        raise NoResultFound
    db.delete(db_plan)
    db.commit()
    return db_plan
