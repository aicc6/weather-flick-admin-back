"""
시스템 상태 체크 서비스
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any

import psutil
import asyncpg
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.schemas.system import (
    SystemStatus,
    ServiceStatus,
    HealthLevel,
    DatabaseStatus,
    ExternalApiStatus,
    ExternalApisStatus,
    SystemStatusData
)


class SystemStatusService:
    """시스템 상태 체크 서비스"""

    def __init__(self):
        self.start_time = time.time()
        self.timeout = 5.0  # 5초 타임아웃

    async def check_database(self) -> DatabaseStatus:
        """데이터베이스 상태 체크"""
        start_time = time.time()
        
        try:
            # 데이터베이스 세션 가져오기
            async for db in get_db():
                # 간단한 쿼리 실행
                result = await db.execute(text("SELECT 1"))
                result.fetchone()
                
                response_time = (time.time() - start_time) * 1000  # 밀리초로 변환
                
                return DatabaseStatus(
                    status=ServiceStatus.UP,
                    response_time=response_time,
                    message="데이터베이스 연결 정상",
                    last_check=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return DatabaseStatus(
                status=ServiceStatus.DOWN,
                response_time=response_time,
                message=f"데이터베이스 연결 실패: {str(e)}",
                last_check=datetime.now(timezone.utc)
            )

    async def check_external_api(self, url: str, name: str) -> ExternalApiStatus:
        """외부 API 상태 체크"""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return ExternalApiStatus(
                        status=ServiceStatus.UP,
                        response_time=response_time,
                        message=f"{name} API 정상",
                        last_check=datetime.now(timezone.utc)
                    )
                else:
                    return ExternalApiStatus(
                        status=ServiceStatus.PARTIAL,
                        response_time=response_time,
                        message=f"{name} API 응답 코드: {response.status_code}",
                        last_check=datetime.now(timezone.utc)
                    )
                    
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return ExternalApiStatus(
                status=ServiceStatus.DOWN,
                response_time=response_time,
                message=f"{name} API 타임아웃",
                last_check=datetime.now(timezone.utc)
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ExternalApiStatus(
                status=ServiceStatus.DOWN,
                response_time=response_time,
                message=f"{name} API 오류: {str(e)}",
                last_check=datetime.now(timezone.utc)
            )

    async def check_external_apis(self) -> ExternalApisStatus:
        """모든 외부 API 상태 체크"""
        # API 엔드포인트들 (실제 환경에서는 환경변수로 관리)
        apis = {
            "weather_api": "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst",
            "tourism_api": "https://apis.data.go.kr/B551011/KorService1/areaBasedList1",
            "google_places": "https://maps.googleapis.com/maps/api/place/textsearch/json"
        }
        
        # 병렬로 API 체크
        tasks = [
            self.check_external_api(url, name) 
            for name, url in apis.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 매핑
        api_statuses = {}
        for (name, _), result in zip(apis.items(), results):
            if isinstance(result, Exception):
                api_statuses[name] = ExternalApiStatus(
                    status=ServiceStatus.DOWN,
                    response_time=0.0,
                    message=f"{name} 체크 실패: {str(result)}",
                    last_check=datetime.now(timezone.utc)
                )
            else:
                api_statuses[name] = result
        
        return ExternalApisStatus(
            weather_api=api_statuses["weather_api"],
            tourism_api=api_statuses["tourism_api"],
            google_places=api_statuses["google_places"]
        )

    def check_system_resources(self) -> Dict[str, Any]:
        """시스템 리소스 체크"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2)
            }
        except Exception as e:
            return {
                "error": f"시스템 리소스 체크 실패: {str(e)}"
            }

    def determine_overall_status(
        self, 
        db_status: DatabaseStatus, 
        api_status: ExternalApisStatus,
        resources: Dict[str, Any]
    ) -> tuple[SystemStatus, HealthLevel, str]:
        """전체 시스템 상태 결정"""
        
        # 데이터베이스 상태 확인
        if db_status.status == ServiceStatus.DOWN:
            return SystemStatus.UNHEALTHY, HealthLevel.CRITICAL, "데이터베이스 연결 불가"
        
        # 외부 API 상태 확인
        api_down_count = 0
        apis = [api_status.weather_api, api_status.tourism_api, api_status.google_places]
        for api in apis:
            if api.status == ServiceStatus.DOWN:
                api_down_count += 1
        
        # 시스템 리소스 확인
        resource_warning = False
        if "error" not in resources:
            if (resources.get("cpu_percent", 0) > 80 or 
                resources.get("memory_percent", 0) > 85 or 
                resources.get("disk_percent", 0) > 90):
                resource_warning = True
        
        # 상태 결정 로직
        if api_down_count >= 2:
            return SystemStatus.UNHEALTHY, HealthLevel.CRITICAL, "다수 외부 API 장애"
        elif api_down_count == 1 or resource_warning:
            return SystemStatus.DEGRADED, HealthLevel.WARNING, "일부 서비스 성능 저하"
        elif db_status.status == ServiceStatus.PARTIAL:
            return SystemStatus.DEGRADED, HealthLevel.WARNING, "데이터베이스 성능 저하"
        else:
            return SystemStatus.HEALTHY, HealthLevel.SUCCESS, "모든 시스템 정상"

    async def get_system_status(self) -> SystemStatusData:
        """전체 시스템 상태 조회"""
        try:
            # 병렬로 상태 체크
            db_task = self.check_database()
            api_task = self.check_external_apis()
            
            db_status, api_status = await asyncio.gather(db_task, api_task)
            
            # 시스템 리소스 체크
            resources = self.check_system_resources()
            
            # 전체 상태 결정
            overall_status, health_level, message = self.determine_overall_status(
                db_status, api_status, resources
            )
            
            # 가동 시간 계산
            uptime_seconds = int(time.time() - self.start_time)
            
            # 서비스 상태 결정
            if overall_status == SystemStatus.HEALTHY:
                service_status = ServiceStatus.UP
            elif overall_status == SystemStatus.DEGRADED:
                service_status = ServiceStatus.PARTIAL
            else:
                service_status = ServiceStatus.DOWN
            
            return SystemStatusData(
                overall_status=overall_status,
                service_status=service_status,
                health_level=health_level,
                message=message,
                last_check=datetime.now(timezone.utc),
                uptime_seconds=uptime_seconds,
                database=db_status,
                external_apis=api_status,
                details=resources
            )
            
        except Exception as e:
            return SystemStatusData(
                overall_status=SystemStatus.UNKNOWN,
                service_status=ServiceStatus.DOWN,
                health_level=HealthLevel.CRITICAL,
                message=f"시스템 상태 체크 실패: {str(e)}",
                last_check=datetime.now(timezone.utc),
                uptime_seconds=0,
                database=DatabaseStatus(
                    status=ServiceStatus.DOWN,
                    response_time=0.0,
                    message="체크 실패",
                    last_check=datetime.now(timezone.utc)
                ),
                external_apis=ExternalApisStatus(
                    weather_api=ExternalApiStatus(
                        status=ServiceStatus.DOWN,
                        response_time=0.0,
                        message="체크 실패",
                        last_check=datetime.now(timezone.utc)
                    ),
                    tourism_api=ExternalApiStatus(
                        status=ServiceStatus.DOWN,
                        response_time=0.0,
                        message="체크 실패",
                        last_check=datetime.now(timezone.utc)
                    ),
                    google_places=ExternalApiStatus(
                        status=ServiceStatus.DOWN,
                        response_time=0.0,
                        message="체크 실패",
                        last_check=datetime.now(timezone.utc)
                    )
                ),
                details={"error": str(e)}
            )


# 전역 인스턴스
system_service = SystemStatusService()