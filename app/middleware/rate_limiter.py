"""
Rate Limiting 미들웨어
API 요청 속도 제한을 통한 DDoS 공격 방지 및 서버 자원 보호
"""

from typing import Dict, Optional, Callable
from datetime import datetime, timedelta
import time
import asyncio
import re
from collections import defaultdict
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis
from functools import lru_cache
import json
import hashlib


class RateLimitExceeded(HTTPException):
    """Rate limit 초과 예외"""
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": "너무 많은 요청이 발생했습니다. 잠시 후 다시 시도해주세요.",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )


class InMemoryRateLimiter:
    """메모리 기반 Rate Limiter (Redis 없을 때 사용)"""
    
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self._cleanup_interval = 60  # 60초마다 정리
        self._last_cleanup = time.time()
    
    async def is_allowed(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> tuple[bool, int]:
        """요청 허용 여부 확인"""
        now = time.time()
        
        # 주기적으로 오래된 데이터 정리
        if now - self._last_cleanup > self._cleanup_interval:
            await self._cleanup()
        
        # 현재 윈도우 시작 시간
        window_start = now - window_seconds
        
        # 이전 요청들 필터링
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if req_time > window_start
        ]
        
        # 현재 요청 수
        current_requests = len(self.requests[key])
        
        if current_requests >= max_requests:
            # 가장 오래된 요청 시간으로부터 재시도 시간 계산
            oldest_request = min(self.requests[key])
            retry_after = int(oldest_request + window_seconds - now) + 1
            return False, max(retry_after, 1)
        
        # 요청 기록
        self.requests[key].append(now)
        return True, 0
    
    async def _cleanup(self):
        """오래된 데이터 정리"""
        now = time.time()
        cutoff = now - 3600  # 1시간 이상 된 데이터 삭제
        
        for key in list(self.requests.keys()):
            self.requests[key] = [
                req_time for req_time in self.requests[key] 
                if req_time > cutoff
            ]
            if not self.requests[key]:
                del self.requests[key]
        
        self._last_cleanup = now


class RedisRateLimiter:
    """Redis 기반 Rate Limiter (분산 환경용)"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def is_allowed(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> tuple[bool, int]:
        """Sliding window 방식의 rate limiting"""
        now = time.time()
        window_start = now - window_seconds
        
        # Redis 파이프라인 사용
        pipe = self.redis.pipeline()
        
        # 오래된 요청 제거
        pipe.zremrangebyscore(key, 0, window_start)
        
        # 현재 요청 수 확인
        pipe.zcard(key)
        
        # 현재 요청 추가
        pipe.zadd(key, {str(now): now})
        
        # TTL 설정
        pipe.expire(key, window_seconds + 1)
        
        results = pipe.execute()
        current_requests = results[1]
        
        if current_requests >= max_requests:
            # 가장 오래된 요청 시간 조회
            oldest = self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_time = oldest[0][1]
                retry_after = int(oldest_time + window_seconds - now) + 1
                return False, max(retry_after, 1)
            return False, 1
        
        return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate Limiting 미들웨어"""
    
    def __init__(
        self,
        app,
        redis_client: Optional[redis.Redis] = None,
        default_limit: int = 100,
        default_window: int = 60,
        endpoint_limits: Optional[Dict[str, tuple[int, int]]] = None,
        key_func: Optional[Callable] = None,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        
        # Rate limiter 초기화
        if redis_client:
            self.limiter = RedisRateLimiter(redis_client)
        else:
            self.limiter = InMemoryRateLimiter()
        
        self.default_limit = default_limit
        self.default_window = default_window
        self.endpoint_limits = endpoint_limits or {}
        self.key_func = key_func or self._default_key_func
        self.exclude_paths = exclude_paths or ["/docs", "/redoc", "/openapi.json"]
    
    def _default_key_func(self, request: Request) -> str:
        """기본 키 생성 함수 (IP 기반)"""
        # X-Forwarded-For 헤더 확인 (프록시 뒤에 있을 경우)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host
        
        # 인증된 사용자는 사용자 ID로 구분
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"
        
        return f"ip:{ip}"
    
    def _get_endpoint_limit(self, path: str, method: str) -> tuple[int, int]:
        """엔드포인트별 제한 설정 조회"""
        # 정확한 매칭
        key = f"{method}:{path}"
        if key in self.endpoint_limits:
            return self.endpoint_limits[key]
        
        # 경로 패턴 매칭
        for pattern, limit in self.endpoint_limits.items():
            if "*" in pattern:
                pattern_regex = pattern.replace("*", ".*")
                if re.match(pattern_regex, key):
                    return limit
        
        return self.default_limit, self.default_window
    
    async def dispatch(self, request: Request, call_next):
        """미들웨어 처리"""
        # 제외 경로 확인
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Rate limit 키 생성
        key = self.key_func(request)
        endpoint_key = f"{key}:{request.method}:{request.url.path}"
        
        # 엔드포인트별 제한 확인
        max_requests, window_seconds = self._get_endpoint_limit(
            request.url.path, 
            request.method
        )
        
        # Rate limit 확인
        allowed, retry_after = await self.limiter.is_allowed(
            endpoint_key, 
            max_requests, 
            window_seconds
        )
        
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "너무 많은 요청이 발생했습니다. 잠시 후 다시 시도해주세요.",
                        "retry_after": retry_after
                    }
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Window": str(window_seconds),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # 요청 처리
        response = await call_next(request)
        
        # Rate limit 헤더 추가
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Window"] = str(window_seconds)
        
        return response


