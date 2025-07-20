"""
알림 서비스
관리자 백엔드에서 사용자에게 알림을 전송하는 서비스
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import asyncio
import logging

from app.models import (
    User,
    UserNotificationSettings,
    UserDeviceToken,
    Notification,
    NotificationStatus,
    NotificationType,
    NotificationChannel
)
from app.services.fcm_service import FCMService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class NotificationService:
    """알림 서비스 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.fcm_service = FCMService()
        self.email_service = EmailService()
    
    async def create_notification(
        self,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        channel: NotificationChannel,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        scheduled_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None
    ) -> Notification:
        """알림 생성"""
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type.value,
            title=title,
            body=message,
            data=data or {},
            status='pending'
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        logger.info(f"Notification created: {notification.log_id}")
        
        return notification
    
    async def send_notification(self, notification: Notification, channel: NotificationChannel = NotificationChannel.PUSH) -> bool:
        """개별 알림 전송"""
        try:
            # 사용자 알림 설정 확인
            settings = self.db.query(UserNotificationSettings).filter(
                UserNotificationSettings.user_id == notification.user_id
            ).first()
            
            # 채널별 전송
            success = False
            # FCMNotificationLog는 기본적으로 푸시 알림용이므로 채널 구분 없이 처리
            if channel == NotificationChannel.PUSH:
                success = await self._send_push_notification(notification, settings)
            elif channel == NotificationChannel.EMAIL:
                success = await self._send_email_notification(notification, settings)
            elif channel == NotificationChannel.IN_APP:
                success = await self._send_in_app_notification(notification)
            
            if success:
                notification.status = 'sent'
                notification.sent_at = datetime.utcnow()
                logger.info(f"Notification sent successfully: {notification.log_id}")
            else:
                notification.status = 'failed'
                logger.error(f"Failed to send notification: {notification.log_id}")
            
            self.db.commit()
            return success
            
        except Exception as e:
            logger.error(f"Error sending notification {notification.log_id}: {str(e)}")
            notification.status = 'failed'
            notification.error_message = str(e)
            self.db.commit()
            return False
    
    async def _send_push_notification(self, notification: Notification, settings: Optional[UserNotificationSettings]) -> bool:
        """푸시 알림 전송"""
        # 설정 확인
        if settings and not settings.push_enabled:
            return False
        
        # 사용자 디바이스 토큰 조회
        tokens = self.db.query(UserDeviceToken).filter(
            UserDeviceToken.user_id == notification.user_id,
            UserDeviceToken.is_active == True
        ).all()
        
        if not tokens:
            logger.warning(f"No active device tokens for user {notification.user_id}")
            return False
        
        success_count = 0
        
        for token in tokens:
            try:
                result = await self.fcm_service.send_notification(
                    token=token.device_token,
                    title=notification.title,
                    body=notification.body,
                    data=notification.data
                )
                
                if result:
                    success_count += 1
                    token.last_used = func.now()
                    
            except Exception as e:
                logger.error(f"Error sending push notification to token {token.id}: {str(e)}")
                # 토큰이 유효하지 않으면 비활성화
                if "invalid" in str(e).lower() or "not registered" in str(e).lower():
                    token.is_active = False
        
        self.db.commit()
        return success_count > 0
    
    async def _send_email_notification(self, notification: Notification, settings: Optional[UserNotificationSettings]) -> bool:
        """이메일 알림 전송"""
        # 설정 확인
        if settings and not settings.email_enabled:
            return False
        
        # 사용자 이메일 조회
        user = self.db.query(User).filter(User.user_id == notification.user_id).first()
        if not user:
            return False
        
        try:
            # 문의 답변 알림인 경우 특별 처리
            if notification.notification_type == NotificationType.CONTACT_ANSWER.value:
                # 답변 내용 추출
                answer_content = notification.data.get('answer_content', notification.body)
                
                return await self.email_service.send_contact_answer_email(
                    to_email=user.email,
                    contact_title=notification.data.get('contact_title', ''),
                    answer_content=answer_content,
                    contact_id=notification.data.get('contact_id', 0)
                )
            else:
                # 일반 알림 이메일 전송
                return await self.email_service.send_notification_email(
                    to_email=user.email,
                    subject=notification.title,
                    content=notification.message
                )
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False
    
    async def _send_in_app_notification(self, notification: Notification) -> bool:
        """인앱 알림 전송"""
        # 인앱 알림은 데이터베이스에 저장하는 것으로 처리
        notification.status = NotificationStatus.DELIVERED
        notification.delivered_at = func.now()
        return True
    
    async def send_contact_answer_notification(
        self,
        user: User,
        contact_title: str,
        answer_content: str,
        contact_id: int,
        user_settings: Optional[UserNotificationSettings] = None
    ) -> Dict[str, bool]:
        """문의 답변 알림 전송 (모든 활성 채널)"""
        results = {
            "push": False,
            "email": False,
            "in_app": False
        }
        
        # 기본 설정이 없으면 모든 채널 활성화
        if not user_settings:
            user_settings = UserNotificationSettings(
                push_enabled=True,
                email_enabled=True,
                in_app_enabled=True,
                system_messages=True
            )
        
        notification_data = {
            "contact_id": contact_id,
            "contact_title": contact_title,
            "answer_content": answer_content[:500]  # 답변 내용 요약
        }
        
        # 푸시 알림
        if user_settings.push_enabled and user_settings.system_messages:
            push_notification = await self.create_notification(
                user_id=user.user_id,
                notification_type=NotificationType.CONTACT_ANSWER,
                channel=NotificationChannel.PUSH,
                title="문의하신 내용에 답변이 등록되었습니다",
                message=f"'{contact_title}' 문의에 대한 답변이 등록되었습니다.",
                data=notification_data,
                priority=7
            )
            results["push"] = await self.send_notification(push_notification, NotificationChannel.PUSH)
        
        # 이메일 알림
        if user_settings.email_enabled and user_settings.system_messages:
            email_notification = await self.create_notification(
                user_id=user.user_id,
                notification_type=NotificationType.CONTACT_ANSWER,
                channel=NotificationChannel.EMAIL,
                title="문의하신 내용에 답변이 등록되었습니다",
                message=answer_content,
                data=notification_data,
                priority=7
            )
            results["email"] = await self.send_notification(email_notification, NotificationChannel.EMAIL)
        
        # 인앱 알림 (항상 생성)
        if user_settings.in_app_enabled:
            in_app_notification = await self.create_notification(
                user_id=user.user_id,
                notification_type=NotificationType.CONTACT_ANSWER,
                channel=NotificationChannel.IN_APP,
                title="문의하신 내용에 답변이 등록되었습니다",
                message=f"'{contact_title}' 문의에 대한 답변이 등록되었습니다. 확인해보세요!",
                data=notification_data,
                priority=7
            )
            results["in_app"] = await self.send_notification(in_app_notification, NotificationChannel.IN_APP)
        
        return results