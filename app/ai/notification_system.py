"""
스마트 알림 시스템
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Review, TravelPlan, User

logger = get_logger("notification_system")


class NotificationType(Enum):
    """알림 유형"""

    WEATHER_UPDATE = "weather_update"
    TRAVEL_REMINDER = "travel_reminder"
    DESTINATION_ALERT = "destination_alert"
    PERSONALIZED_RECOMMENDATION = "personalized_recommendation"
    PRICE_ALERT = "price_alert"
    SOCIAL_UPDATE = "social_update"
    SYSTEM_NOTIFICATION = "system_notification"


class NotificationPriority(Enum):
    """알림 우선순위"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class NotificationMessage:
    """알림 메시지"""

    user_id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    content: str
    data: dict[str, Any] | None = None
    scheduled_time: datetime | None = None
    expires_at: datetime | None = None
    channel: str = "app"  # app, email, sms, push


class UserNotificationPreferences:
    """사용자 알림 설정"""

    def __init__(self, user_id: str, db: Session):
        self.user_id = user_id
        self.db = db
        self.preferences = self._load_preferences()

    def _load_preferences(self) -> dict[str, Any]:
        """사용자 알림 설정 로드"""
        # 실제 구현에서는 user_notification_preferences 테이블에서 로드
        return {
            "enabled": True,
            "weather_alerts": True,
            "travel_reminders": True,
            "recommendations": True,
            "price_alerts": False,
            "social_updates": False,
            "quiet_hours": {"start": "22:00", "end": "08:00"},
            "preferred_channels": ["app", "email"],
            "frequency": "realtime",  # realtime, daily, weekly
        }

    def is_notification_enabled(self, notification_type: NotificationType) -> bool:
        """특정 알림 유형이 활성화되어 있는지 확인"""
        if not self.preferences.get("enabled", True):
            return False

        type_mapping = {
            NotificationType.WEATHER_UPDATE: "weather_alerts",
            NotificationType.TRAVEL_REMINDER: "travel_reminders",
            NotificationType.DESTINATION_ALERT: "weather_alerts",
            NotificationType.PERSONALIZED_RECOMMENDATION: "recommendations",
            NotificationType.PRICE_ALERT: "price_alerts",
            NotificationType.SOCIAL_UPDATE: "social_updates",
            NotificationType.SYSTEM_NOTIFICATION: "enabled",
        }

        setting_key = type_mapping.get(notification_type, "enabled")
        return self.preferences.get(setting_key, True)

    def is_quiet_hours(self, current_time: datetime = None) -> bool:
        """현재 시간이 조용한 시간인지 확인"""
        if not current_time:
            current_time = datetime.now()

        quiet_hours = self.preferences.get("quiet_hours")
        if not quiet_hours:
            return False

        start_time = datetime.strptime(quiet_hours["start"], "%H:%M").time()
        end_time = datetime.strptime(quiet_hours["end"], "%H:%M").time()
        current_time_only = current_time.time()

        if start_time <= end_time:
            return start_time <= current_time_only <= end_time
        else:
            return current_time_only >= start_time or current_time_only <= end_time


