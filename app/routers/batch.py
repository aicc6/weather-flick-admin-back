"""
배치 작업 관리 라우터
weather-flick-batch API 서버와 통신하는 HTTP 클라이언트
"""

import asyncio
import httpx
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.schemas.common import SuccessResponse, PaginatedResponse
from app.services.system_log import log_system_event
from app.config import settings

router = APIRouter(prefix="/batch", tags=["batch"])

# 배치 API 서버 설정
BATCH_API_BASE_URL = getattr(settings, 'batch_api_url', 'http://localhost:8001')
BATCH_API_TIMEOUT = getattr(settings, 'batch_api_timeout', 30)

# HTTP 클라이언트 헬퍼 함수
async def batch_api_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """배치 API 서버에 HTTP 요청"""
    url = f"{BATCH_API_BASE_URL}{endpoint}"
    
    timeout = httpx.Timeout(BATCH_API_TIMEOUT)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
    
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="배치 서비스 응답 시간 초과"
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="배치 서비스에 연결할 수 없습니다"
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="요청한 리소스를 찾을 수 없습니다")
        elif e.response.status_code == 409:
            raise HTTPException(status_code=409, detail="작업이 이미 실행 중입니다")
        else:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"배치 서비스 오류: {e.response.text}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"배치 서비스 통신 오류: {str(e)}"
        )


# 스키마 정의
class BatchJobInfo(BaseModel):
    job_id: str
    name: str
    description: str
    category: str
    timeout: int
    status: str = "available"


class BatchJobRequest(BaseModel):
    job_id: str = Field(..., description="실행할 배치 작업 ID")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="작업 실행 매개변수")


class BatchJobStatus(BaseModel):
    job_id: str
    execution_id: str
    status: str  # running, completed, failed, timeout
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[int] = None  # 실행 시간 (초)
    output: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None


class BatchJobExecutionResponse(BaseModel):
    execution_id: str
    job_id: str
    status: str
    message: str
    start_time: datetime


@router.get("/jobs", response_model=SuccessResponse[List[BatchJobInfo]])
async def get_available_batch_jobs(
    category: Optional[str] = Query(None, description="작업 카테고리 필터")
):
    """이용 가능한 배치 작업 목록 조회"""
    
    # 배치 API 서버에서 작업 목록 조회
    params = {}
    if category:
        params["category"] = category
    
    batch_jobs = await batch_api_request("GET", "/api/batch/jobs", params=params)
    
    # 응답 형식 변환
    jobs = []
    for job in batch_jobs:
        jobs.append(BatchJobInfo(
            job_id=job["job_id"],
            name=job["name"],
            description=job["description"],
            category=job["category"],
            timeout=job["timeout"],
            status=job["status"]
        ))
    
    return SuccessResponse(
        data=jobs,
        message="배치 작업 목록을 성공적으로 조회했습니다."
    )


@router.get("/jobs/categories")
async def get_batch_job_categories():
    """배치 작업 카테고리 목록 조회"""
    
    # 배치 API 서버에서 카테고리 목록 조회
    categories = await batch_api_request("GET", "/api/batch/jobs/categories")
    
    return SuccessResponse(
        data=categories,
        message="배치 작업 카테고리를 성공적으로 조회했습니다."
    )


@router.post("/jobs/execute", response_model=SuccessResponse[BatchJobExecutionResponse])
async def execute_batch_job(
    request: BatchJobRequest,
    db: Session = Depends(get_db)
):
    """배치 작업 수동 실행"""
    
    # 배치 API 서버에 작업 실행 요청
    payload = {
        "job_id": request.job_id,
        "parameters": request.parameters or {}
    }
    
    batch_response = await batch_api_request(
        "POST", 
        "/api/batch/jobs/execute", 
        json=payload
    )
    
    # 시스템 로그 기록
    log_system_event(
        level="INFO",
        message=f"배치 작업 '{request.job_id}' 수동 실행 시작",
        source="batch_manager",
        context={
            "job_id": request.job_id,
            "execution_id": batch_response.get("execution_id"),
            "parameters": request.parameters
        },
        db=db
    )
    
    # 응답 형식 변환
    response_data = BatchJobExecutionResponse(
        execution_id=batch_response["execution_id"],
        job_id=batch_response["job_id"],
        status=batch_response["status"],
        message=batch_response["message"],
        start_time=datetime.fromisoformat(batch_response["start_time"])
    )
    
    return SuccessResponse(
        data=response_data,
        message="배치 작업 실행이 시작되었습니다."
    )


@router.get("/jobs/{job_id}/status", response_model=SuccessResponse[BatchJobStatus])
async def get_batch_job_status(job_id: str):
    """특정 배치 작업 상태 조회"""
    
    # 배치 API 서버에서 작업 상태 조회
    batch_status = await batch_api_request("GET", f"/api/batch/jobs/{job_id}/status")
    
    # 응답 형식 변환
    status_data = BatchJobStatus(
        job_id=batch_status["job_id"],
        execution_id=batch_status["execution_id"],
        status=batch_status["status"],
        start_time=datetime.fromisoformat(batch_status["start_time"]),
        end_time=datetime.fromisoformat(batch_status["end_time"]) if batch_status.get("end_time") else None,
        duration=batch_status.get("duration"),
        output=batch_status.get("output"),
        error=batch_status.get("error"),
        exit_code=batch_status.get("exit_code")
    )
    
    return SuccessResponse(
        data=status_data,
        message="배치 작업 상태를 성공적으로 조회했습니다."
    )


