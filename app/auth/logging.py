"""
관리자 활동 로그 시스템
Cursor 규칙에 따른 관리자 활동 로깅 구현
"""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import AdminActivityLog

logger = logging.getLogger(__name__)

async def log_admin_activity(
    admin_id: int,
    action: str,
    description: str,
    target_resource: str | None = None,
    severity: str = "NORMAL",
    db: Session | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None
):
    """
    관리자 활동 로그 기록 (데이터베이스 저장 포함)
    
    Args:
        admin_id: 관리자 ID
        action: 수행된 작업 (예: USER_DELETE, USER_UPDATE)
        description: 작업 설명
        target_resource: 대상 리소스 (예: user_id, plan_id)
        severity: 심각도 (NORMAL, HIGH, CRITICAL)
        db: 데이터베이스 세션
        ip_address: IP 주소
        user_agent: 사용자 에이전트
    """
    try:
        # 로거로 기록
        logger.info(f"[ADMIN_LOG] {severity} - Admin {admin_id}: {action} - {description}")

        # 중요한 활동은 별도 경고 로그
        if severity in ["HIGH", "CRITICAL"]:
            logger.warning(f"[중요 관리자 활동] {description} (관리자: {admin_id}, 심각도: {severity})")

        # 데이터베이스에 로그 저장
        if db:
            try:
                admin_log = AdminActivityLog(
                    admin_id=admin_id,
                    action=action,
                    description=description,
                    target_resource=target_resource,
                    severity=severity,
                    ip_address=ip_address or "127.0.0.1",
                    user_agent=user_agent
                )
                db.add(admin_log)
                db.commit()
                logger.debug(f"관리자 활동 로그 DB 저장 완료: {action}")
            except Exception as db_error:
                logger.error(f"관리자 활동 로그 DB 저장 실패: {db_error}")
                db.rollback()
                # DB 저장 실패해도 로거 기록은 유지

    except Exception as e:
        logger.error(f"관리자 활동 로그 기록 실패: {e}")


class AdminLogService:
    """관리자 로그 관리 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def get_recent_activities(
        self,
        limit: int = 50,
        admin_id: int | None = None,
        severity: str | None = None
    ) -> list[AdminActivityLog]:
        """최근 관리자 활동 내역 조회"""
        try:
            query = self.db.query(AdminActivityLog)

            if admin_id:
                query = query.filter(AdminActivityLog.admin_id == admin_id)

            if severity:
                query = query.filter(AdminActivityLog.severity == severity)

            return query.order_by(AdminActivityLog.created_at.desc()).limit(limit).all()

        except Exception as e:
            logger.error(f"관리자 활동 내역 조회 실패: {e}")
            return []

    def get_activity_statistics(self) -> dict:
        """관리자 활동 통계"""
        try:
            from sqlalchemy import func

            # 오늘의 활동 수
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_activities = self.db.query(func.count(AdminActivityLog.log_id)).filter(
                AdminActivityLog.created_at >= today
            ).scalar() or 0

            # 심각도별 통계
            severity_stats = self.db.query(
                AdminActivityLog.severity,
                func.count(AdminActivityLog.log_id)
            ).group_by(AdminActivityLog.severity).all()

            return {
                "today_activities": today_activities,
                "severity_distribution": dict(severity_stats),
                "total_logs": self.db.query(func.count(AdminActivityLog.log_id)).scalar() or 0
            }

        except Exception as e:
            logger.error(f"관리자 활동 통계 조회 실패: {e}")
            return {}