class WeatherNotificationGenerator:
    """날씨 알림 생성기"""

    def __init__(self, db: Session):
        self.db = db

    async def generate_weather_alerts(self, user_id: str) -> list[NotificationMessage]:
        """날씨 알림 생성"""
        notifications = []

        try:
            # 사용자의 예정된 여행 계획 조회
            upcoming_plans = self._get_upcoming_travel_plans(user_id)

            for plan in upcoming_plans:
                # 각 여행 계획에 대한 날씨 알림 생성
                weather_notifications = await self._generate_plan_weather_alerts(
                    user_id, plan
                )
                notifications.extend(weather_notifications)

        except Exception as e:
            logger.error(f"Error generating weather alerts: {e}")

        return notifications

    def _get_upcoming_travel_plans(self, user_id: str) -> list[TravelPlan]:
        """다가오는 여행 계획 조회"""
        tomorrow = datetime.now() + timedelta(days=1)
        week_later = datetime.now() + timedelta(days=7)

        return (
            self.db.query(TravelPlan)
            .filter(
                and_(
                    TravelPlan.user_id == user_id,
                    TravelPlan.start_date >= tomorrow,
                    TravelPlan.start_date <= week_later,
                )
            )
            .all()
        )

    async def _generate_plan_weather_alerts(
        self, user_id: str, plan: TravelPlan
    ) -> list[NotificationMessage]:
        """특정 여행 계획에 대한 날씨 알림 생성"""
        notifications = []

        # 여행 시작 3일 전 날씨 예보
        alert_date = plan.start_date - timedelta(days=3)
        if alert_date >= datetime.now():
            notifications.append(
                NotificationMessage(
                    user_id=user_id,
                    type=NotificationType.WEATHER_UPDATE,
                    priority=NotificationPriority.MEDIUM,
                    title="여행 날씨 예보 업데이트",
                    content=f"{plan.title} 여행 3일 전 날씨 예보를 확인해보세요.",
                    data={"travel_plan_id": plan.plan_id, "days_before": 3},
                    scheduled_time=alert_date,
                )
            )

        # 여행 시작 1일 전 날씨 알림
        alert_date = plan.start_date - timedelta(days=1)
        if alert_date >= datetime.now():
            notifications.append(
                NotificationMessage(
                    user_id=user_id,
                    type=NotificationType.WEATHER_UPDATE,
                    priority=NotificationPriority.HIGH,
                    title="내일 여행 날씨 확인",
                    content=f"{plan.title} 여행 내일 날씨를 확인하고 준비하세요.",
                    data={"travel_plan_id": plan.plan_id, "days_before": 1},
                    scheduled_time=alert_date,
                )
            )

        return notifications


class TravelReminderGenerator:
    """여행 알림 생성기"""

    def __init__(self, db: Session):
        self.db = db

    async def generate_travel_reminders(
        self, user_id: str
    ) -> list[NotificationMessage]:
        """여행 알림 생성"""
        notifications = []

        try:
            # 체크인 알림
            checkin_reminders = await self._generate_checkin_reminders(user_id)
            notifications.extend(checkin_reminders)

            # 준비물 알림
            preparation_reminders = await self._generate_preparation_reminders(user_id)
            notifications.extend(preparation_reminders)

            # 여행 후 리뷰 알림
            review_reminders = await self._generate_review_reminders(user_id)
            notifications.extend(review_reminders)

        except Exception as e:
            logger.error(f"Error generating travel reminders: {e}")

        return notifications

    async def _generate_checkin_reminders(
        self, user_id: str
    ) -> list[NotificationMessage]:
        """체크인 알림 생성"""
        notifications = []

        # 여행 시작 1일 전 체크인 알림
        tomorrow = datetime.now() + timedelta(days=1)
        plans = (
            self.db.query(TravelPlan)
            .filter(
                and_(
                    TravelPlan.user_id == user_id,
                    TravelPlan.start_date >= tomorrow,
                    TravelPlan.start_date <= tomorrow + timedelta(days=1),
                )
            )
            .all()
        )

        for plan in plans:
            notifications.append(
                NotificationMessage(
                    user_id=user_id,
                    type=NotificationType.TRAVEL_REMINDER,
                    priority=NotificationPriority.HIGH,
                    title="여행 체크인 알림",
                    content=f"{plan.title} 여행이 내일 시작됩니다. 체크인 준비를 해주세요.",
                    data={"travel_plan_id": plan.plan_id, "reminder_type": "checkin"},
                    scheduled_time=datetime.now(),
                )
            )

        return notifications

    async def _generate_preparation_reminders(
        self, user_id: str
    ) -> list[NotificationMessage]:
        """준비물 알림 생성"""
        notifications = []

        # 여행 시작 2일 전 준비물 알림
        day_after_tomorrow = datetime.now() + timedelta(days=2)
        plans = (
            self.db.query(TravelPlan)
            .filter(
                and_(
                    TravelPlan.user_id == user_id,
                    TravelPlan.start_date >= day_after_tomorrow,
                    TravelPlan.start_date <= day_after_tomorrow + timedelta(days=1),
                )
            )
            .all()
        )

        for plan in plans:
            notifications.append(
                NotificationMessage(
                    user_id=user_id,
                    type=NotificationType.TRAVEL_REMINDER,
                    priority=NotificationPriority.MEDIUM,
                    title="여행 준비물 체크",
                    content=f"{plan.title} 여행 준비물을 미리 준비해보세요.",
                    data={
                        "travel_plan_id": plan.plan_id,
                        "reminder_type": "preparation",
                    },
                    scheduled_time=datetime.now(),
                )
            )

        return notifications

    async def _generate_review_reminders(
        self, user_id: str
    ) -> list[NotificationMessage]:
        """리뷰 알림 생성"""
        notifications = []

        # 여행 종료 후 1일 후 리뷰 알림
        yesterday = datetime.now() - timedelta(days=1)
        completed_plans = (
            self.db.query(TravelPlan)
            .filter(
                and_(
                    TravelPlan.user_id == user_id,
                    TravelPlan.end_date >= yesterday - timedelta(days=1),
                    TravelPlan.end_date <= yesterday,
                )
            )
            .all()
        )

        for plan in completed_plans:
            # 이미 리뷰를 작성했는지 확인
            existing_review = (
                self.db.query(Review).filter(Review.user_id == user_id).first()
            )

            if not existing_review:
                notifications.append(
                    NotificationMessage(
                        user_id=user_id,
                        type=NotificationType.TRAVEL_REMINDER,
                        priority=NotificationPriority.LOW,
                        title="여행 후기 작성",
                        content=f"{plan.title} 여행은 어떠셨나요? 후기를 작성해보세요.",
                        data={
                            "travel_plan_id": plan.plan_id,
                            "reminder_type": "review",
                        },
                        scheduled_time=datetime.now(),
                    )
                )

        return notifications


