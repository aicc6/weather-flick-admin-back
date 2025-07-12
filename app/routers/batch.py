"""
배치 작업 관리 API 라우터

이 모듈은 배치 작업을 수동으로 실행하고 모니터링할 수 있는 엔드포인트를 제공합니다.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from enum import Enum

from app.database import get_db
from app.auth.dependencies import require_admin, require_super_admin
from app.models import Admin
from app.schemas.batch import (
    BatchJobResponse,
    BatchJobListResponse,
    BatchJobExecuteRequest,
    BatchJobExecuteResponse,
    BatchJobStatusResponse,
    BatchJobLogResponse,
    BatchJobStopResponse,
    BatchJobType,
    BatchJobStatus,
    BatchJobStatisticsResponse
)
from app.services.batch import BatchJobService

router = APIRouter(
    prefix="/api/batch",
    tags=["batch"],
    responses={404: {"description": "Not found"}},
)


@router.get("/jobs", response_model=BatchJobListResponse)
async def get_batch_jobs(
    job_type: Optional[BatchJobType] = None,
    status: Optional[BatchJobStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    배치 작업 목록을 조회합니다.
    
    - **job_type**: 작업 유형으로 필터링 (옵션)
    - **status**: 작업 상태로 필터링 (옵션)
    - **start_date**: 시작일 이후 작업만 조회 (옵션)
    - **end_date**: 종료일 이전 작업만 조회 (옵션)
    - **page**: 페이지 번호
    - **limit**: 페이지당 항목 수
    """
    service = BatchJobService(db)
    return await service.get_jobs(
        job_type=job_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit
    )


@router.post("/jobs/{job_type}/execute", response_model=BatchJobExecuteResponse)
async def execute_batch_job(
    job_type: BatchJobType,
    background_tasks: BackgroundTasks,
    request: Optional[BatchJobExecuteRequest] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    특정 배치 작업을 수동으로 실행합니다.
    
    - **job_type**: 실행할 작업 유형
    - **request**: 작업 실행 옵션 (옵션)
    
    지원하는 작업 유형:
    - KTO_DATA_COLLECTION: 한국관광공사 데이터 수집
    - WEATHER_DATA_COLLECTION: 기상청 날씨 데이터 수집
    - RECOMMENDATION_CALCULATION: 추천 점수 계산
    - DATA_QUALITY_CHECK: 데이터 품질 검사
    - ARCHIVE_BACKUP: 아카이빙 및 백업
    - SYSTEM_HEALTH_CHECK: 시스템 헬스체크
    """
    service = BatchJobService(db)
    
    try:
        # 배치 API를 통해 작업 실행 요청
        response = await service.execute_batch_job(
            job_type=job_type,
            parameters=request.parameters if request else {},
            admin_id=current_admin.admin_id,
            priority=request.priority if request else 5
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to execute batch job: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"배치 작업 실행 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/jobs/{job_id}/status", response_model=BatchJobStatusResponse)
async def get_batch_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    특정 배치 작업의 상태를 조회합니다.
    
    - **job_id**: 작업 ID
    """
    service = BatchJobService(db)
    job = await service.get_job_async(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    return BatchJobStatusResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        total_steps=job.total_steps,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        result_summary=job.result_summary
    )


@router.get("/jobs/{job_id}/logs", response_model=BatchJobLogResponse)
async def get_batch_job_logs(
    job_id: str,
    level: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    특정 배치 작업의 로그를 조회합니다.
    
    - **job_id**: 작업 ID
    - **level**: 로그 레벨로 필터링 (INFO, WARNING, ERROR)
    - **page**: 페이지 번호
    - **limit**: 페이지당 로그 수
    """
    service = BatchJobService(db)
    
    logs = await service.get_job_logs(
        job_id=job_id,
        level=level,
        page=page,
        limit=limit
    )
    
    return logs


@router.post("/jobs/{job_id}/stop", response_model=BatchJobStopResponse)
async def stop_batch_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin)  # 슈퍼관리자만 중단 가능
):
    """
    실행 중인 배치 작업을 중단합니다.
    
    - **job_id**: 중단할 작업 ID
    
    주의: 이 기능은 슈퍼관리자만 사용할 수 있습니다.
    """
    service = BatchJobService(db)
    
    # 작업 상태 먼저 확인
    job = await service.get_job_async(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    if job.status != BatchJobStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"실행 중이 아닌 작업은 중단할 수 없습니다. 현재 상태: {job.status.value}"
        )
    
    success = await service.stop_job_async(
        job_id=job_id,
        stopped_by=current_admin.admin_id,
        reason="관리자가 수동으로 중단 요청"
    )
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="작업 중단에 실패했습니다."
        )
    
    return BatchJobStopResponse(
        job_id=job_id,
        message="작업 중단 요청이 전송되었습니다.",
        status=BatchJobStatus.STOPPING
    )


@router.get("/statistics", response_model=BatchJobStatisticsResponse)
async def get_batch_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    배치 작업 통계를 조회합니다.
    
    - **start_date**: 통계 시작일 (옵션)
    - **end_date**: 통계 종료일 (옵션)
    """
    service = BatchJobService(db)
    return await service.get_statistics(
        start_date=start_date,
        end_date=end_date
    )


@router.get("/jobs/{job_id}", response_model=BatchJobResponse)
async def get_batch_job_detail(
    job_id: str,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    특정 배치 작업의 상세 정보를 조회합니다.
    
    - **job_id**: 작업 ID
    """
    service = BatchJobService(db)
    job = await service.get_job_async(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    return job