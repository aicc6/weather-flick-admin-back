"""
WebSocket API for real-time batch job logs streaming
"""

import json
import logging
from datetime import datetime
from typing import Dict, Set

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models_batch_execution import BatchJobExecution
from app.models import BatchJobLog

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ws",
    tags=["websocket"],
)

# 활성 WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        logger.info(f"WebSocket connected for job {job_id}")
        
    def disconnect(self, websocket: WebSocket, job_id: str):
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        logger.info(f"WebSocket disconnected for job {job_id}")
        
    async def send_to_job(self, job_id: str, message: dict):
        if job_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to websocket: {e}")
                    disconnected.add(connection)
            
            # 실패한 연결 제거
            for conn in disconnected:
                self.active_connections[job_id].discard(conn)

manager = ConnectionManager()


@router.websocket("/jobs/{job_id}/logs/stream")
async def websocket_endpoint(
    websocket: WebSocket,
    job_id: str,
    api_key: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for streaming batch job logs in real-time.
    
    - **job_id**: 배치 작업 ID
    - **api_key**: API 인증 키 (쿼리 파라미터로 전달)
    """
    # 간단한 API 키 검증 (실제로는 더 복잡한 인증 필요)
    if api_key != "batch-api-secret-key":
        await websocket.close(code=4001, reason="Invalid API key")
        return
    
    await manager.connect(websocket, job_id)
    
    try:
        # 데이터베이스에서 직접 작업 정보 조회
        job = db.query(BatchJobExecution).filter(
            BatchJobExecution.id == job_id
        ).first()
        
        if not job:
            await websocket.send_json({
                "type": "error",
                "message": f"작업을 찾을 수 없습니다: {job_id}"
            })
            await websocket.close()
            return
        
        # 기존 로그 전송 (historical logs)
        try:
            existing_logs = db.query(BatchJobLog).filter(
                BatchJobLog.job_id == job_id
            ).order_by(BatchJobLog.start_time).all()
            
            for log in existing_logs:
                await websocket.send_json({
                    "type": "log",
                    "timestamp": log.start_time.isoformat() if log.start_time else datetime.now().isoformat(),
                    "level": "ERROR" if log.status == "failed" else "INFO",
                    "message": log.error_message or f"{log.job_name} - {log.status}",
                    "details": {
                        "status": log.status,
                        "job_name": log.job_name,
                        "job_type": log.job_type,
                        "duration": log.duration,
                        "result": log.result
                    },
                    "historical": True
                })
        except Exception as e:
            logger.error(f"Error fetching historical logs: {e}")
        
        # 작업 상태 정보 전송
        try:
            await websocket.send_json({
                "type": "job_update",
                "data": {
                    "status": job.status if job.status else "UNKNOWN",
                    "progress": float(job.progress) if job.progress else 0.0,
                    "current_step": job.current_step,
                    "total_steps": job.total_steps
                }
            })
        except Exception as e:
            logger.error(f"Error sending job status: {e}")
        
        # 실시간 업데이트 대기
        while True:
            try:
                # 클라이언트로부터 메시지 수신
                data = await websocket.receive_text()
                
                # ping-pong 처리
                if data == "ping":
                    await websocket.send_text("pong")
                    continue
                
                # 주기적으로 작업 상태 업데이트
                # 데이터베이스에서 최신 상태 조회
                try:
                    # 새로고침된 작업 정보 가져오기
                    db.refresh(job)
                    
                    # 최신 로그 가져오기 (마지막으로 전송한 이후의 로그만)
                    # 실제 구현에서는 마지막 전송 시간을 추적해야 함
                    
                    await websocket.send_json({
                        "type": "job_update",
                        "data": {
                            "status": job.status if job.status else "UNKNOWN",
                            "progress": float(job.progress) if job.progress else 0.0,
                            "current_step": job.current_step,
                            "total_steps": job.total_steps
                        }
                    })
                except Exception as e:
                    logger.error(f"Error updating job status: {e}")
                    
            except WebSocketDisconnect:
                manager.disconnect(websocket, job_id)
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        manager.disconnect(websocket, job_id)