class PersonalizedRecommendationGenerator:
    """개인화 추천 알림 생성기"""

    def __init__(self, db: Session):
        self.db = db

    async def generate_recommendation_notifications(
        self, user_id: str
    ) -> list[NotificationMessage]:
        """개인화 추천 알림 생성"""
        notifications = []

        try:
            # AI 추천 기반 알림
            ai_recommendations = await self._generate_ai_recommendations(user_id)
            notifications.extend(ai_recommendations)

            # 계절별 추천 알림
            seasonal_recommendations = await self._generate_seasonal_recommendations(
                user_id
            )
            notifications.extend(seasonal_recommendations)

            # 트렌드 기반 추천 알림
            trend_recommendations = await self._generate_trend_recommendations(user_id)
            notifications.extend(trend_recommendations)

        except Exception as e:
            logger.error(f"Error generating recommendation notifications: {e}")

        return notifications

    async def _generate_ai_recommendations(
        self, user_id: str
    ) -> list[NotificationMessage]:
        """AI 추천 알림 생성"""
        # 실제 구현에서는 AI 추천 엔진과 연동
        return [
            NotificationMessage(
                user_id=user_id,
                type=NotificationType.PERSONALIZED_RECOMMENDATION,
                priority=NotificationPriority.MEDIUM,
                title="맞춤 여행지 추천",
                content="당신의 취향에 맞는 새로운 여행지를 발견했습니다!",
                data={"recommendation_type": "ai_based"},
                scheduled_time=datetime.now(),
            )
        ]

    async def _generate_seasonal_recommendations(
        self, user_id: str
    ) -> list[NotificationMessage]:
        """계절별 추천 알림 생성"""
        current_month = datetime.now().month

        seasonal_messages = {
            3: "봄꽃 여행지 추천",
            6: "여름 휴가지 추천",
            9: "가을 단풍 여행지 추천",
            12: "겨울 여행지 추천",
        }

        if current_month in seasonal_messages:
            return [
                NotificationMessage(
                    user_id=user_id,
                    type=NotificationType.PERSONALIZED_RECOMMENDATION,
                    priority=NotificationPriority.LOW,
                    title=seasonal_messages[current_month],
                    content="이 계절에 특별한 여행지를 추천해드립니다.",
                    data={"recommendation_type": "seasonal", "month": current_month},
                    scheduled_time=datetime.now(),
                )
            ]

        return []

    async def _generate_trend_recommendations(
        self, user_id: str
    ) -> list[NotificationMessage]:
        """트렌드 기반 추천 알림 생성"""
        return [
            NotificationMessage(
                user_id=user_id,
                type=NotificationType.PERSONALIZED_RECOMMENDATION,
                priority=NotificationPriority.LOW,
                title="인기 급상승 여행지",
                content="요즘 인기 급상승하는 여행지를 확인해보세요!",
                data={"recommendation_type": "trending"},
                scheduled_time=datetime.now(),
            )
        ]