@router.get("/jobs/running", response_model=SuccessResponse[List[BatchJobStatus]])
async def get_running_batch_jobs():
    """실행 중인 배치 작업 목록 조회"""
    
    running_job_list = []
    current_time = datetime.now()
    
    for job_id, job_info in running_jobs.items():
        if job_info["status"] == "running":
            duration = int((current_time - job_info["start_time"]).total_seconds())
            
            running_job_list.append(BatchJobStatus(
                job_id=job_id,
                execution_id=job_info["execution_id"],
                status=job_info["status"],
                start_time=job_info["start_time"],
                duration=duration,
                output=job_info.get("output"),
                error=job_info.get("error")
            ))
    
    return SuccessResponse(
        data=running_job_list,
        message="실행 중인 배치 작업 목록을 성공적으로 조회했습니다."
    )


@router.delete("/jobs/{job_id}/cancel")
async def cancel_batch_job(job_id: str, db: Session = Depends(get_db)):
    """배치 작업 취소 (실행 중인 작업만)"""
    
    if job_id not in running_jobs:
        raise HTTPException(
            status_code=404,
            detail="실행 중인 작업을 찾을 수 없습니다."
        )
    
    job_info = running_jobs[job_id]
    
    if job_info["status"] != "running":
        raise HTTPException(
            status_code=400,
            detail="실행 중이지 않은 작업은 취소할 수 없습니다."
        )
    
    # 프로세스 종료 시도 (실제 구현에서는 프로세스 PID 관리 필요)
    try:
        # 작업 상태를 cancelled로 변경
        running_jobs[job_id]["status"] = "cancelled"
        running_jobs[job_id]["end_time"] = datetime.now()
        running_jobs[job_id]["error"] = "사용자에 의해 취소됨"
        
        # 시스템 로그 기록
        log_system_event(
            level="WARNING",
            message=f"배치 작업 '{job_id}' 사용자에 의해 취소됨",
            source="batch_manager",
            context={"execution_id": job_info["execution_id"]},
            db=db
        )
        
        return SuccessResponse(
            data={"job_id": job_id, "status": "cancelled"},
            message="배치 작업이 취소되었습니다."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"작업 취소 중 오류가 발생했습니다: {str(e)}"
        )


async def run_batch_job_background(
    job_id: str,
    execution_id: str,
    job_config: Dict[str, Any],
    parameters: Dict[str, Any],
    db: Session
):
    """백그라운드에서 배치 작업 실행"""
    
    try:
        # 배치 프로젝트 경로 확인
        if not BATCH_PROJECT_PATH.exists():
            raise Exception(f"배치 프로젝트 경로를 찾을 수 없습니다: {BATCH_PROJECT_PATH}")
        
        script_path = BATCH_PROJECT_PATH / job_config["script"]
        if not script_path.exists():
            raise Exception(f"배치 스크립트를 찾을 수 없습니다: {script_path}")
        
        # 실행 명령어 구성
        cmd = ["python", str(script_path)] + job_config["args"]
        
        # 매개변수가 있는 경우 추가
        if parameters:
            for key, value in parameters.items():
                cmd.extend([f"--{key}", str(value)])
        
        # 프로세스 실행
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=BATCH_PROJECT_PATH,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # 타임아웃과 함께 프로세스 대기
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=job_config["timeout"]
            )
            
            # 결과 처리
            end_time = datetime.now()
            output = stdout.decode('utf-8') if stdout else ""
            error = stderr.decode('utf-8') if stderr else ""
            
            if process.returncode == 0:
                status = "completed"
            else:
                status = "failed"
            
            # 실행 결과 업데이트
            running_jobs[job_id].update({
                "status": status,
                "end_time": end_time,
                "output": output,
                "error": error,
                "exit_code": process.returncode
            })
            
            # 시스템 로그 기록
            log_system_event(
                level="INFO" if status == "completed" else "ERROR",
                message=f"배치 작업 '{job_config['name']}' 실행 {status}",
                source="batch_manager",
                context={
                    "job_id": job_id,
                    "execution_id": execution_id,
                    "exit_code": process.returncode,
                    "duration": int((end_time - running_jobs[job_id]["start_time"]).total_seconds())
                },
                db=db
            )
            
        except asyncio.TimeoutError:
            # 타임아웃 발생
            process.kill()
            await process.wait()
            
            running_jobs[job_id].update({
                "status": "timeout",
                "end_time": datetime.now(),
                "error": f"작업이 {job_config['timeout']}초 타임아웃으로 종료되었습니다.",
                "exit_code": -1
            })
            
            log_system_event(
                level="ERROR",
                message=f"배치 작업 '{job_config['name']}' 타임아웃 발생",
                source="batch_manager",
                context={
                    "job_id": job_id,
                    "execution_id": execution_id,
                    "timeout": job_config["timeout"]
                },
                db=db
            )
            
    except Exception as e:
        # 실행 오류 처리
        running_jobs[job_id].update({
            "status": "failed",
            "end_time": datetime.now(),
            "error": str(e),
            "exit_code": -1
        })
        
        log_system_event(
            level="ERROR",
            message=f"배치 작업 '{job_config['name']}' 실행 오류: {str(e)}",
            source="batch_manager",
            context={
                "job_id": job_id,
                "execution_id": execution_id,
                "error": str(e)
            },
            db=db
        )
    
    # 완료된 작업은 일정 시간 후 정리 (선택사항)
    # await asyncio.sleep(3600)  # 1시간 후 정리
    # if job_id in running_jobs and running_jobs[job_id]["status"] != "running":
    #     del running_jobs[job_id]