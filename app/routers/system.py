from datetime import datetime
from typing import Any

import requests
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.models import SystemLog
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.system import (
    DatabaseStatus,
    ExternalApisStatus,
    ExternalApiStatus,
    SystemLogTestRequest,
    SystemLogTestResponse,
    SystemStatusData,
)
from app.services.system_log import log_system_event

router = APIRouter(prefix="/system", tags=["system"])

# 외부 API 헬스체크 함수
def check_external_api_status(url, timeout=3, method="HEAD", health_endpoint=None):
    """
    외부 API 상태 확인
    
    Args:
        url: 확인할 API URL
        timeout: 타임아웃 시간 (초)
        method: HTTP 메소드 (HEAD 또는 GET)
        health_endpoint: 헬스체크 엔드포인트 경로
        
    Returns:
        dict: 상태 정보 (status, response_time)
    """
    try:
        import time
        start_time = time.time()
        
        # 헬스체크 엔드포인트가 지정된 경우 사용
        check_url = url + health_endpoint if health_endpoint else url
        
        if method == "GET":
            resp = requests.get(check_url, timeout=timeout)
        else:
            resp = requests.head(check_url, timeout=timeout)
            
        response_time = round((time.time() - start_time) * 1000, 2)  # ms

        if resp.status_code < 400:
            return {"status": "정상", "response_time": f"{response_time}ms"}
        else:
            return {"status": f"오류({resp.status_code})", "response_time": f"{response_time}ms"}
    except requests.exceptions.Timeout:
        return {"status": "타임아웃", "response_time": "-"}
    except Exception:
        return {"status": "연결실패", "response_time": "-"}


@router.get("/logs")
def get_system_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    level: str = Query(None),
    source: str = Query(None),
    message: str = Query(None),
    db: Session = Depends(get_db),
):
    """시스템 로그 목록 조회"""
    query = db.query(SystemLog)
    if level:
        query = query.filter(SystemLog.level == level)
    if source:
        query = query.filter(SystemLog.source == source)
    if message:
        query = query.filter(SystemLog.message.ilike(f"%{message}%"))

    total = query.count()
    query = query.order_by(SystemLog.created_at.desc())
    logs = query.offset((page - 1) * size).limit(size).all()

    # SystemLog 객체를 딕셔너리로 변환
    log_items = []
    for log in logs:
        log_items.append({
            "log_id": log.log_id,
            "level": log.level,
            "source": log.source,
            "message": log.message,
            "context": log.context,
            "created_at": log.created_at
        })

    return PaginatedResponse(
        items=log_items,
        total=total,
        page=page,
        size=size,
        message="시스템 로그를 성공적으로 조회했습니다."
    )

@router.post("/logs/test", response_model=SuccessResponse[SystemLogTestResponse])
def test_log(
    request: SystemLogTestRequest,
    db: Session = Depends(get_db),
):
    """시스템 로그 테스트 생성"""
    log = log_system_event(
        level=request.level,
        message=request.message,
        source=request.source,
        context=request.context,
        db=db
    )

    response_data = SystemLogTestResponse(
        log_id=log.log_id,
        level=log.level,
        source=log.source,
        message=log.message,
        created_at=log.created_at
    )

    return SuccessResponse(
        data=response_data,
        message="테스트 로그가 성공적으로 생성되었습니다."
    )

# 서비스 상태 확인 API (하드웨어 모니터링 제거, 서비스 의존성 중심으로 변경)
@router.get("/status", response_model=Any)
async def get_service_status():
    """
    서비스 상태 조회
    
    - 데이터베이스 연결 상태
    - 외부 API 의존성 상태
    """
    try:
        import time

        from app.config import settings

        # 데이터베이스 연결 상태 확인
        db_status_dict = {"status": "연결됨", "response_time": "-"}
        try:
            start_time = time.time()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            response_time = round((time.time() - start_time) * 1000, 2)
            db_status_dict = {"status": "연결됨", "response_time": f"{response_time}ms"}
        except Exception:
            db_status_dict = {"status": "연결실패", "response_time": "-"}

        # 외부 API 의존성 상태 확인
        external_apis_dict = {
            "weather_api": check_external_api_status(settings.weather_api_url),
            "weather_flick_back": check_external_api_status(
                settings.weather_flick_back_url, 
                method="GET", 
                health_endpoint="/health"
            ),
            "google_places": check_external_api_status(settings.google_places_url)
        }

        # 전체 서비스 상태 판단
        service_healthy = (
            db_status_dict["status"] == "연결됨" and
            all(api["status"] in ["정상", "타임아웃"] for api in external_apis_dict.values())
        )

        # Pydantic 모델로 변환
        database_status = DatabaseStatus(**db_status_dict)
        external_apis_status = ExternalApisStatus(
            weather_api=ExternalApiStatus(**external_apis_dict["weather_api"]),
            weather_flick_back=ExternalApiStatus(**external_apis_dict["weather_flick_back"]),
            google_places=ExternalApiStatus(**external_apis_dict["google_places"])
        )

        system_status_data = SystemStatusData(
            service_status="정상" if service_healthy else "문제발생",
            database=database_status,
            external_apis=external_apis_status
        )

        return SuccessResponse(
            data=system_status_data,
            message="시스템 상태를 성공적으로 조회했습니다."
        )

    except Exception as e:
        import logging
        logging.error(f"System status error: {e}")
        # 간단한 응답 반환
        return {
            "success": False,
            "data": None,
            "message": f"시스템 상태 조회 중 오류 발생: {str(e)}",
            "error": {"code": "SYSTEM_ERROR", "message": str(e)},
            "timestamp": datetime.now().isoformat()
        }
