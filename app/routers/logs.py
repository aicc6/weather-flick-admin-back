"""
관리자 로그 관리 라우터
Cursor 규칙에 따른 로그 조회 및 관리 API
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth.dependencies import require_admin, require_super_admin
from ..auth.logging import AdminLogService
from ..database import get_db
from ..models import Admin, SystemLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["Admin Logs"])


@router.get("/activities")
async def get_recent_activities(
    limit: int = Query(50, ge=1, le=200, description="조회할 로그 수"),
    admin_id: int | None = Query(None, description="특정 관리자 필터"),
    severity: str | None = Query(
        None, description="심각도 필터 (NORMAL, HIGH, CRITICAL)"
    ),
    db: Session = Depends(get_db),
    admin_user: Admin = Depends(require_admin),
):
    """
    최근 관리자 활동 내역 조회 (관리자 전용)

    Args:
        limit: 조회할 로그 수 (1-200)
        admin_id: 특정 관리자 ID로 필터링
        severity: 심각도로 필터링
        db: 데이터베이스 세션
        admin_user: 현재 관리자

    Returns:
        관리자 활동 로그 목록
    """
    try:
        log_service = AdminLogService(db)
        activities = log_service.get_recent_activities(
            limit=limit, admin_id=admin_id, severity=severity
        )

        # 로그를 딕셔너리로 변환
        activity_list = []
        for activity in activities:
            activity_list.append(
                {
                    "log_id": activity.log_id,
                    "admin_id": activity.admin_id,
                    "admin_email": (
                        activity.admin.email if activity.admin else "Unknown"
                    ),
                    "action": activity.action,
                    "description": activity.description,
                    "target_resource": activity.target_resource,
                    "severity": activity.severity,
                    "ip_address": activity.ip_address,
                    "created_at": activity.created_at.isoformat(),
                }
            )

        return {
            "success": True,
            "data": {
                "activities": activity_list,
                "total": len(activity_list),
                "filters": {"admin_id": admin_id, "severity": severity, "limit": limit},
            },
            "message": f"관리자 활동 로그 {len(activity_list)}개를 조회했습니다.",
            "error": None,
            "meta": None,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"관리자 활동 로그 조회 실패: {e}")
        raise HTTPException(
            status_code=500, detail="관리자 활동 로그 조회 중 오류가 발생했습니다."
        )


@router.get("/statistics")
async def get_log_statistics(
    db: Session = Depends(get_db), admin_user: Admin = Depends(require_admin)
):
    """
    관리자 활동 통계 조회 (관리자 전용)

    Returns:
        관리자 활동 통계 정보
    """
    try:
        log_service = AdminLogService(db)
        stats = log_service.get_activity_statistics()

        return {
            "success": True,
            "data": stats,
            "message": "관리자 활동 통계를 성공적으로 조회했습니다.",
            "error": None,
            "meta": None,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"관리자 활동 통계 조회 실패: {e}")
        raise HTTPException(
            status_code=500, detail="관리자 활동 통계 조회 중 오류가 발생했습니다."
        )


@router.delete("/cleanup")
async def cleanup_old_logs(
    days: int = Query(90, ge=30, le=365, description="보관할 일 수 (30-365일)"),
    db: Session = Depends(get_db),
    admin_user: Admin = Depends(require_super_admin),  # 슈퍼관리자만 로그 정리 가능
):
    """
    오래된 관리자 로그 정리 (슈퍼관리자 전용)

    Args:
        days: 보관할 일 수 (30-365일)
        db: 데이터베이스 세션
        admin_user: 현재 슈퍼관리자

    Returns:
        정리된 로그 수
    """
    try:
        from datetime import timedelta

        from sqlalchemy import func

        cutoff_date = datetime.now() - timedelta(days=days)

        # 삭제할 로그 수 조회
        delete_count = (
            db.query(func.count(SystemLog.log_id))
            .filter(SystemLog.created_at < cutoff_date)
            .scalar()
            or 0
        )

        if delete_count == 0:
            return {
                "success": True,
                "data": {"deleted_count": 0},
                "message": f"{days}일 이전의 로그가 없습니다.",
                "error": None,
                "meta": None,
                "timestamp": datetime.now().isoformat(),
            }

        # 오래된 로그 삭제
        db.query(SystemLog).filter(SystemLog.created_at < cutoff_date).delete()
        db.commit()

        logger.info(
            f"관리자 로그 정리 완료: {delete_count}개 삭제 (관리자: {admin_user.admin_id})"
        )

        return {
            "success": True,
            "data": {"deleted_count": delete_count},
            "message": f"{days}일 이전의 로그 {delete_count}개를 정리했습니다.",
            "error": None,
            "meta": None,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"관리자 로그 정리 실패: {e}")
        raise HTTPException(
            status_code=500, detail="관리자 로그 정리 중 오류가 발생했습니다."
        )