def create_rate_limiter(
    redis_url: Optional[str] = None,
    **kwargs
) -> RateLimitMiddleware:
    """Rate limiter 생성 헬퍼 함수"""
    redis_client = None
    
    if redis_url:
        try:
            import redis
            redis_client = redis.from_url(redis_url)
            redis_client.ping()
        except Exception as e:
            print(f"Redis 연결 실패, 메모리 기반 rate limiter 사용: {e}")
    
    # 엔드포인트별 제한 설정
    endpoint_limits = {
        # 인증 관련 - 더 엄격한 제한
        "POST:/api/auth/login": (5, 60),  # 1분에 5번
        "POST:/api/auth/register": (3, 300),  # 5분에 3번
        "POST:/api/auth/forgot-password": (3, 600),  # 10분에 3번
        
        # 쓰기 작업 - 중간 제한
        "POST:/api/*": (30, 60),  # 1분에 30번
        "PUT:/api/*": (30, 60),
        "DELETE:/api/*": (20, 60),  # 1분에 20번
        
        # 읽기 작업 - 느슨한 제한
        "GET:/api/*": (100, 60),  # 1분에 100번
        
        # 시스템 상태 - 특별 제한
        "GET:/api/system/status": (60, 60),  # 1분에 60번 (1초에 1번)
    }
    
    class RateLimitMiddlewareWrapper:
        def __init__(self, redis_client, endpoint_limits, **kwargs):
            self.redis_client = redis_client
            self.endpoint_limits = endpoint_limits
            self.kwargs = kwargs
            
        def __call__(self, app):
            return RateLimitMiddleware(
                app=app,
                redis_client=self.redis_client,
                endpoint_limits=self.endpoint_limits,
                **self.kwargs
            )
    
    return RateLimitMiddlewareWrapper(
        redis_client=redis_client,
        endpoint_limits=endpoint_limits,
        **kwargs
    )


# IP 기반 차단 기능
class IPBlocker:
    """악의적인 IP 차단 관리"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.blocked_ips = set()
        self.block_duration = 3600  # 1시간
    
    async def is_blocked(self, ip: str) -> bool:
        """IP 차단 여부 확인"""
        if self.redis:
            return bool(self.redis.get(f"blocked:ip:{ip}"))
        return ip in self.blocked_ips
    
    async def block_ip(self, ip: str, duration: Optional[int] = None):
        """IP 차단"""
        duration = duration or self.block_duration
        
        if self.redis:
            self.redis.setex(f"blocked:ip:{ip}", duration, "1")
        else:
            self.blocked_ips.add(ip)
            # 메모리 기반일 때는 자동 해제 구현 필요
            asyncio.create_task(self._unblock_after(ip, duration))
    
    async def unblock_ip(self, ip: str):
        """IP 차단 해제"""
        if self.redis:
            self.redis.delete(f"blocked:ip:{ip}")
        else:
            self.blocked_ips.discard(ip)
    
    async def _unblock_after(self, ip: str, duration: int):
        """일정 시간 후 자동 차단 해제"""
        await asyncio.sleep(duration)
        self.blocked_ips.discard(ip)