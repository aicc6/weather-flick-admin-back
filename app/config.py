"""Admin application configuration settings."""

import os
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv()


class Settings(BaseSettings):
    """Admin application settings configuration."""
    
    # 기본 설정
    app_name: str = "Weather Flick Admin API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # 서버 설정
    host: str = "127.0.0.1"
    port: int = 8001

    # CORS 설정
    cors_origins: list[str] = ["*"]

    # JWT 설정
    secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24시간
    refresh_token_expire_minutes: int = 10080  # 7 days

    # 데이터베이스 설정
    database_url: str = os.getenv("DATABASE_URL", "")

    # 이메일 설정
    mail_username: str = os.getenv("MAIL_USERNAME", "")
    mail_password: str = os.getenv("MAIL_PASSWORD", "")
    mail_from: str = os.getenv("MAIL_FROM", "noreply@weatherflick.com")
    mail_port: int = int(os.getenv("MAIL_PORT", "587"))
    mail_server: str = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    mail_starttls: bool = os.getenv("MAIL_STARTTLS", "true").lower() == "true"
    mail_ssl_tls: bool = os.getenv("MAIL_SSL_TLS", "false").lower() == "true"
    mail_from_name: str = os.getenv("MAIL_FROM_NAME", "Weather Flick Admin")

    # Redis 설정
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # 외부 API 설정
    weather_api_key: str = os.getenv("WEATHER_API_KEY", "")
    weather_api_url: str = "http://api.weatherapi.com/v1"
    
    kma_api_key: str = os.getenv("KMA_API_KEY", "")
    kma_forecast_url: str = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
    
    kakao_api_key: str = os.getenv("KAKAO_API_KEY", "")
    kakao_api_url: str = "https://dapi.kakao.com/v2/local"
    
    naver_client_id: str = os.getenv("NAVER_CLIENT_ID", "")
    naver_client_secret: str = os.getenv("NAVER_CLIENT_SECRET", "")
    naver_api_url: str = "https://openapi.naver.com/v1"
    
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    google_places_url: str = "https://maps.googleapis.com/maps/api/place"
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    
    korea_tourism_api_key: str = os.getenv("KOREA_TOURISM_API_KEY", "")
    korea_tourism_api_url: str = "http://api.visitkorea.or.kr/openapi/service/rest/KorService"

    # 프론트엔드 설정
    admin_frontend_url: str = os.getenv("ADMIN_FRONTEND_URL", "http://localhost:5174")

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_set(cls, v: str) -> str:
        """Validate that secret key is set."""
        if not v:
            raise ValueError("JWT_SECRET_KEY must be set")
        return v

    @field_validator("database_url")
    @classmethod
    def database_url_must_be_set(cls, v: str) -> str:
        """Validate that database URL is set."""
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as list."""
        if self.is_production:
            return [self.admin_frontend_url]
        return self.cors_origins

    class Config:
        """Pydantic config."""
        
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 추가 필드 무시


# 설정 인스턴스 생성
settings = Settings()

# 필수 환경 변수 검증
required_vars = {
    "JWT_SECRET_KEY": settings.secret_key,
    "DATABASE_URL": settings.database_url,
    "KMA_API_KEY": settings.kma_api_key,
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(
        f"다음 필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}"
    )
