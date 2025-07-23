"""
배치 작업 실행 관리 모델
admin-back에서 배치 작업 실행 내역을 관리하기 위한 별도 모델
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class BatchJobExecution(Base):
    """
    배치 작업 실행 내역 테이블
    사용처: weather-flick-admin-back
    설명: 관리자가 실행한 배치 작업 내역 관리
    """
    __tablename__ = "batch_job_executions"
    
    # Primary Key
    id = Column(String, primary_key=True, index=True)
    
    # 작업 정보
    job_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True, default="PENDING")
    parameters = Column(JSONB)
    
    # 진행 상황
    progress = Column(Float, default=0.0)
    current_step = Column(String)
    total_steps = Column(Integer)
    
    # 실행 정보
    created_at = Column(DateTime, server_default=func.now(), index=True)
    created_by = Column(String, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # 결과 정보
    error_message = Column(Text)
    result_summary = Column(JSONB)
    
    # 인덱스
    __table_args__ = (
        # 복합 인덱스 추가 가능
    )