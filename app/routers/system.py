from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from app.models import SystemLog
from app.database import get_db, engine
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.services.system_log import log_system_event
from sqlalchemy import text
import requests

router = APIRouter(prefix="/system", tags=["system"])

# 외부 API 헬스체크 함수
def check_external_api_status(url, timeout=3):
    """
    외부 API 상태 확인
    
    Args:
        url: 확인할 API URL
        timeout: 타임아웃 시간 (초)
        
    Returns:
        dict: 상태 정보 (status, response_time)
    """
    try:
        import time
        start_time = time.time()
        resp = requests.head(url, timeout=timeout)
        response_time = round((time.time() - start_time) * 1000, 2)  # ms
        
        if resp.status_code < 400:
            return {"status": "정상", "response_time": f"{response_time}ms"}
        else:
            return {"status": f"오류({resp.status_code})", "response_time": f"{response_time}ms"}
    except requests.exceptions.Timeout:
        return {"status": "타임아웃", "response_time": "-"}
    except Exception as e:
        return {"status": "연결실패", "response_time": "-"}

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

# 서비스 상태 확인 API (하드웨어 모니터링 제거, 서비스 의존성 중심으로 변경)
@router.get("/status")
async def get_service_status():
    """
    서비스 상태 조회
    
    - 데이터베이스 연결 상태
    - 외부 API 의존성 상태
    """
    from app.config import settings
    import time
    
    # 데이터베이스 연결 상태 확인
    db_status = {"status": "연결됨", "response_time": "-"}
    try:
        start_time = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        response_time = round((time.time() - start_time) * 1000, 2)
        db_status = {"status": "연결됨", "response_time": f"{response_time}ms"}
    except Exception as e:
        db_status = {"status": "연결실패", "response_time": "-"}

    # 외부 API 의존성 상태 확인
    external_apis = {
        "weather_api": check_external_api_status(settings.weather_api_url),
        "tourism_api": check_external_api_status(settings.korea_tourism_api_url),
        "google_places": check_external_api_status(settings.google_places_url)
    }
    
    # 전체 서비스 상태 판단
    service_healthy = (
        db_status["status"] == "연결됨" and
        all(api["status"] in ["정상", "타임아웃"] for api in external_apis.values())
    )
    
    return {
        "service_status": "정상" if service_healthy else "문제발생",
        "database": db_status,
        "external_apis": external_apis,
        "timestamp": datetime.now().isoformat()
    }
