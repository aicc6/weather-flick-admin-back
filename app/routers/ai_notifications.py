"""
스마트 알림 시스템 API 라우터
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.ai.notification_system import (
    NotificationPriority,
    NotificationType,
    UserNotificationPreferences,
    get_notification_system,
)
from app.auth.dependencies import get_current_admin
from app.database import get_db
from app.logging_config import get_logger
from app.utils.cache import CACHE_PREFIX, CACHE_TTL, cache_result

logger = get_logger("ai_notifications_router")

router = APIRouter(prefix="/ai/notifications", tags=["AI Notifications"])


class NotificationRequest(BaseModel):
    """알림 요청 모델"""

    user_id: str | None = Field(None, description="사용자 ID (관리자용)")
    notification_types: list[str] | None = Field(None, description="알림 유형 필터")
    priority: str | None = Field(None, description="우선순위 필터")
    limit: int = Field(10, ge=1, le=100, description="조회할 알림 수")


class NotificationResponse(BaseModel):
    """알림 응답 모델"""

    notification_id: str
    user_id: str
    type: str
    priority: str
    title: str
    content: str
    data: dict[str, Any] | None = None
    scheduled_time: datetime | None = None
    created_at: datetime
    is_read: bool = False
    channel: str = "app"


class NotificationPreferencesRequest(BaseModel):
    """알림 설정 요청 모델"""

    enabled: bool = True
    weather_alerts: bool = True
    travel_reminders: bool = True
    recommendations: bool = True
    price_alerts: bool = False
    social_updates: bool = False
    quiet_hours: dict[str, str] = {"start": "22:00", "end": "08:00"}
    preferred_channels: list[str] = ["app", "email"]
    frequency: str = "realtime"


class NotificationStatsResponse(BaseModel):
    """알림 통계 응답 모델"""

    total_notifications: int
    unread_count: int
    by_type: dict[str, int]
    by_priority: dict[str, int]
    delivery_rate: float
    open_rate: float


@router.get("/", response_model=list[NotificationResponse])
@cache_result(ttl=CACHE_TTL["SHORT"], prefix=CACHE_PREFIX["NOTIFICATIONS"])
async def get_user_notifications(
    skip: int = Query(0, ge=0, description="건너뛸 알림 수"),
    limit: int = Query(10, ge=1, le=100, description="조회할 알림 수"),
    notification_type: str | None = Query(None, description="알림 유형 필터"),
    priority: str | None = Query(None, description="우선순위 필터"),
    unread_only: bool = Query(False, description="읽지 않은 알림만 조회"),
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """사용자 알림 조회"""
    try:
        # 실제 구현에서는 데이터베이스에서 알림 조회
        # 여기서는 예시 데이터 반환
        notifications = []

        # 알림 생성 (실제로는 DB에서 조회)
        notification_system = get_notification_system(db)
        generated_notifications = await notification_system.generate_user_notifications(
            current_user["user_id"]
        )

        # 응답 형식으로 변환
        for i, notification in enumerate(generated_notifications[:limit]):
            notifications.append(
                NotificationResponse(
                    notification_id=f"notif_{i}",
                    user_id=notification.user_id,
                    type=notification.type.value,
                    priority=notification.priority.value,
                    title=notification.title,
                    content=notification.content,
                    data=notification.data,
                    scheduled_time=notification.scheduled_time,
                    created_at=datetime.now(),
                    is_read=False,
                    channel=notification.channel,
                )
            )

        return notifications

    except Exception as e:
        logger.error(f"Error getting user notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notifications")


@router.post("/generate")
async def generate_notifications(
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """사용자 알림 생성"""
    try:
        notification_system = get_notification_system(db)

        # 백그라운드에서 알림 생성 및 전송
        background_tasks.add_task(
            notification_system.generate_user_notifications, current_user["user_id"]
        )

        return {
            "success": True,
            "message": "알림 생성이 시작되었습니다.",
            "user_id": current_user["user_id"],
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error generating notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate notifications")


@router.post("/batch-generate")
async def batch_generate_notifications(
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """전체 사용자 알림 배치 생성 (관리자용)"""
    try:
        # 관리자 권한 확인
        # 관리자 백엔드에서는 이미 관리자 인증 완료

        notification_system = get_notification_system(db)

        # 백그라운드에서 전체 사용자 알림 처리
        background_tasks.add_task(notification_system.process_all_user_notifications)

        return {
            "success": True,
            "message": "전체 사용자 알림 배치 생성이 시작되었습니다.",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in batch notification generation: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate batch notifications"
        )


@router.get("/preferences")
async def get_notification_preferences(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """사용자 알림 설정 조회"""
    try:
        preferences = UserNotificationPreferences(current_user["user_id"], db)

        return {
            "success": True,
            "data": preferences.preferences,
            "user_id": current_user["user_id"],
        }

    except Exception as e:
        logger.error(f"Error getting notification preferences: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get notification preferences"
        )


@router.put("/preferences")
async def update_notification_preferences(
    preferences_request: NotificationPreferencesRequest,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """사용자 알림 설정 업데이트"""
    try:
        # 실제 구현에서는 데이터베이스에 설정 저장
        updated_preferences = preferences_request.dict()

        # 설정 유효성 검사
        if updated_preferences.get("frequency") not in ["realtime", "daily", "weekly"]:
            raise HTTPException(status_code=400, detail="Invalid frequency setting")

        # 데이터베이스 업데이트 (실제 구현에서는 user_notification_preferences 테이블)
        logger.info(
            f"Updating notification preferences for user {current_user['user_id']}"
        )

        return {
            "success": True,
            "message": "알림 설정이 업데이트되었습니다.",
            "data": updated_preferences,
            "user_id": current_user["user_id"],
        }

    except Exception as e:
        logger.error(f"Error updating notification preferences: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update notification preferences"
        )


@router.post("/mark-read/{notification_id}")
async def mark_notification_as_read(
    notification_id: str,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """알림 읽음 처리"""
    try:
        # 실제 구현에서는 데이터베이스에서 알림 상태 업데이트
        logger.info(
            f"Marking notification {notification_id} as read for user {current_user['user_id']}"
        )

        return {
            "success": True,
            "message": "알림이 읽음 처리되었습니다.",
            "notification_id": notification_id,
            "user_id": current_user["user_id"],
        }

    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to mark notification as read"
        )


@router.post("/mark-all-read")
async def mark_all_notifications_as_read(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """모든 알림 읽음 처리"""
    try:
        # 실제 구현에서는 데이터베이스에서 모든 알림 상태 업데이트
        logger.info(
            f"Marking all notifications as read for user {current_user['user_id']}"
        )

        return {
            "success": True,
            "message": "모든 알림이 읽음 처리되었습니다.",
            "user_id": current_user["user_id"],
        }

    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to mark all notifications as read"
        )


@router.get("/stats", response_model=NotificationStatsResponse)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["STATS"])
async def get_notification_statistics(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """알림 통계 조회"""
    try:
        notification_system = get_notification_system(db)
        stats = notification_system.get_notification_statistics()

        return NotificationStatsResponse(
            total_notifications=stats.get("total_notifications", 0),
            unread_count=stats.get("unread_count", 0),
            by_type=stats.get("by_type", {}),
            by_priority=stats.get("by_priority", {}),
            delivery_rate=stats.get("delivery_rate", 0.0),
            open_rate=stats.get("open_rate", 0.0),
        )

    except Exception as e:
        logger.error(f"Error getting notification statistics: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get notification statistics"
        )


@router.get("/types")
async def get_notification_types():
    """알림 유형 목록 조회"""
    try:
        types = [
            {
                "value": notification_type.value,
                "name": notification_type.name,
                "description": _get_type_description(notification_type),
            }
            for notification_type in NotificationType
        ]

        return {
            "success": True,
            "data": types,
            "count": len(types),
        }

    except Exception as e:
        logger.error(f"Error getting notification types: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notification types")


@router.get("/priorities")
async def get_notification_priorities():
    """알림 우선순위 목록 조회"""
    try:
        priorities = [
            {
                "value": priority.value,
                "name": priority.name,
                "description": _get_priority_description(priority),
            }
            for priority in NotificationPriority
        ]

        return {
            "success": True,
            "data": priorities,
            "count": len(priorities),
        }

    except Exception as e:
        logger.error(f"Error getting notification priorities: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get notification priorities"
        )


@router.delete("/clear-all")
async def clear_all_notifications(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """모든 알림 삭제"""
    try:
        # 실제 구현에서는 데이터베이스에서 알림 삭제
        logger.info(f"Clearing all notifications for user {current_user['user_id']}")

        return {
            "success": True,
            "message": "모든 알림이 삭제되었습니다.",
            "user_id": current_user["user_id"],
        }

    except Exception as e:
        logger.error(f"Error clearing all notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear all notifications")


def _get_type_description(notification_type: NotificationType) -> str:
    """알림 유형 설명 반환"""
    descriptions = {
        NotificationType.WEATHER_UPDATE: "날씨 업데이트 알림",
        NotificationType.TRAVEL_REMINDER: "여행 알림",
        NotificationType.DESTINATION_ALERT: "여행지 알림",
        NotificationType.PERSONALIZED_RECOMMENDATION: "개인화 추천 알림",
        NotificationType.PRICE_ALERT: "가격 알림",
        NotificationType.SOCIAL_UPDATE: "소셜 업데이트",
        NotificationType.SYSTEM_NOTIFICATION: "시스템 알림",
    }
    return descriptions.get(notification_type, "알림")


def _get_priority_description(priority: NotificationPriority) -> str:
    """알림 우선순위 설명 반환"""
    descriptions = {
        NotificationPriority.HIGH: "높음 - 즉시 알림",
        NotificationPriority.MEDIUM: "보통 - 일반 알림",
        NotificationPriority.LOW: "낮음 - 배치 알림",
    }
    return descriptions.get(priority, "일반")


logger.info("AI notifications router initialized")
