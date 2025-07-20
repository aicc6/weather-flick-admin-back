"""
FCM (Firebase Cloud Messaging) 서비스
관리자 백엔드용 FCM 서비스
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.messaging import Message, Notification, AndroidConfig, APNSConfig, WebpushConfig

logger = logging.getLogger(__name__)


class FCMService:
    """FCM 푸시 알림 서비스 (HTTP v1 API)"""

    def __init__(self):
        # Firebase Admin SDK 초기화
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Firebase Admin SDK 초기화"""
        try:
            # 이미 초기화되어 있는지 확인
            if not firebase_admin._apps:
                # 서비스 계정 키 파일 경로
                cred_path = os.path.join(
                    os.path.dirname(__file__), 
                    "..", "..", "config", "firebase-service-account.json"
                )
                
                if not os.path.exists(cred_path):
                    logger.error(f"Firebase service account file not found: {cred_path}")
                    raise FileNotFoundError(f"Firebase service account file not found: {cred_path}")
                
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                logger.info("Firebase Admin SDK already initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")
            raise

    async def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image: Optional[str] = None,
        badge: Optional[int] = None,
        sound: str = "default",
        priority: str = "high",
    ) -> bool:
        """단일 디바이스에 푸시 알림 전송"""
        
        try:
            # 데이터 페이로드 준비 (모든 값은 문자열이어야 함)
            if data:
                data_payload = {k: str(v) for k, v in data.items()}
            else:
                data_payload = {}

            # FCM 메시지 생성
            message = Message(
                token=token,
                notification=Notification(
                    title=title,
                    body=body,
                    image=image
                ),
                data=data_payload,
                android=AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        sound=sound,
                        notification_count=badge
                    )
                ),
                apns=APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound=sound,
                            badge=badge
                        )
                    )
                ),
                webpush=WebpushConfig(
                    notification=messaging.WebpushNotification(
                        title=title,
                        body=body,
                        icon=image,
                        badge=str(badge) if badge else None
                    )
                )
            )

            # 메시지 전송
            response = messaging.send(message)
            logger.info(f"FCM notification sent successfully: {response}")
            return True

        except messaging.UnregisteredError:
            logger.error(f"FCM token is not registered: {token[:20]}...")
            return False
        except ValueError as e:
            logger.error(f"Invalid FCM message arguments: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending FCM notification: {str(e)}")
            return False

    async def send_multicast_notification(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image: Optional[str] = None,
        badge: Optional[int] = None,
        sound: str = "default",
        priority: str = "high",
    ) -> Dict[str, Any]:
        """다중 디바이스에 푸시 알림 전송"""
        
        if not tokens:
            return {"success": 0, "failure": 0, "results": []}

        try:
            # 데이터 페이로드 준비
            if data:
                data_payload = {k: str(v) for k, v in data.items()}
            else:
                data_payload = {}

            # MulticastMessage 생성
            message = messaging.MulticastMessage(
                tokens=tokens,
                notification=Notification(
                    title=title,
                    body=body,
                    image=image
                ),
                data=data_payload,
                android=AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        sound=sound,
                        notification_count=badge
                    )
                ),
                apns=APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound=sound,
                            badge=badge
                        )
                    )
                )
            )

            # 메시지 전송
            response = messaging.send_multicast(message)
            
            results = []
            for i, result in enumerate(response.responses):
                if result.success:
                    results.append({"token": tokens[i], "success": True})
                else:
                    results.append({
                        "token": tokens[i], 
                        "success": False, 
                        "error": str(result.exception)
                    })
            
            logger.info(f"FCM multicast sent: {response.success_count} success, {response.failure_count} failure")
            
            return {
                "success": response.success_count,
                "failure": response.failure_count,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error sending FCM multicast notification: {str(e)}")
            return {
                "success": 0,
                "failure": len(tokens),
                "error": str(e),
                "results": []
            }