"""
보안 미들웨어 모듈 (관리자 백엔드용)
XSS, 클릭재킹, CSRF 등의 보안 위협으로부터 보호하는 미들웨어
"""

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class AdminSecurityHeadersMiddleware(BaseHTTPMiddleware):
    """관리자 시스템용 보안 헤더 미들웨어"""

    def __init__(self, app, csp_policy: str = None):
        super().__init__(app)
        # 관리자 시스템에 맞는 더 엄격한 CSP 정책
        self.csp_policy = csp_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://unpkg.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' "
            "https://apis.data.go.kr "
            "https://api.openweathermap.org; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # XSS 보호 (더 엄격한 설정)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 클릭재킹 방지 (관리자 시스템은 완전 차단)
        response.headers["X-Frame-Options"] = "DENY"

        # MIME 타입 스니핑 방지
        response.headers["X-Content-Type-Options"] = "nosniff"

        # CSP (Content Security Policy) - 관리자용 엄격한 정책
        response.headers["Content-Security-Policy"] = self.csp_policy

        # Referrer 정책 (관리자 시스템은 더 엄격)
        response.headers["Referrer-Policy"] = "no-referrer"

        # HSTS (HTTPS Strict Transport Security)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # 권한 정책 (관리자 시스템은 모든 기능 차단)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "bluetooth=(), "
            "accelerometer=(), "
            "gyroscope=()"
        )

        # 캐시 제어 (관리자 정보는 캐시하지 않음)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, private"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response


class AdminRateLimitMiddleware(BaseHTTPMiddleware):
    """관리자용 Rate Limiting 미들웨어 (더 엄격한 제한)"""

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests  # 관리자는 더 낮은 제한
        self.window_seconds = window_seconds
        self.requests = {}
        self.failed_attempts = {}  # 실패한 로그인 시도 추적

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import time

        from starlette.responses import JSONResponse

        client_ip = request.client.host
        current_time = time.time()

        # 실패한 로그인 시도에 대한 추가 제한
        if request.url.path == "/api/auth/login":
            if client_ip in self.failed_attempts:
                failed_count = len(
                    [
                        timestamp
                        for timestamp in self.failed_attempts[client_ip]
                        if current_time - timestamp < 300  # 5분 내 실패 시도
                    ]
                )

                if failed_count >= 5:  # 5회 실패 시 15분 차단
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "Too Many Failed Login Attempts",
                            "message": "Account temporarily locked due to multiple failed login attempts.",
                            "retry_after": 900,  # 15분
                        },
                    )

        # 일반적인 Rate Limiting
        if client_ip in self.requests:
            self.requests[client_ip] = [
                (timestamp, count)
                for timestamp, count in self.requests[client_ip]
                if current_time - timestamp < self.window_seconds
            ]

        if client_ip not in self.requests:
            self.requests[client_ip] = []

        current_requests = sum(count for _, count in self.requests[client_ip])

        if current_requests >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_seconds} seconds.",
                    "retry_after": self.window_seconds,
                },
            )

        self.requests[client_ip].append((current_time, 1))

        response = await call_next(request)

        # 로그인 실패 추적
        if request.url.path == "/api/auth/login" and response.status_code in [401, 403]:
            if client_ip not in self.failed_attempts:
                self.failed_attempts[client_ip] = []
            self.failed_attempts[client_ip].append(current_time)

        # Rate limit 헤더 추가
        remaining = max(0, self.max_requests - current_requests - 1)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int(current_time + self.window_seconds)
        )

        return response


class AdminCORSSecurityMiddleware(BaseHTTPMiddleware):
    """관리자용 CORS 보안 미들웨어"""

    def __init__(self, app, allowed_origins: list = None, production: bool = False):
        super().__init__(app)
        self.production = production

        if production:
            # 프로덕션 환경에서는 특정 도메인만 허용
            self.allowed_origins = allowed_origins or [
                "https://wf-dev.seongjunlee.dev",
                "https://wf-admin-dev.seongjunlee.dev",
            ]
        else:
            # 개발 환경에서는 로컬호스트 허용
            self.allowed_origins = allowed_origins or [
                "http://localhost:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174",
            ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("origin")

        response = await call_next(request)

        # 관리자 시스템은 더 엄격한 Origin 검증
        if origin and origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        elif (
            not self.production
            and origin
            and origin.startswith("http://localhost:5174")
        ):
            response.headers["Access-Control-Allow-Origin"] = origin

        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        )
        response.headers["Access-Control-Allow-Headers"] = (
            "Origin, X-Requested-With, Content-Type, Accept, Authorization, "
            "Cache-Control, Pragma, API-Version"
        )
        response.headers["Access-Control-Max-Age"] = "3600"  # 1시간 (더 짧게)

        return response
