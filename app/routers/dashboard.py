"""
관리자 대시보드 라우터
Cursor 규칙에 따른 종합 대시보드 API
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth.rbac_dependencies import require_permission
from ..database import get_db
from ..models_admin import Admin
from ..services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_statistics(
    db: Session = Depends(get_db),
    admin_user: Admin = Depends(require_permission("dashboard.read")),
):
    """
    관리자 대시보드 종합 통계 조회 (관리자 전용)

    Returns:
        사용자, 관리자, 시스템, 활동 통계를 포함한 종합 대시보드 데이터
    """
    try:
        dashboard_service = DashboardService(db)
        stats = await dashboard_service.get_dashboard_stats()

        return {
            "success": True,
            "data": stats,
            "message": "대시보드 통계를 성공적으로 조회했습니다.",
            "error": None,
            "meta": None,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"대시보드 통계 조회 실패: {e}")
        raise HTTPException(
            status_code=500, detail="대시보드 통계 조회 중 오류가 발생했습니다."
        )


@router.get("/activities")
async def get_recent_dashboard_activities(
    limit: int = Query(20, ge=1, le=50, description="조회할 활동 수"),
    db: Session = Depends(get_db),
    admin_user: Admin = Depends(require_permission("dashboard.read")),
):
    """
    대시보드용 최근 관리자 활동 내역 조회 (관리자 전용)

    Args:
        limit: 조회할 활동 수 (1-50)
        db: 데이터베이스 세션
        admin_user: 현재 관리자

    Returns:
        최근 관리자 활동 내역 (요약 형태)
    """
    try:
        dashboard_service = DashboardService(db)
        activities = await dashboard_service.get_recent_activities(limit=limit)

        return {
            "success": True,
            "data": {"activities": activities, "total": len(activities)},
            "message": f"최근 관리자 활동 {len(activities)}개를 조회했습니다.",
            "error": None,
            "meta": None,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"대시보드 활동 내역 조회 실패: {e}")
        raise HTTPException(
            status_code=500, detail="대시보드 활동 내역 조회 중 오류가 발생했습니다."
        )


@router.get("/summary")
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    admin_user: Admin = Depends(require_permission("dashboard.read")),
):
    """
    대시보드 요약 정보 조회 (관리자 전용)

    핵심 지표만 포함한 요약 정보를 제공합니다.

    Returns:
        핵심 대시보드 지표 요약
    """
    try:
        dashboard_service = DashboardService(db)
        full_stats = await dashboard_service.get_dashboard_stats()

        # 핵심 지표만 추출
        summary = {
            "users": {
                "total": full_stats.get("users", {}).get("total", 0),
                "new_today": full_stats.get("users", {}).get("new_today", 0),
                "active": full_stats.get("users", {}).get("active", 0),
            },
            "admins": {
                "total": full_stats.get("admins", {}).get("total", 0),
                "active": full_stats.get("admins", {}).get("active", 0),
            },
            "system": {
                "status": full_stats.get("system", {}).get(
                    "database_status", "unknown"
                ),
                "weather_data_count": full_stats.get("system", {}).get(
                    "weather_data_count", 0
                ),
            },
            "activities": {
                "today_count": full_stats.get("activities", {}).get(
                    "today_activities", 0
                ),
                "critical_count": full_stats.get("activities", {}).get(
                    "recent_critical_count", 0
                ),
            },
        }

        return {
            "success": True,
            "data": summary,
            "message": "대시보드 요약 정보를 성공적으로 조회했습니다.",
            "error": None,
            "meta": None,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"대시보드 요약 조회 실패: {e}")
        raise HTTPException(
            status_code=500, detail="대시보드 요약 조회 중 오류가 발생했습니다."
        )
