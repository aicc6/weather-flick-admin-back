"""
배치 시스템 API 클라이언트

weather-flick-batch 서비스의 API를 호출하는 클라이언트
"""

import logging
from datetime import datetime
from typing import Any

import httpx

from app.config import settings
from app.schemas.batch import (
    BatchJobListResponse,
    BatchJobResponse,
    BatchJobStatus,
    BatchJobType,
)

logger = logging.getLogger(__name__)

class BatchAPIClient:
    """배치 시스템 API 클라이언트"""

    def __init__(self):
        # 배치 API 설정
        self.base_url = settings.batch_api_url or "http://weather-flick-batch:9000"
        self.api_key = settings.batch_api_key or "batch-api-secret-key"
        self.timeout = 30.0

        # HTTP 클라이언트 생성
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            },
            timeout=self.timeout
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def list_jobs(
        self,
        job_type: BatchJobType | None = None,
        status: BatchJobStatus | None = None,
        page: int = 1,
        size: int = 20
    ) -> BatchJobListResponse:
        """배치 작업 목록 조회"""
        try:
            params = {
                "page": page,
                "size": size
            }

            if job_type:
                params["job_type"] = job_type.value
            if status:
                params["status"] = status.value

            response = await self.client.get("/api/batch/jobs", params=params)
            response.raise_for_status()

            data = response.json()
            return BatchJobListResponse(**data)

        except httpx.HTTPError as e:
            logger.error(f"Failed to list batch jobs: {e}")
            raise

    async def execute_job(
        self,
        job_type: BatchJobType,
        parameters: dict[str, Any] | None = None,
        priority: int = 5,
        requested_by: str | None = None
    ) -> dict[str, Any]:
        """배치 작업 실행"""
        try:
            request_data = {
                "parameters": parameters or {},
                "priority": priority,
                "requested_by": requested_by
            }

            response = await self.client.post(
                f"/api/batch/jobs/{job_type.value}/execute",
                json=request_data
            )
            response.raise_for_status()

            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to execute batch job {job_type}: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise

    async def get_job_info(self, job_id: str) -> BatchJobResponse:
        """작업 정보 조회"""
        try:
            response = await self.client.get(f"/api/batch/jobs/{job_id}")
            response.raise_for_status()

            data = response.json()
            return BatchJobResponse(**data)

        except httpx.HTTPError as e:
            logger.error(f"Failed to get job info for {job_id}: {e}")
            raise

    async def get_job_logs(
        self,
        job_id: str,
        level: str | None = None,
        page: int = 1,
        size: int = 100
    ) -> dict[str, Any]:
        """작업 로그 조회"""
        try:
            params = {
                "page": page,
                "size": size
            }

            if level:
                params["level"] = level

            response = await self.client.get(
                f"/api/batch/jobs/{job_id}/logs",
                params=params
            )
            response.raise_for_status()

            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get job logs for {job_id}: {e}")
            raise

    async def stop_job(self, job_id: str, reason: str | None = None) -> dict[str, Any]:
        """작업 중단"""
        try:
            request_data = {
                "reason": reason,
                "force": False
            }

            response = await self.client.post(
                f"/api/batch/jobs/{job_id}/stop",
                json=request_data
            )
            response.raise_for_status()

            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to stop job {job_id}: {e}")
            raise

    async def get_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> list[dict[str, Any]]:
        """작업 통계 조회"""
        try:
            params = {}

            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()

            response = await self.client.get(
                "/api/batch/statistics",
                params=params
            )
            response.raise_for_status()

            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get statistics: {e}")
            raise

    async def get_system_status(self) -> dict[str, Any]:
        """시스템 상태 조회"""
        try:
            response = await self.client.get("/api/batch/system/status")
            response.raise_for_status()

            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get system status: {e}")
            raise

    async def health_check(self) -> bool:
        """헬스체크"""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Batch API health check failed: {e}")
            return False
