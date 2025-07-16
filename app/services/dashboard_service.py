"""
관리자 대시보드 데이터 서비스
Cursor 규칙에 따른 종합 대시보드 서비스 구현
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth.logging import AdminLogService
from ..models import EventLog, User
from ..models_admin import Admin

logger = logging.getLogger(__name__)


class DashboardService:
    """관리자 대시보드 데이터 서비스"""

    def __init__(self, db: Session):
        self.db = db

    async def get_dashboard_stats(self) -> dict[str, Any]:
        """대시보드 종합 통계"""
        try:
            # 시간 범위 설정
            now = datetime.utcnow()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)

            # 사용자 통계
            user_stats = await self._get_user_statistics(today, week_ago, month_ago)

            # 관리자 통계
            admin_stats = await self._get_admin_statistics(today, week_ago)

            # 시스템 통계
            system_stats = await self._get_system_statistics()

            # 활동 통계
            activity_stats = await self._get_activity_statistics(today)

            return {
                "timestamp": now.isoformat(),
                "users": user_stats,
                "admins": admin_stats,
                "system": system_stats,
                "activities": activity_stats,
            }

        except Exception as e:
            logger.error(f"대시보드 통계 조회 실패: {e}")
            raise

    async def _get_user_statistics(
        self, today: datetime, week_ago: datetime, month_ago: datetime
    ) -> dict[str, Any]:
        """사용자 관련 통계"""
        try:
            # 전체 사용자 수
            total_users = self.db.query(func.count(User.user_id)).scalar() or 0

            # 오늘 신규 가입자
            new_today = (
                self.db.query(func.count(User.user_id))
                .filter(User.created_at >= today)
                .scalar()
                or 0
            )

            # 주간 신규 가입자
            new_week = (
                self.db.query(func.count(User.user_id))
                .filter(User.created_at >= week_ago)
                .scalar()
                or 0
            )

            # 월간 신규 가입자
            new_month = (
                self.db.query(func.count(User.user_id))
                .filter(User.created_at >= month_ago)
                .scalar()
                or 0
            )

            # 활성 사용자 수
            active_users = (
                self.db.query(func.count(User.user_id)).filter(User.is_active).scalar()
                or 0
            )

            # 인증된 사용자 수
            verified_users = (
                self.db.query(func.count(User.user_id))
                .filter(User.is_email_verified)
                .scalar()
                or 0
            )

            return {
                "total": total_users,
                "new_today": new_today,
                "new_week": new_week,
                "new_month": new_month,
                "active": active_users,
                "verified": verified_users,
                "growth_rate_week": round((new_week / total_users * 100), 2)
                if total_users > 0
                else 0,
                "verification_rate": round((verified_users / total_users * 100), 2)
                if total_users > 0
                else 0,
            }

        except Exception as e:
            logger.error(f"사용자 통계 조회 실패: {e}")
            return {}

    async def _get_admin_statistics(
        self, today: datetime, week_ago: datetime
    ) -> dict[str, Any]:
        """관리자 관련 통계"""
        try:
            # 전체 관리자 수
            total_admins = self.db.query(func.count(Admin.admin_id)).scalar() or 0

            # 활성 관리자 수
            active_admins = (
                self.db.query(func.count(Admin.admin_id))
                .filter(Admin.status == "ACTIVE")
                .scalar()
                or 0
            )

            # 주간 활동한 관리자 수 (로그 기준)
            active_week_admins = (
                self.db.query(func.count(func.distinct(EventLog.admin_id)))
                .filter(
                    EventLog.created_at >= week_ago,
                    EventLog.event_type == "admin_action",
                )
                .scalar()
                or 0
            )

            return {
                "total": total_admins,
                "active": active_admins,
                "active_this_week": active_week_admins,
                "activity_rate": round((active_week_admins / active_admins * 100), 2)
                if active_admins > 0
                else 0,
            }

        except Exception as e:
            logger.error(f"관리자 통계 조회 실패: {e}")
            return {}

    async def _get_system_statistics(self) -> dict[str, Any]:
        """시스템 관련 통계"""
        try:
            # 데이터베이스 연결 테스트
            db_status = "healthy"
            try:
                # 간단한 쿼리로 DB 연결 확인
                from sqlalchemy import text

                self.db.execute(text("SELECT 1"))
                db_status = "healthy"
            except Exception:
                db_status = "error"

            # CityWeatherData 테이블이 제거되어 관련 통계를 제외합니다.
            # 날씨 데이터는 이제 weather_forecast 테이블에서 관리됩니다.
            weather_data_count = 0
            latest_weather = None

            return {
                "weather_data_count": weather_data_count,
                "latest_weather_time": latest_weather.isoformat()
                if latest_weather
                else None,
                "database_status": db_status,
            }

        except Exception as e:
            logger.error(f"시스템 통계 조회 실패: {e}")
            return {"database_status": "error"}

    async def _get_activity_statistics(self, today: datetime) -> dict[str, Any]:
        """활동 통계"""
        try:
            log_service = AdminLogService(self.db)
            activity_stats = log_service.get_activity_statistics()

            # 최근 중요 활동 조회
            critical_activities = log_service.get_recent_activities(
                limit=10, severity="CRITICAL"
            )

            return {**activity_stats, "recent_critical_count": len(critical_activities)}

        except Exception as e:
            logger.error(f"활동 통계 조회 실패: {e}")
            return {}

    async def get_recent_activities(self, limit: int = 20) -> list[dict[str, Any]]:
        """최근 관리자 활동 내역 (대시보드용)"""
        try:
            log_service = AdminLogService(self.db)
            activities = log_service.get_recent_activities(limit=limit)

            activity_list = []
            for activity in activities:
                event_data = activity.event_data or {}
                activity_list.append(
                    {
                        "admin_email": activity.admin.email
                        if activity.admin
                        else "Unknown",
                        "action": activity.event_name,
                        "description": event_data.get("description", ""),
                        "severity": event_data.get("severity", "NORMAL"),
                        "created_at": activity.created_at.isoformat(),
                    }
                )

            return activity_list

        except Exception as e:
            logger.error(f"관리자 활동 내역 조회 실패: {e}")
            return []
