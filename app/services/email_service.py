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
            template = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Weather Flick 임시 비밀번호</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f4f6f9;
        }
        .container {
            max-width: 600px;
            margin: 20px auto;
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        .logo {
            width: 64px;
            height: 64px;
            border-radius: 12px;
            margin: 0 auto 20px;
            display: block;
            box-shadow: 0 4px 12px rgba(255,255,255,0.2);
        }
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 28px;
            font-weight: 700;
        }
        .header h2 {
            margin: 0;
            font-size: 16px;
            opacity: 0.9;
            font-weight: 400;
        }
        .content {
            padding: 40px 30px;
            background: white;
        }
        .password-box {
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border: 3px solid #f59e0b;
            padding: 25px;
            text-align: center;
            border-radius: 12px;
            margin: 30px 0;
            font-size: 28px;
            font-weight: 700;
            color: #92400e;
            letter-spacing: 2px;
            font-family: 'Courier New', monospace;
        }
        .warning {
            background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
            border-left: 4px solid #ef4444;
            padding: 25px;
            margin: 25px 0;
            border-radius: 8px;
        }
        .warning p {
            margin: 0 0 15px 0;
            color: #dc2626;
            font-size: 18px;
            font-weight: 600;
        }
        .warning ul {
            margin: 15px 0;
            padding-left: 20px;
        }
        .warning li {
            margin: 10px 0;
            color: #7f1d1d;
        }
        .footer {
            text-align: center;
            padding: 30px;
            background: #f8fafc;
            color: #64748b;
            font-size: 14px;
            border-top: 1px solid #e2e8f0;
        }
        .footer p {
            margin: 8px 0;
        }
        h2 {
            color: #1e293b;
            font-size: 24px;
            margin: 0 0 20px 0;
            font-weight: 600;
        }
        p {
            margin: 16px 0;
            color: #475569;
            font-size: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="https://wf-dev.seongjunlee.dev/newicon.jpg" height="200" width="200" alt="Weather Flick Logo" class="logo">
            <h1>Weather Flick</h1>
            <h2>관리자 임시 비밀번호 발급</h2>
        </div>

        <div class="content">
            <p>안녕하세요{% if user_name %}, {{ user_name }}님{% endif %}!</p>

            <p>Weather Flick 관리자 시스템의 임시 비밀번호가 발급되었습니다.</p>

            <div class="password-box">
                {{ temp_password }}
            </div>

            <div class="warning">
                <p>⚠️ 보안을 위해 다음 사항을 꼭 지켜주세요:</p>
                <ul>
                    <li>이 임시 비밀번호는 <strong>24시간 후 자동 만료</strong>됩니다</li>
                    <li>첫 로그인 후 <strong>반드시 새로운 비밀번호로 변경</strong>해주세요</li>
                    <li>이 이메일을 타인과 공유하지 마세요</li>
                    <li>로그인 후 즉시 이 이메일을 삭제하는 것을 권장합니다</li>
                </ul>
            </div>

            <p>문의사항이 있으시면 시스템 관리자에게 연락해주세요.</p>
        </div>

        <div class="footer">
            <p>이 메일은 자동으로 발송된 메일입니다. 회신하지 마세요.</p>
            <p>&copy; 2025 Weather Flick. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
            """)

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

    async def send_notification_email(
        self, to_email: str, subject: str, content: str
    ) -> bool:
        """일반 알림 이메일 전송"""
        try:
            if not self.fastmail:
                logger.warning("이메일 서비스가 초기화되지 않음")
                return False

            # HTML 템플릿
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{subject}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f4f6f9;
        }}
        .container {{
            max-width: 600px;
            margin: 20px auto;
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .footer {{
            text-align: center;
            padding: 20px 30px;
            border-top: 1px solid #E5E7EB;
            color: #6B7280;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Weather Flick</h1>
            <h2>{subject}</h2>
        </div>
        <div class="content">
            <div>{content.replace(chr(10), '<br>')}</div>
        </div>
        <div class="footer">
            <p>이 이메일은 Weather Flick에서 발송되었습니다.</p>
        </div>
    </div>
</body>
</html>
            """

            message = MessageSchema(
                subject=subject,
                recipients=[to_email],
                body=html_content,
                subtype=MessageType.html,
            )

            await self.fastmail.send_message(message)
            logger.info(f"알림 이메일 전송 성공: {to_email}")
            return True

        except Exception as e:
            logger.error(f"알림 이메일 전송 실패: {to_email}, 오류: {e}")
            return False

    async def send_contact_answer_email(
        self, to_email: str, contact_title: str, answer_content: str, contact_id: int
    ) -> bool:
        """문의 답변 이메일 전송"""
        try:
            if not self.fastmail:
                logger.warning("이메일 서비스가 초기화되지 않음")
                return False

            subject = "문의하신 내용에 답변이 등록되었습니다"

            # HTML 템플릿 생성
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: #ffffff;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .message-box {{
            background: #f0f9ff;
            border-left: 4px solid #3b82f6;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
        }}
        .inquiry-title {{
            font-size: 18px;
            font-weight: bold;
            color: #1e40af;
            margin-bottom: 10px;
        }}
        .answer-content {{
            background: #f8fafc;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            white-space: pre-wrap;
        }}
        .cta-button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            margin-top: 20px;
        }}
        .footer {{
            text-align: center;
            padding: 30px;
            background: #f8fafc;
            color: #64748b;
            font-size: 14px;
            border-top: 1px solid #e2e8f0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Weather Flick</h1>
            <p style="margin-top: 10px; font-size: 18px;">문의 답변 알림</p>
        </div>
        <div class="content">
            <h2 style="color: #1e293b;">안녕하세요!</h2>
            <p>문의하신 내용에 대한 답변이 등록되었습니다.</p>

            <div class="message-box">
                <div class="inquiry-title">📝 문의 제목</div>
                <div>{contact_title}</div>
            </div>

            <h3 style="color: #1e293b; margin-top: 30px;">💬 답변 내용</h3>
            <div class="answer-content">{answer_content}</div>

            <p style="margin-top: 30px;">자세한 내용은 Weather Flick 웹사이트에서 확인하실 수 있습니다.</p>

            <a href="https://wf-dev.seongjunlee.dev/contact" class="cta-button">답변 확인하기</a>
        </div>
        <div class="footer">
            <p>이 이메일은 Weather Flick에서 발송되었습니다.</p>
            <p>궁금하신 점이 있으시면 언제든지 문의해주세요.</p>
        </div>
    </div>
</body>
</html>
            """

            message = MessageSchema(
                subject=subject,
                recipients=[to_email],
                body=html_content,
                subtype=MessageType.html,
            )

            await self.fastmail.send_message(message)
            logger.info(f"문의 답변 이메일 전송 성공: {to_email}")
            return True

        except Exception as e:
            logger.error(f"문의 답변 이메일 전송 실패: {to_email}, 오류: {e}")
            return False

    async def send_password_reset_notification(
        self, email: str, user_name: str | None = None
    ) -> bool:
        """비밀번호 재설정 알림 이메일 전송"""
        try:
            if not self.fastmail:
                logger.warning("이메일 서비스가 초기화되지 않음")
                return False

            template = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Weather Flick 비밀번호 변경 완료</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f4f6f9;
        }
        .container {
            max-width: 600px;
            margin: 20px auto;
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        .logo {
            width: 64px;
            height: 64px;
            border-radius: 12px;
            margin: 0 auto 20px;
            display: block;
            box-shadow: 0 4px 12px rgba(255,255,255,0.2);
        }
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 28px;
            font-weight: 700;
        }
        .header h2 {
            margin: 0;
            font-size: 16px;
            opacity: 0.9;
            font-weight: 400;
        }
        .content {
            padding: 40px 30px;
            background: white;
        }
        .success-info {
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
            border-left: 4px solid #10b981;
            padding: 25px;
            margin: 25px 0;
            border-radius: 8px;
        }
        .success-info p {
            margin: 8px 0;
            color: #065f46;
        }
        .footer {
            text-align: center;
            padding: 30px;
            background: #f8fafc;
            color: #64748b;
            font-size: 14px;
            border-top: 1px solid #e2e8f0;
        }
        .footer p {
            margin: 8px 0;
        }
        h2 {
            color: #1e293b;
            font-size: 24px;
            margin: 0 0 20px 0;
            font-weight: 600;
        }
        p {
            margin: 16px 0;
            color: #475569;
            font-size: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="https://wf-dev.seongjunlee.dev/newicon.jpg" height="200" width="200" alt="Weather Flick Logo" class="logo">
            <h1>Weather Flick</h1>
            <h2>비밀번호 변경 완료</h2>
        </div>

        <div class="content">
            <p>안녕하세요{% if user_name %}, {{ user_name }}님{% endif %}!</p>

            <p>Weather Flick 관리자 계정의 비밀번호가 성공적으로 변경되었습니다.</p>

            <div class="success-info">
                <p><strong>✅ 변경 완료 시간:</strong> {{ current_time }}</p>
                <p><strong>🛡️ 계정 보안이 강화되었습니다.</strong></p>
            </div>

            <p>만약 본인이 변경하지 않았다면 즉시 시스템 관리자에게 연락해주세요.</p>
        </div>

        <div class="footer">
            <p>이 메일은 자동으로 발송된 메일입니다. 회신하지 마세요.</p>
            <p>&copy; 2025 Weather Flick. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
            """)

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
