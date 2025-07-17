"""
배치 작업 관리 서비스
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.config import settings
from app.models_batch_execution import BatchJobExecution
from app.schemas.batch import (
    BatchJobExecuteResponse,
    BatchJobListResponse,
    BatchJobLogResponse,
    BatchJobResponse,
    BatchJobStatistic,
    BatchJobStatisticsResponse,
    BatchJobStatus,
    BatchJobType,
)

logger = logging.getLogger(__name__)


class BatchJobService:
    """배치 작업 관리 서비스"""

    def __init__(self, db: Session):
        self.db = db

    async def get_jobs(
        self,
        job_type: BatchJobType | None = None,
        status: BatchJobStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        limit: int = 20
    ) -> BatchJobListResponse:
        """배치 작업 목록 조회"""

        query = self.db.query(BatchJobExecution)

        # 필터 적용
        filters = []
        if job_type:
            filters.append(BatchJobExecution.job_type == job_type.value)
        if status:
            filters.append(BatchJobExecution.status == status.value)
        if start_date:
            filters.append(BatchJobExecution.created_at >= start_date)
        if end_date:
            filters.append(BatchJobExecution.created_at <= end_date)

        if filters:
            query = query.filter(and_(*filters))

        # 총 개수 계산
        total_count = query.count()

        # 페이지네이션 적용
        offset = (page - 1) * limit
        jobs = query.order_by(desc(BatchJobExecution.created_at)).offset(offset).limit(limit).all()

        # 응답 변환
        job_responses = []
        for job in jobs:
            duration_seconds = None
            if job.started_at and job.completed_at:
                duration_seconds = (job.completed_at - job.started_at).total_seconds()

            job_responses.append(BatchJobResponse(
                id=job.id,
                job_type=BatchJobType(job.job_type),
                status=BatchJobStatus(job.status),
                parameters=job.parameters or {},
                progress=job.progress or 0.0,
                current_step=job.current_step,
                total_steps=job.total_steps,
                created_at=job.created_at,
                created_by=job.created_by,
                started_at=job.started_at,
                completed_at=job.completed_at,
                duration_seconds=duration_seconds,
                error_message=job.error_message,
                result_summary=job.result_summary or {}
            ))

        total_pages = (total_count + limit - 1) // limit

        return BatchJobListResponse(
            jobs=job_responses,
            total_count=total_count,
            page=page,
            limit=limit,
            total_pages=total_pages
        )

    async def execute_batch_job(
        self,
        job_type: BatchJobType,
        parameters: dict[str, Any],
        admin_id: str,
        priority: int = 5
    ) -> BatchJobExecuteResponse:
        """배치 작업 실행"""

        # 작업 ID 생성
        job_id = str(uuid4())

        # 데이터베이스에 작업 기록
        job = BatchJobExecution(
            id=job_id,
            job_type=job_type.value,
            status=BatchJobStatus.PENDING.value,
            parameters=parameters,
            created_by=admin_id,
            created_at=datetime.utcnow(),
            priority=priority
        )

        self.db.add(job)
        self.db.commit()

        # 실제 배치 시스템 API 호출
        try:
            batch_api_url = settings.batch_api_url if hasattr(settings, 'batch_api_url') else "http://localhost:9090"
            api_key = settings.batch_api_key if hasattr(settings, 'batch_api_key') else "batch-api-secret-key"
            
            # 배치 API 호출
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{batch_api_url}/api/batch/jobs/{job_type.value}/execute",
                        headers={"X-API-Key": api_key},
                        json={
                            "parameters": parameters,
                            "priority": priority,
                            "requested_by": f"admin:{admin_id}"
                        },
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        batch_response = response.json()
                        logger.info(f"배치 API 호출 성공: {batch_response}")
                        
                        # API 응답의 job_id 사용
                        if "job_id" in batch_response:
                            api_job_id = batch_response["job_id"]
                            # DB의 job_id 업데이트
                            job.id = api_job_id
                            self.db.commit()
                            job_id = api_job_id
                    else:
                        logger.error(f"배치 API 호출 실패: {response.status_code} - {response.text}")
                        
                except httpx.ConnectError:
                    logger.warning("배치 API 서버에 연결할 수 없습니다. DB에만 기록합니다.")
                except Exception as e:
                    logger.error(f"배치 API 호출 중 오류 발생: {e}")
            
            logger.info(f"배치 작업 생성됨: {job_id} - {job_type.value}")
            
            return BatchJobExecuteResponse(
                job_id=job_id,
                message="배치 작업이 성공적으로 요청되었습니다. 곧 실행됩니다.",
                status=BatchJobStatus.PENDING
            )

        except Exception as e:
            logger.error(f"Failed to create batch job {job_id}: {e}")
            job.status = BatchJobStatus.FAILED.value
            job.error_message = str(e)
            self.db.commit()

            return BatchJobExecuteResponse(
                job_id=job_id,
                message="배치 작업 생성 중 오류가 발생했습니다.",
                status=BatchJobStatus.FAILED
            )

    async def get_job_async(self, job_id: str) -> BatchJobExecution | None:
        """작업 상세 정보 조회 (비동기)"""
        return self.db.query(BatchJobExecution).filter(BatchJobExecution.id == job_id).first()

    async def get_job_logs(
        self,
        job_id: str,
        level: str | None = None,
        page: int = 1,
        limit: int = 100
    ) -> BatchJobLogResponse:
        """작업 로그 조회"""

        # BatchJobDetail 테이블이 없으므로 빈 결과 반환
        # 실제 배치 시스템과의 통합 전까지 모의 데이터 반환
        log_responses = []
        total_count = 0

        return BatchJobLogResponse(
            job_id=job_id,
            logs=log_responses,
            total_count=total_count,
            page=page,
            limit=limit
        )

    async def stop_job_async(
        self,
        job_id: str,
        stopped_by: str,
        reason: str = ""
    ) -> bool:
        """작업 중단 (비동기)"""

        # 배치 시스템 API 호출 대신 직접 상태 업데이트
        # TODO: 실제 배치 시스템과 연동 시 API 호출로 변경 필요
        try:
            # 데이터베이스 상태 업데이트
            job = self.db.query(BatchJobExecution).filter(BatchJobExecution.id == job_id).first()
            if job:
                job.status = BatchJobStatus.STOPPED.value
                job.stopped_by = stopped_by
                job.completed_at = datetime.utcnow()
                job.error_message = f"수동 중단: {reason}" if reason else "관리자에 의해 중단됨"
                self.db.commit()
                
                logger.info(f"배치 작업 중단됨: {job_id} by {stopped_by}")
                return True
            else:
                logger.error(f"작업을 찾을 수 없습니다: {job_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to stop job {job_id}: {e}")
            return False

    async def get_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> BatchJobStatisticsResponse:
        """배치 작업 통계 조회"""

        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        query = self.db.query(BatchJobExecution).filter(
            BatchJobExecution.created_at >= start_date,
            BatchJobExecution.created_at <= end_date
        )

        total_jobs = query.count()

        # 작업 유형별 통계
        statistics_by_type = []
        for job_type in BatchJobType:
            type_query = query.filter(BatchJobExecution.job_type == job_type.value)

            total_count = type_query.count()
            if total_count == 0:
                continue

            completed_count = type_query.filter(BatchJobExecution.status == BatchJobStatus.COMPLETED.value).count()
            failed_count = type_query.filter(BatchJobExecution.status == BatchJobStatus.FAILED.value).count()
            stopped_count = type_query.filter(BatchJobExecution.status == BatchJobStatus.STOPPED.value).count()
            running_count = type_query.filter(BatchJobExecution.status == BatchJobStatus.RUNNING.value).count()

            # 평균 실행 시간 계산
            completed_jobs = type_query.filter(
                BatchJobExecution.status == BatchJobStatus.COMPLETED.value,
                BatchJobExecution.started_at.isnot(None),
                BatchJobExecution.completed_at.isnot(None)
            ).all()

            average_duration_seconds = None
            if completed_jobs:
                durations = [
                    (job.completed_at - job.started_at).total_seconds()
                    for job in completed_jobs
                ]
                average_duration_seconds = sum(durations) / len(durations)

            success_rate = (completed_count / total_count * 100) if total_count > 0 else 0

            statistics_by_type.append(BatchJobStatistic(
                job_type=job_type,
                total_count=total_count,
                completed_count=completed_count,
                failed_count=failed_count,
                stopped_count=stopped_count,
                running_count=running_count,
                average_duration_seconds=average_duration_seconds,
                success_rate=success_rate
            ))

        # 최근 실패한 작업들
        recent_failures = query.filter(
            BatchJobExecution.status == BatchJobStatus.FAILED.value
        ).order_by(desc(BatchJobExecution.created_at)).limit(5).all()

        # 현재 실행 중인 작업들
        currently_running = query.filter(
            BatchJobExecution.status == BatchJobStatus.RUNNING.value
        ).order_by(desc(BatchJobExecution.started_at)).all()

        # 응답 변환
        def convert_to_response(job):
            duration_seconds = None
            if job.started_at and job.completed_at:
                duration_seconds = (job.completed_at - job.started_at).total_seconds()

            return BatchJobResponse(
                id=job.id,
                job_type=BatchJobType(job.job_type),
                status=BatchJobStatus(job.status),
                parameters=job.parameters or {},
                progress=job.progress or 0.0,
                current_step=job.current_step,
                total_steps=job.total_steps,
                created_at=job.created_at,
                created_by=job.created_by,
                started_at=job.started_at,
                completed_at=job.completed_at,
                duration_seconds=duration_seconds,
                error_message=job.error_message,
                result_summary=job.result_summary or {}
            )

        return BatchJobStatisticsResponse(
            start_date=start_date,
            end_date=end_date,
            total_jobs=total_jobs,
            statistics_by_type=statistics_by_type,
            recent_failures=[convert_to_response(job) for job in recent_failures],
            currently_running=[convert_to_response(job) for job in currently_running]
        )