class SmartNotificationSystem:
    """스마트 알림 시스템 메인 클래스"""

    def __init__(self, db: Session):
        self.db = db
        self.weather_generator = WeatherNotificationGenerator(db)
        self.travel_generator = TravelReminderGenerator(db)
        self.recommendation_generator = PersonalizedRecommendationGenerator(db)
        self.notification_queue = []

    async def generate_user_notifications(
        self, user_id: str
    ) -> list[NotificationMessage]:
        """사용자별 알림 생성"""
        try:
            # 사용자 알림 설정 확인
            preferences = UserNotificationPreferences(user_id, self.db)

            if not preferences.preferences.get("enabled", True):
                return []

            # 모든 알림 생성기 실행
            tasks = [
                self.weather_generator.generate_weather_alerts(user_id),
                self.travel_generator.generate_travel_reminders(user_id),
                self.recommendation_generator.generate_recommendation_notifications(
                    user_id
                ),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 통합
            all_notifications = []
            for result in results:
                if isinstance(result, list):
                    all_notifications.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error in notification generation: {result}")

            # 사용자 설정에 따른 필터링
            filtered_notifications = []
            for notification in all_notifications:
                if preferences.is_notification_enabled(notification.type):
                    # 조용한 시간 확인
                    if (
                        notification.priority == NotificationPriority.HIGH
                        or not preferences.is_quiet_hours()
                    ):
                        filtered_notifications.append(notification)

            return filtered_notifications

        except Exception as e:
            logger.error(f"Error generating user notifications: {e}")
            return []

    async def process_all_user_notifications(self) -> dict[str, Any]:
        """모든 사용자 알림 처리"""
        try:
            # 활성 사용자 조회
            active_users = self._get_active_users()

            total_notifications = 0
            processed_users = 0

            for user in active_users:
                try:
                    notifications = await self.generate_user_notifications(user.user_id)

                    if notifications:
                        # 알림 저장 및 전송
                        await self._save_and_send_notifications(notifications)
                        total_notifications += len(notifications)

                    processed_users += 1

                except Exception as e:
                    logger.error(
                        f"Error processing notifications for user {user.user_id}: {e}"
                    )
                    continue

            return {
                "processed_users": processed_users,
                "total_notifications": total_notifications,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error processing all user notifications: {e}")
            return {"error": str(e)}

    def _get_active_users(self) -> list[User]:
        """활성 사용자 조회"""
        # 최근 30일 내 활동한 사용자
        thirty_days_ago = datetime.now() - timedelta(days=30)

        return (
            self.db.query(User)
            .filter(User.last_login >= thirty_days_ago)
            .limit(1000)  # 배치 처리 제한
            .all()
        )

    async def _save_and_send_notifications(
        self, notifications: list[NotificationMessage]
    ):
        """알림 저장 및 전송"""
        try:
            for notification in notifications:
                # 데이터베이스에 알림 저장
                await self._save_notification(notification)

                # 알림 전송
                await self._send_notification(notification)

        except Exception as e:
            logger.error(f"Error saving and sending notifications: {e}")

    async def _save_notification(self, notification: NotificationMessage):
        """알림 데이터베이스 저장"""
        # 실제 구현에서는 notifications 테이블에 저장
        logger.info(
            f"Saving notification: {notification.title} for user {notification.user_id}"
        )

    async def _send_notification(self, notification: NotificationMessage):
        """알림 전송"""
        # 실제 구현에서는 푸시 알림, 이메일, SMS 등으로 전송
        logger.info(
            f"Sending notification: {notification.title} to user {notification.user_id}"
        )

    async def schedule_notification(self, notification: NotificationMessage):
        """알림 스케줄링"""
        if notification.scheduled_time:
            # 스케줄된 시간에 알림 전송
            delay = (notification.scheduled_time - datetime.now()).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)

        await self._save_and_send_notifications([notification])

    def get_notification_statistics(self) -> dict[str, Any]:
        """알림 통계"""
        # 실제 구현에서는 notifications 테이블에서 통계 조회
        return {
            "total_notifications": 0,
            "by_type": {},
            "by_priority": {},
            "delivery_rate": 0.0,
            "open_rate": 0.0,
        }


# 알림 시스템 싱글톤
notification_system = None


def get_notification_system(db: Session) -> SmartNotificationSystem:
    """알림 시스템 인스턴스 반환"""
    global notification_system
    if notification_system is None:
        notification_system = SmartNotificationSystem(db)
    return notification_system


logger.info("Smart notification system initialized")
