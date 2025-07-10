"""
보안 헤더 미들웨어
HTTP 보안 헤더를 통한 웹 애플리케이션 보안 강화
"""

from typing import Dict, Optional, List
from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import hashlib
import secrets
import base64


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """보안 헤더 추가 미들웨어"""
    
    def __init__(
        self,
        app,
        enable_hsts: bool = True,
        enable_csp: bool = True,
        enable_xss_protection: bool = True,
        enable_content_type_options: bool = True,
        enable_frame_options: bool = True,
        enable_referrer_policy: bool = True,
        enable_permissions_policy: bool = True,
        custom_headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp
        self.enable_xss_protection = enable_xss_protection
        self.enable_content_type_options = enable_content_type_options
        self.enable_frame_options = enable_frame_options
        self.enable_referrer_policy = enable_referrer_policy
        self.enable_permissions_policy = enable_permissions_policy
        self.custom_headers = custom_headers or {}
        
    async def dispatch(self, request: Request, call_next):
        """보안 헤더 추가"""
        # CSP nonce 생성
        nonce = None
        if self.enable_csp:
            nonce = self._generate_nonce()
            request.state.csp_nonce = nonce
        
        # 응답 처리
        response = await call_next(request)
        
        # 보안 헤더 추가
        self._add_security_headers(response, nonce)
        
        return response
    
    def _add_security_headers(self, response: Response, nonce: Optional[str] = None):
        """응답에 보안 헤더 추가"""
        
        # HSTS (HTTP Strict Transport Security)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # CSP (Content Security Policy)
        if self.enable_csp:
            csp_directives = self._build_csp_directives(nonce)
            response.headers["Content-Security-Policy"] = csp_directives
        
        # XSS Protection (구형 브라우저용)
        if self.enable_xss_protection:
            response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Type Options
        if self.enable_content_type_options:
            response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Frame Options
        if self.enable_frame_options:
            response.headers["X-Frame-Options"] = "DENY"
        
        # Referrer Policy
        if self.enable_referrer_policy:
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (구 Feature Policy)
        if self.enable_permissions_policy:
            response.headers["Permissions-Policy"] = (
                "geolocation=(), camera=(), microphone=(), payment=(), usb=(), magnetometer=()"
            )
        
        # 커스텀 헤더
        for header, value in self.custom_headers.items():
            response.headers[header] = value
    
    def _build_csp_directives(self, nonce: Optional[str] = None) -> str:
        """CSP 지시자 구성"""
        directives = {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'strict-dynamic'"],
            "style-src": ["'self'", "'unsafe-inline'"],  # 프로덕션에서는 nonce 사용 권장
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'"],
            "connect-src": ["'self'", "https://api.weatherflick.com"],
            "frame-ancestors": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "object-src": ["'none'"],
            "upgrade-insecure-requests": [],
        }
        
        # Nonce 추가
        if nonce:
            directives["script-src"].append(f"'nonce-{nonce}'")
            directives["style-src"] = ["'self'", f"'nonce-{nonce}'"]
        
        # 지시자 문자열 생성
        csp_string = "; ".join(
            f"{key} {' '.join(values)}" if values else key
            for key, values in directives.items()
        )
        
        return csp_string
    
    def _generate_nonce(self) -> str:
        """CSP nonce 생성"""
        return base64.b64encode(secrets.token_bytes(16)).decode('utf-8')


class CorsSecurityMiddleware(BaseHTTPMiddleware):
    """CORS 관련 추가 보안 미들웨어"""
    
    def __init__(
        self,
        app,
        allowed_origins: List[str],
        strict_mode: bool = True
    ):
        super().__init__(app)
        self.allowed_origins = set(allowed_origins)
        self.strict_mode = strict_mode
    
    async def dispatch(self, request: Request, call_next):
        """Origin 검증 강화"""
        origin = request.headers.get("origin")
        
        if origin and self.strict_mode:
            if origin not in self.allowed_origins:
                # 의심스러운 요청 로깅
                print(f"Blocked request from unauthorized origin: {origin}")
                # strict 모드에서는 차단하지 않고 CORS 헤더만 제거
                response = await call_next(request)
                # CORS 헤더 제거
                response.headers.pop("Access-Control-Allow-Origin", None)
                response.headers.pop("Access-Control-Allow-Credentials", None)
                return response
        
        return await call_next(request)


def create_security_headers_config(environment: str = "production") -> Dict[str, any]:
    """환경별 보안 헤더 설정"""
    
    base_config = {
        "enable_hsts": True,
        "enable_csp": True,
        "enable_xss_protection": True,
        "enable_content_type_options": True,
        "enable_frame_options": True,
        "enable_referrer_policy": True,
        "enable_permissions_policy": True,
    }
    
    if environment == "development":
        # 개발 환경에서는 일부 제한 완화
        base_config["enable_csp"] = False  # CSP는 개발 시 문제 유발 가능
        base_config["enable_hsts"] = False  # HTTPS 아닐 수 있음
    
    elif environment == "staging":
        # 스테이징은 프로덕션과 동일하되 HSTS preload 제외
        base_config["custom_headers"] = {
            "X-Environment": "staging"
        }
    
    else:  # production
        base_config["custom_headers"] = {
            "X-Environment": "production",
            "X-Powered-By": "Weather Flick"  # 기본 서버 정보 숨김
        }
    
    return base_config


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Rate Limit 정보 헤더 미들웨어"""
    
    async def dispatch(self, request: Request, call_next):
        """Rate limit 정보 헤더 추가"""
        response = await call_next(request)
        
        # Rate limit 정보가 request state에 있으면 헤더 추가
        if hasattr(request.state, "rate_limit_info"):
            info = request.state.rate_limit_info
            response.headers["X-RateLimit-Limit"] = str(info.get("limit", 100))
            response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(info.get("reset", 0))
        
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """요청 ID 추가 미들웨어 (디버깅 및 추적용)"""
    
    async def dispatch(self, request: Request, call_next):
        """고유 요청 ID 생성 및 추가"""
        # 요청 ID 생성
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = self._generate_request_id()
        
        # Request state에 저장
        request.state.request_id = request_id
        
        # 응답 처리
        response = await call_next(request)
        
        # 응답 헤더에 추가
        response.headers["X-Request-ID"] = request_id
        
        return response
    
    def _generate_request_id(self) -> str:
        """요청 ID 생성"""
        return secrets.token_urlsafe(16)