from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from app.models import SystemLog
from app.database import get_db
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.services.system_log import log_system_event

router = APIRouter(prefix="/system", tags=["system"])

class SystemLogOut(BaseModel):
    log_id: int
    level: str
    source: str
    message: str
    context: Optional[dict]
    created_at: datetime

    class Config:
        orm_mode = True

@router.get("/logs", response_model=List[SystemLogOut])
def get_system_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    level: Optional[str] = None,
    source: Optional[str] = None,
    message: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(SystemLog)
    if level:
        query = query.filter(SystemLog.level == level)
    if source:
        query = query.filter(SystemLog.source == source)
    if message:
        query = query.filter(SystemLog.message.ilike(f"%{message}%"))
    query = query.order_by(SystemLog.created_at.desc())
    logs = query.offset((page - 1) * size).limit(size).all()
    return logs

@router.post("/logs/test")
def test_log(
    message: str = Body(...),
    level: str = Body('INFO'),
    source: str = Body(None),
    context: dict = Body(None),
    db: Session = Depends(get_db),
):
    log = log_system_event(level=level, message=message, source=source, context=context, db=db)
    return {"log_id": log.log_id, "level": log.level, "source": log.source, "message": log.message, "created_at": log.created_at}
