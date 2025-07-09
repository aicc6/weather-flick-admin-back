"""
이메일 전송 서비스
"""

import logging

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jinja2 import Template

from ..config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """이메일 전송 서비스"""

    def __init__(self):
        """이메일 서비스 초기화"""
        try:
            # 설정에서 이메일 정보 가져오기
            if not all(
                [settings.mail_username, settings.mail_password, settings.mail_from]
            ):
                logger.warning("이메일 설정이 없습니다. 이메일 기능이 비활성화됩니다.")
                self.fastmail = None
                return

            self.conf = ConnectionConfig(
                MAIL_USERNAME=settings.mail_username,
                MAIL_PASSWORD=settings.mail_password,
                MAIL_FROM=settings.mail_from,
                MAIL_PORT=settings.mail_port,
                MAIL_SERVER=settings.mail_server,
                MAIL_FROM_NAME=settings.mail_from_name,
                MAIL_STARTTLS=settings.mail_starttls,
                MAIL_SSL_TLS=settings.mail_ssl_tls,
                USE_CREDENTIALS=True,
                VALIDATE_CERTS=True,
            )

            self.fastmail = FastMail(self.conf)
            logger.info("이메일 서비스 초기화 완료")

        except Exception as e:
            logger.warning(f"이메일 서비스 초기화 실패: {e}")
            self.fastmail = None

    async def send_temporary_password_email(
        self, email: str, temp_password: str, user_name: str | None = None
    ) -> bool:
        """임시 비밀번호 이메일 전송"""
        try:
            if not self.fastmail:
                logger.warning("이메일 서비스가 초기화되지 않음")
                return False

            # 이메일 템플릿
            template = Template(
                """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Weather Flick 임시 비밀번호</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #4A90E2; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .password-box { 
            background-color: #e8f4fd; 
            border: 2px solid #4A90E2; 
            padding: 15px; 
            margin: 20px 0; 
            text-align: center; 
            font-size: 18px; 
            font-weight: bold; 
            letter-spacing: 2px;
        }
        .warning { color: #e74c3c; font-weight: bold; }
        .footer { text-align: center; margin-top: 30px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌤️ Weather Flick</h1>
            <h2>임시 비밀번호 발급</h2>
        </div>
        
        <div class="content">
            <p>안녕하세요{% if user_name %}, {{ user_name }}님{% endif %}!</p>
            
            <p>Weather Flick 관리자 시스템의 임시 비밀번호가 발급되었습니다.</p>
            
            <div class="password-box">
                {{ temp_password }}
            </div>
            
            <p class="warning">⚠️ 보안을 위해 다음 사항을 꼭 지켜주세요:</p>
            <ul>
                <li>이 임시 비밀번호는 <strong>24시간 후 자동 만료</strong>됩니다</li>
                <li>첫 로그인 후 <strong>반드시 새로운 비밀번호로 변경</strong>해주세요</li>
                <li>이 이메일을 타인과 공유하지 마세요</li>
                <li>로그인 후 즉시 이 이메일을 삭제하는 것을 권장합니다</li>
            </ul>
            
            <p>문의사항이 있으시면 시스템 관리자에게 연락해주세요.</p>
        </div>
        
        <div class="footer">
            <p>이 메일은 자동으로 발송된 메일입니다. 회신하지 마세요.</p>
            <p>&copy; 2025 Weather Flick. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
            """
            )

            html_content = template.render(
                temp_password=temp_password, user_name=user_name
            )

            message = MessageSchema(
                subject="Weather Flick 임시 비밀번호 발급",
                recipients=[email],
                body=html_content,
                subtype=MessageType.html,
            )

            await self.fastmail.send_message(message)
            logger.info(f"임시 비밀번호 이메일 전송 성공: {email}")
            return True

        except Exception as e:
            logger.error(f"임시 비밀번호 이메일 전송 실패: {email}, 오류: {e}")
            return False

    async def send_password_reset_notification(
        self, email: str, user_name: str | None = None
    ) -> bool:
        """비밀번호 재설정 알림 이메일 전송"""
        try:
            if not self.fastmail:
                logger.warning("이메일 서비스가 초기화되지 않음")
                return False

            template = Template(
                """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Weather Flick 비밀번호 변경 완료</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #27AE60; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .footer { text-align: center; margin-top: 30px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌤️ Weather Flick</h1>
            <h2>비밀번호 변경 완료</h2>
        </div>
        
        <div class="content">
            <p>안녕하세요{% if user_name %}, {{ user_name }}님{% endif %}!</p>
            
            <p>Weather Flick 관리자 계정의 비밀번호가 성공적으로 변경되었습니다.</p>
            
            <p><strong>변경 시간:</strong> {{ current_time }}</p>
            
            <p>만약 본인이 변경하지 않았다면 즉시 시스템 관리자에게 연락해주세요.</p>
        </div>
        
        <div class="footer">
            <p>이 메일은 자동으로 발송된 메일입니다. 회신하지 마세요.</p>
            <p>&copy; 2025 Weather Flick. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
            """
            )

            from datetime import datetime

            html_content = template.render(
                user_name=user_name,
                current_time=datetime.now().strftime("%Y년 %m월 %d일 %H:%M"),
            )

            message = MessageSchema(
                subject="Weather Flick 비밀번호 변경 완료",
                recipients=[email],
                body=html_content,
                subtype=MessageType.html,
            )

            await self.fastmail.send_message(message)
            logger.info(f"비밀번호 변경 알림 이메일 전송 성공: {email}")
            return True

        except Exception as e:
            logger.error(f"비밀번호 변경 알림 이메일 전송 실패: {email}, 오류: {e}")
            return False

    def is_configured(self) -> bool:
        """이메일 서비스 설정 여부 확인"""
        return (
            self.fastmail is not None
            and bool(settings.mail_username)
            and bool(settings.mail_password)
            and bool(settings.mail_from)
        )


# 전역 이메일 서비스 인스턴스
email_service = EmailService()


async def send_temp_password_email(
    email: str, temp_password: str, user_name: str = None
) -> bool:
    """임시 비밀번호 이메일 전송 편의 함수"""
    return await email_service.send_temporary_password_email(
        email, temp_password, user_name
    )


async def send_password_change_notification(email: str, user_name: str = None) -> bool:
    """비밀번호 변경 알림 이메일 전송 편의 함수"""
    return await email_service.send_password_reset_notification(email, user_name)
