from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from app.models import SystemLog
from app.database import get_db
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.services.system_log import log_system_event
import psutil
import time
from sqlalchemy import text
from app.database import engine
import requests
from collections import deque

router = APIRouter(prefix="/system", tags=["system"])

# 서버 시작 시간 기록
start_time = time.time()

# 최근 에러 기록 (메모리, 최대 1000개)
ERROR_LOG = deque(maxlen=1000)

# 외부 API 헬스체크 함수
def check_api_health(url, headers=None):
    try:
        resp = requests.head(url, timeout=3, headers=headers)
        if resp.status_code < 400:
            return '정상'
        return f'오류({resp.status_code})'
    except Exception as e:
        return '점검중'

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

# 시스템 리소스 상태 API (main.py에서 이동)
@router.get("/status")
async def get_system_status():
    """시스템 상태 조회"""
    from app.config import settings
    
    # 서버 리소스
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent

    # DB 상태
    db_status = "연결됨"
    db_response = "-"
    try:
        t0 = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_response = f"{(time.time() - t0) * 1000:.0f}ms"
    except Exception as e:
        db_status = "끊김"
        db_response = "-"
        ERROR_LOG.append(time.time())

    # 서버 상태/업타임
    uptime_seconds = time.time() - start_time
    uptime_hours = uptime_seconds // 3600
    uptime_str = f"{int(uptime_hours)}시간 {int((uptime_seconds%3600)//60)}분"
    server_status = "정상"

    # API 성능 (샘플: DB 응답시간 사용)
    avg_response = db_response if db_response != '-' else "-"

    # 외부 API 상태
    external = {
        "weather": check_api_health(settings.weather_api_url),
        "tour": check_api_health(settings.korea_tourism_api_url),
        "map": check_api_health(settings.google_places_url),
        "payment": check_api_health("https://api.iamport.kr/")
    }

    # 에러율 (최근 24시간 내 에러 비율, 샘플: 전체 요청수 대신 10000으로 가정)
    now = time.time()
    error_24h = [t for t in ERROR_LOG if now - t < 86400]
    error_rate = f"{len(error_24h)/10000*100:.2f}%" if error_24h else "0.00%"

    return {
        "server": {"status": server_status, "uptime": uptime_str},
        "db": {"status": db_status, "response": db_response},
        "api": {"avgResponse": avg_response},
        "error": {"rate": error_rate},
        "resource": {"cpu": cpu, "memory": memory, "disk": disk},
        "external": external,
    }
