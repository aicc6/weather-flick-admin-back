from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 기본 설정
    app_name: str = "Weather Flick Admin API"
    app_version: str = "1.0.0"
    debug: bool = False

    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS 설정
    cors_origins: list = ["*"]

    # JWT 설정
    secret_key: str = "weatherflick-admin-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24시간

    # 데이터베이스 설정
    database_url: str = "postgresql://aicc6:aicc6_pass@seongjunlee.dev:55432/weather_flick"

    # 이메일 설정
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "noreply@weatherflick.com"
    mail_port: int = 587
    mail_server: str = "smtp.gmail.com"
    mail_starttls: bool = True
    mail_ssl_tls: bool = False
    mail_from_name: str = "Weather Flick"

    # WeatherAPI 설정
    weather_api_key: str = ""
    weather_api_url: str = "http://api.weatherapi.com/v1"

    # 기상청 API 설정
    kma_api_key: str = ""

    # 카카오 API 설정 (맛집, 장소 검색)
    kakao_api_key: str = ""
    kakao_api_url: str = "https://dapi.kakao.com/v2/local"

    # 네이버 API 설정 (블로그, 뉴스 검색)
    naver_client_id: str = ""
    naver_client_secret: str = ""
    naver_api_url: str = "https://openapi.naver.com/v1"

    # 구글 Places API 설정 (장소 검색)
    google_api_key: str = ""
    google_places_url: str = "https://maps.googleapis.com/maps/api/place"

    # 구글 OAuth 설정
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # 공공데이터포털 API 설정 (관광정보, 대기질 정보)
    public_data_api_key: str = ""
    public_data_api_url: str = "http://api.visitkorea.or.kr/openapi/service/rest/KorService"

    # 한국관광공사 API 설정
    korea_tourism_api_key: str = ""
    korea_tourism_api_url: str = "http://api.visitkorea.or.kr/openapi/service/rest/KorService"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
