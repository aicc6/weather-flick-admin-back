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
    SystemLogOut,
    SystemLogTestRequest,
    SystemLogTestResponse,
    SystemStatusData,
    SystemStatus,
    ServiceStatus,
    HealthLevel,
)
from app.services.system_log import log_system_event
from app.services.system_service import system_service

router = APIRouter(prefix="/system", tags=["system"])


# 외부 API 헬스체크 함수
def check_external_api_status(api_name, api_key, url, timeout=3):
    """
    외부 API 상태 확인

    Args:
        api_name: API 이름 (로깅용)
        api_key: API 키
        url: 확인할 API URL
        timeout: 타임아웃 시간 (초)

    Returns:
        dict: 상태 정보 (status, response_time)
    """
    # API 키가 설정되지 않은 경우
    if not api_key or api_key in ["your_weather_api_key", "your_google_api_key", "your_kakao_api_key", "your_naver_client_id", "your_naver_client_secret"]:
        return {"status": "키 미설정", "response_time": "-"}
    
    try:
        import time

        start_time = time.time()
        # HEAD 요청 대신 실제 API 엔드포인트에 맞는 요청 사용
        if "weatherapi.com" in url:
            # WeatherAPI의 경우 current weather 엔드포인트 확인
            test_url = f"{url}/current.json?key={api_key}&q=London&aqi=no"
            resp = requests.head(test_url, timeout=timeout)
        elif "visitkorea.or.kr" in url:
            # 한국관광공사 API의 경우 지역코드 API 확인
            test_url = f"{url}/areaCode?serviceKey={api_key}&numOfRows=1&MobileOS=ETC&MobileApp=TestApp"
            resp = requests.head(test_url, timeout=timeout)
        elif "places.googleapis.com" in url:
            # Google Places API의 경우 실제 엔드포인트 확인
            test_url = f"{url}/v1/places:searchText"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": "places.id,places.displayName"
            }
            # POST 요청으로 간단한 텍스트 검색 테스트
            resp = requests.post(test_url, 
                               headers=headers,
                               json={"textQuery": "test"},
                               timeout=timeout)
        else:
            # 기타 API는 기본 HEAD 요청
            resp = requests.head(url, timeout=timeout)
            
        response_time = round((time.time() - start_time) * 1000, 2)  # ms

        if resp.status_code < 400:
            return {"status": "정상", "response_time": f"{response_time}ms"}
        elif resp.status_code == 403:
            return {"status": "인증오류", "response_time": f"{response_time}ms"}
        elif resp.status_code == 404:
            return {"status": "엔드포인트확인필요", "response_time": f"{response_time}ms"}
        else:
            return {
                "status": f"오류({resp.status_code})",
                "response_time": f"{response_time}ms",
            }
    except requests.exceptions.Timeout:
        return {"status": "타임아웃", "response_time": "-"}
    except Exception as e:
        return {"status": "연결실패", "response_time": "-"}


@router.get("/logs", response_model=PaginatedResponse[SystemLogOut])
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

    return PaginatedResponse(
        items=logs,
        total=total,
        page=page,
        size=size,
        message="시스템 로그를 성공적으로 조회했습니다.",
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
        db=db,
    )

    response_data = SystemLogTestResponse(
        log_id=log.log_id,
        level=log.level,
        source=log.source,
        message=log.message,
        created_at=log.created_at,
    )

    return SuccessResponse(
        data=response_data, message="테스트 로그가 성공적으로 생성되었습니다."
    )


@router.get("/status", response_model=SuccessResponse[SystemStatusData])
async def get_system_status():
    """
    시스템 상태 조회 (개선된 버전)
    
    - 전체 시스템 상태 (HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN)
    - 데이터베이스 연결 상태
    - 외부 API 의존성 상태  
    - 시스템 리소스 상태
    - 가동 시간 및 상세 정보
    """
    try:
        # 시스템 서비스를 통한 상태 조회
        system_status = await system_service.get_system_status()
        
        return SuccessResponse(
            data=system_status,
            message="시스템 상태를 성공적으로 조회했습니다."
        )
        
    except Exception as e:
        import logging
        
        logging.error(f"System status error: {e}")
        
        # 오류 발생 시 기본 응답
        from datetime import timezone
        
        error_status = SystemStatusData(
            overall_status=SystemStatus.UNKNOWN,
            service_status=ServiceStatus.DOWN,
            health_level=HealthLevel.CRITICAL,
            message=f"시스템 상태 조회 실패: {str(e)}",
            last_check=datetime.now(timezone.utc),
            uptime_seconds=0,
            database=DatabaseStatus(
                status=ServiceStatus.DOWN,
                response_time=0.0,
                message="조회 실패",
                last_check=datetime.now(timezone.utc)
            ),
            external_apis=ExternalApisStatus(
                weather_api=ExternalApiStatus(
                    status=ServiceStatus.DOWN,
                    response_time=0.0,
                    message="조회 실패",
                    last_check=datetime.now(timezone.utc)
                ),
                tourism_api=ExternalApiStatus(
                    status=ServiceStatus.DOWN,
                    response_time=0.0,
                    message="조회 실패",
                    last_check=datetime.now(timezone.utc)
                ),
                google_places=ExternalApiStatus(
                    status=ServiceStatus.DOWN,
                    response_time=0.0,
                    message="조회 실패",
                    last_check=datetime.now(timezone.utc)
                )
            ),
            details={"error": str(e)}
        )
        
        return SuccessResponse(
            data=error_status,
            message="시스템 상태 조회 중 오류가 발생했지만 기본 정보를 반환합니다."
        )


# 기존 호환성을 위한 레거시 엔드포인트 (deprecated)
@router.get("/status/legacy", response_model=Any, deprecated=True)
async def get_service_status_legacy():
    """
    서비스 상태 조회 (레거시)
    
    @deprecated: /system/status 사용을 권장합니다.
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
            "weather_api": check_external_api_status("Weather API", settings.weather_api_key, settings.weather_api_url),
            "tourism_api": check_external_api_status("Tourism API", settings.korea_tourism_api_key, settings.korea_tourism_api_url),
            "google_places": check_external_api_status("Google Places", settings.google_api_key, settings.google_places_url),
        }

        # 전체 서비스 상태 판단
        service_healthy = db_status_dict["status"] == "연결됨" and all(
            api["status"] in ["정상", "타임아웃"] for api in external_apis_dict.values()
        )

        return {
            "success": True,
            "data": {
                "service_status": "정상" if service_healthy else "문제발생",
                "database": db_status_dict,
                "external_apis": external_apis_dict,
            },
            "message": "시스템 상태를 성공적으로 조회했습니다.",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        import logging
        logging.error(f"System status error: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"시스템 상태 조회 중 오류 발생: {str(e)}",
            "error": {"code": "SYSTEM_ERROR", "message": str(e)},
            "timestamp": datetime.now().isoformat(),
        }
