"""
배치 작업 관리 서비스
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import httpx
from uuid import uuid4

from app.models import AdminBatchJob, AdminBatchJobDetail
from app.schemas.batch import (
    BatchJobType, BatchJobStatus, BatchJobLogLevel,
    BatchJobResponse, BatchJobListResponse, BatchJobExecuteResponse,
    BatchJobStatusResponse, BatchJobLog, BatchJobLogResponse,
    BatchJobStopResponse, BatchJobStatisticsResponse, BatchJobStatistic
)
from app.config import settings

logger = logging.getLogger(__name__)


class BatchJobService:
    """배치 작업 관리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        
    async def get_jobs(
        self,
        job_type: Optional[BatchJobType] = None,
        status: Optional[BatchJobStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 20
    ) -> BatchJobListResponse:
        """배치 작업 목록 조회"""
        
        query = self.db.query(AdminBatchJob)
        
        # 필터 적용
        filters = []
        if job_type:
            filters.append(AdminBatchJob.job_type == job_type.value)
        if status:
            filters.append(AdminBatchJob.status == status.value)
        if start_date:
            filters.append(AdminBatchJob.created_at >= start_date)
        if end_date:
            filters.append(AdminBatchJob.created_at <= end_date)
            
        if filters:
            query = query.filter(and_(*filters))
            
        # 총 개수 계산
        total_count = query.count()
        
        # 페이지네이션 적용
        offset = (page - 1) * limit
        jobs = query.order_by(desc(AdminBatchJob.created_at)).offset(offset).limit(limit).all()
        
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
        parameters: Dict[str, Any],
        admin_id: str,
        priority: int = 5
    ) -> BatchJobExecuteResponse:
        """배치 작업 실행"""
        
        # 작업 ID 생성
        job_id = str(uuid4())
        
        # 데이터베이스에 작업 기록
        job = AdminBatchJob(
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
        
        # 배치 시스템에 작업 요청 (모의)
        try:
            # 실제 배치 시스템 API 호출
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.batch_api_url}/api/jobs/execute",
                    json={
                        "job_id": job_id,
                        "job_type": job_type.value,
                        "parameters": parameters,
                        "priority": priority
                    },
                    headers={"Authorization": f"Bearer {settings.batch_api_key}"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    # 작업 시작됨으로 상태 업데이트
                    job.status = BatchJobStatus.RUNNING.value
                    job.started_at = datetime.utcnow()
                    self.db.commit()
                    
                    return BatchJobExecuteResponse(
                        job_id=job_id,
                        message="배치 작업이 성공적으로 시작되었습니다.",
                        status=BatchJobStatus.RUNNING
                    )
                else:
                    # 실행 실패
                    job.status = BatchJobStatus.FAILED.value
                    job.error_message = f"배치 시스템 응답 오류: {response.status_code}"
                    self.db.commit()
                    
                    return BatchJobExecuteResponse(
                        job_id=job_id,
                        message="배치 작업 시작에 실패했습니다.",
                        status=BatchJobStatus.FAILED
                    )
                    
        except Exception as e:
            logger.error(f"Failed to execute batch job {job_id}: {e}")
            job.status = BatchJobStatus.FAILED.value
            job.error_message = str(e)
            self.db.commit()
            
            return BatchJobExecuteResponse(
                job_id=job_id,
                message="배치 작업 실행 중 오류가 발생했습니다.",
                status=BatchJobStatus.FAILED
            )
    
    async def get_job_async(self, job_id: str) -> Optional[AdminBatchJob]:
        """작업 상세 정보 조회 (비동기)"""
        return self.db.query(AdminBatchJob).filter(AdminBatchJob.id == job_id).first()
    
    async def get_job_logs(
        self,
        job_id: str,
        level: Optional[str] = None,
        page: int = 1,
        limit: int = 100
    ) -> BatchJobLogResponse:
        """작업 로그 조회"""
        
        query = self.db.query(AdminBatchJobDetail).filter(AdminBatchJobDetail.job_id == job_id)
        
        if level:
            query = query.filter(AdminBatchJobDetail.level == level)
            
        # 총 개수 계산
        total_count = query.count()
        
        # 페이지네이션 적용
        offset = (page - 1) * limit
        logs = query.order_by(desc(AdminBatchJobDetail.timestamp)).offset(offset).limit(limit).all()
        
        # 응답 변환
        log_responses = []
        for log in logs:
            log_responses.append(BatchJobLog(
                id=log.id,
                timestamp=log.timestamp,
                level=BatchJobLogLevel(log.level),
                message=log.message,
                details=log.details or {}
            ))
        
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
        
        try:
            # 배치 시스템에 중단 요청
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.batch_api_url}/api/jobs/{job_id}/stop",
                    json={"reason": reason, "stopped_by": stopped_by},
                    headers={"Authorization": f"Bearer {settings.batch_api_key}"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    # 데이터베이스 상태 업데이트
                    job = self.db.query(AdminBatchJob).filter(AdminBatchJob.id == job_id).first()
                    if job:
                        job.status = BatchJobStatus.STOPPING.value
                        job.stopped_by = stopped_by
                        # job.stop_reason = reason  # 모델에 stop_reason 필드가 없음
                        self.db.commit()
                    
                    return True
                else:
                    logger.error(f"Failed to stop job {job_id}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to stop job {job_id}: {e}")
            return False
    
    async def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> BatchJobStatisticsResponse:
        """배치 작업 통계 조회"""
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
            
        query = self.db.query(AdminBatchJob).filter(
            AdminBatchJob.created_at >= start_date,
            AdminBatchJob.created_at <= end_date
        )
        
        total_jobs = query.count()
        
        # 작업 유형별 통계
        statistics_by_type = []
        for job_type in BatchJobType:
            type_query = query.filter(AdminBatchJob.job_type == job_type.value)
            
            total_count = type_query.count()
            if total_count == 0:
                continue
                
            completed_count = type_query.filter(AdminBatchJob.status == BatchJobStatus.COMPLETED.value).count()
            failed_count = type_query.filter(AdminBatchJob.status == BatchJobStatus.FAILED.value).count()
            stopped_count = type_query.filter(AdminBatchJob.status == BatchJobStatus.STOPPED.value).count()
            running_count = type_query.filter(AdminBatchJob.status == BatchJobStatus.RUNNING.value).count()
            
            # 평균 실행 시간 계산
            completed_jobs = type_query.filter(
                AdminBatchJob.status == BatchJobStatus.COMPLETED.value,
                AdminBatchJob.started_at.isnot(None),
                AdminBatchJob.completed_at.isnot(None)
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
            AdminBatchJob.status == BatchJobStatus.FAILED.value
        ).order_by(desc(AdminBatchJob.created_at)).limit(5).all()
        
        # 현재 실행 중인 작업들
        currently_running = query.filter(
            AdminBatchJob.status == BatchJobStatus.RUNNING.value
        ).order_by(desc(AdminBatchJob.started_at)).all()
        
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