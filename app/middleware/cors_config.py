"""
CORS 보안 설정 미들웨어
Cross-Origin Resource Sharing 정책을 통한 보안 강화
"""

from typing import List, Optional, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings
import re


class CorsSettings(BaseSettings):
    """CORS 설정"""
    
    # 기본 허용 도메인
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",  # 사용자 프론트엔드 개발
        "http://localhost:5174",  # 관리자 프론트엔드 개발
        "https://weatherflick.com",  # 프로덕션 도메인
        "https://admin.weatherflick.com",  # 관리자 프로덕션 도메인
    ]
    
    # 허용 메서드
    ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    
    # 허용 헤더
    ALLOWED_HEADERS: List[str] = [
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
        "X-CSRF-Token",
        "API-Version",
        "Accept-Version",
    ]
    
    # 노출 헤더
    EXPOSE_HEADERS: List[str] = [
        "X-Total-Count",
        "X-Page-Count",
        "X-Page-Number",
        "X-Page-Size",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Response-Time",
        "X-Request-ID",
    ]
    
    # 자격 증명 허용
    ALLOW_CREDENTIALS: bool = True
    
    # Preflight 캐시 시간 (초)
    MAX_AGE: int = 3600
    
    # 개발 모드에서 모든 origin 허용
    ALLOW_ALL_ORIGINS_IN_DEV: bool = True
    
    model_config = {"extra": "ignore", "env_prefix": "CORS_", "env_file": ".env"}


def setup_cors(
    app: FastAPI,
    settings: Optional[CorsSettings] = None,
    environment: str = "production"
) -> None:
    """CORS 미들웨어 설정"""
    
    if settings is None:
        settings = CorsSettings()
    
    # 개발 환경에서는 더 유연한 설정
    if environment == "development" and settings.ALLOW_ALL_ORIGINS_IN_DEV:
        allowed_origins = ["*"]
    else:
        allowed_origins = settings.ALLOWED_ORIGINS
    
    # CORS 미들웨어 추가
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=settings.ALLOW_CREDENTIALS,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
        expose_headers=settings.EXPOSE_HEADERS,
        max_age=settings.MAX_AGE,
    )


class DynamicCorsMiddleware:
    """동적 CORS 검증 미들웨어"""
    
    def __init__(
        self,
        allowed_origin_patterns: Optional[List[str]] = None,
        allowed_origin_checker: Optional[callable] = None
    ):
        """
        Args:
            allowed_origin_patterns: 정규식 패턴 리스트 (예: [r"https://.*\\.weatherflick\\.com"])
            allowed_origin_checker: Origin 검증 함수
        """
        self.patterns = []
        if allowed_origin_patterns:
            self.patterns = [re.compile(pattern) for pattern in allowed_origin_patterns]
        self.checker = allowed_origin_checker
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Origin 허용 여부 확인"""
        # 패턴 매칭
        for pattern in self.patterns:
            if pattern.match(origin):
                return True
        
        # 커스텀 체커
        if self.checker:
            return self.checker(origin)
        
        return False


def create_secure_cors_config(
    environment: str = "production",
    additional_origins: Optional[List[str]] = None
) -> Dict[str, any]:
    """환경별 보안 CORS 설정 생성"""
    
    base_config = {
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "Accept",
            "X-CSRF-Token",
        ],
        "expose_headers": [
            "X-Total-Count",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
        ],
        "max_age": 3600,
    }
    
    # 환경별 origin 설정
    if environment == "development":
        base_config["allow_origins"] = ["*"]
    elif environment == "staging":
        base_config["allow_origins"] = [
            "https://staging.weatherflick.com",
            "https://staging-admin.weatherflick.com",
        ]
    else:  # production
        base_config["allow_origins"] = [
            "https://weatherflick.com",
            "https://www.weatherflick.com",
            "https://admin.weatherflick.com",
        ]
    
    # 추가 origin 병합
    if additional_origins:
        if base_config["allow_origins"] != ["*"]:
            base_config["allow_origins"].extend(additional_origins)
    
    return base_config


# CORS 정책 검증 함수들
def validate_origin_subdomain(base_domain: str) -> callable:
    """서브도메인 검증 함수 생성"""
    def validator(origin: str) -> bool:
        # HTTPS만 허용
        if not origin.startswith("https://"):
            return False
        
        # 도메인 추출
        domain = origin.replace("https://", "").split(":")[0]
        
        # 정확한 매칭 또는 서브도메인 매칭
        return domain == base_domain or domain.endswith(f".{base_domain}")
    
    return validator


def validate_origin_whitelist(whitelist: List[str]) -> callable:
    """화이트리스트 기반 검증 함수"""
    def validator(origin: str) -> bool:
        return origin in whitelist
    
    return validator


def create_cors_headers(
    origin: str,
    allowed_methods: List[str] = None,
    allowed_headers: List[str] = None,
    max_age: int = 3600
) -> Dict[str, str]:
    """CORS 헤더 수동 생성 (필요시 사용)"""
    
    headers = {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Vary": "Origin",
    }
    
    if allowed_methods:
        headers["Access-Control-Allow-Methods"] = ", ".join(allowed_methods)
    
    if allowed_headers:
        headers["Access-Control-Allow-Headers"] = ", ".join(allowed_headers)
    
    if max_age:
        headers["Access-Control-Max-Age"] = str(max_age)
    
    return headers