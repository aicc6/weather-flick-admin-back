"""
캐싱 시스템 유틸리티
"""

import hashlib
import json
import time
from collections.abc import Callable
from functools import wraps
from typing import Any


class MemoryCache:
    """메모리 기반 캐시 시스템"""

    def __init__(self, default_ttl: int = 300):  # 5분 기본 TTL
        self._cache: dict[str, dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    def _is_expired(self, cache_entry: dict[str, Any]) -> bool:
        """캐시 엔트리가 만료되었는지 확인"""
        return time.time() > cache_entry["expires_at"]

    def _generate_key(self, key: str, prefix: str = None) -> str:
        """캐시 키 생성"""
        if prefix:
            return f"{prefix}:{key}"
        return key

    def get(self, key: str, prefix: str = None) -> Any | None:
        """캐시에서 값 조회"""
        cache_key = self._generate_key(key, prefix)

        if cache_key in self._cache:
            cache_entry = self._cache[cache_key]

            if not self._is_expired(cache_entry):
                self.stats["hits"] += 1
                return cache_entry["value"]
            else:
                # 만료된 항목 제거
                del self._cache[cache_key]

        self.stats["misses"] += 1
        return None

    def set(self, key: str, value: Any, ttl: int = None, prefix: str = None) -> None:
        """캐시에 값 저장"""
        cache_key = self._generate_key(key, prefix)
        ttl = ttl or self.default_ttl

        self._cache[cache_key] = {
            "value": value,
            "expires_at": time.time() + ttl,
            "created_at": time.time(),
        }

        self.stats["sets"] += 1

    def delete(self, key: str, prefix: str = None) -> bool:
        """캐시에서 값 삭제"""
        cache_key = self._generate_key(key, prefix)

        if cache_key in self._cache:
            del self._cache[cache_key]
            self.stats["deletes"] += 1
            return True

        return False

    def clear(self, prefix: str = None) -> int:
        """캐시 클리어"""
        if prefix:
            # 특정 프리픽스만 삭제
            keys_to_delete = [
                k for k in self._cache.keys() if k.startswith(f"{prefix}:")
            ]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)
        else:
            # 모든 캐시 삭제
            count = len(self._cache)
            self._cache.clear()
            return count

    def cleanup_expired(self) -> int:
        """만료된 캐시 엔트리 정리"""
        expired_keys = [
            key for key, entry in self._cache.items() if self._is_expired(entry)
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """캐시 통계 조회"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            **self.stats,
            "cache_size": len(self._cache),
            "hit_rate": round(hit_rate, 2),
        }


# 전역 캐시 인스턴스
cache = MemoryCache()


def cache_result(ttl: int = 300, prefix: str = None, key_func: Callable = None):
    """
    함수 결과를 캐시하는 데코레이터

    Args:
        ttl: Time to live (초)
        prefix: 캐시 키 프리픽스
        key_func: 커스텀 키 생성 함수
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 캐시 키 생성
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 기본 키 생성 (함수명 + 인자들 해시)
                arg_str = json.dumps([str(arg) for arg in args], sort_keys=True)
                kwarg_str = json.dumps(kwargs, sort_keys=True, default=str)
                combined = f"{func.__name__}:{arg_str}:{kwarg_str}"
                cache_key = hashlib.md5(combined.encode()).hexdigest()

            # 캐시에서 조회
            cached_result = cache.get(cache_key, prefix)
            if cached_result is not None:
                return cached_result

            # 캐시 미스 시 함수 실행
            result = await func(*args, **kwargs)

            # 결과 캐시
            cache.set(cache_key, result, ttl, prefix)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 캐시 키 생성
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 기본 키 생성 (함수명 + 인자들 해시)
                arg_str = json.dumps([str(arg) for arg in args], sort_keys=True)
                kwarg_str = json.dumps(kwargs, sort_keys=True, default=str)
                combined = f"{func.__name__}:{arg_str}:{kwarg_str}"
                cache_key = hashlib.md5(combined.encode()).hexdigest()

            # 캐시에서 조회
            cached_result = cache.get(cache_key, prefix)
            if cached_result is not None:
                return cached_result

            # 캐시 미스 시 함수 실행
            result = func(*args, **kwargs)

            # 결과 캐시
            cache.set(cache_key, result, ttl, prefix)

            return result

        # 비동기 함수인지 확인
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def cache_key_for_user_query(user_id: str, query_type: str, **params) -> str:
    """사용자 쿼리용 캐시 키 생성"""
    param_str = json.dumps(params, sort_keys=True, default=str)
    return f"user:{user_id}:{query_type}:{hashlib.md5(param_str.encode()).hexdigest()}"


def cache_key_for_destination_query(destination_id: str = None, **params) -> str:
    """여행지 쿼리용 캐시 키 생성"""
    param_str = json.dumps(params, sort_keys=True, default=str)
    base = f"destination:{destination_id}" if destination_id else "destinations"
    return f"{base}:{hashlib.md5(param_str.encode()).hexdigest()}"


def cache_key_for_weather_query(city: str, **params) -> str:
    """날씨 쿼리용 캐시 키 생성"""
    param_str = json.dumps(params, sort_keys=True, default=str)
    return f"weather:{city}:{hashlib.md5(param_str.encode()).hexdigest()}"


# 자주 사용되는 캐시 프리픽스 상수
CACHE_PREFIX = {
    "DESTINATIONS": "destinations",
    "REVIEWS": "reviews",
    "WEATHER": "weather",
    "TRAVEL_PLANS": "travel_plans",
    "RECOMMENDATIONS": "recommendations",
    "USERS": "users",
    "ANALYTICS": "analytics",
    "ML_PREDICTIONS": "ml_predictions",
    "ML_MODELS": "ml_models",
    "ML_PERFORMANCE": "ml_performance",
    "NOTIFICATIONS": "notifications",
    "STATS": "stats",
    "PREDICTIONS": "predictions",
    "USER_INSIGHTS": "user_insights",
    "DESTINATION_FORECAST": "destination_forecast",
    "TRENDS": "trends",
}

# 캐시 TTL 상수 (초)
CACHE_TTL = {
    "SHORT": 60,  # 1분
    "MEDIUM": 300,  # 5분
    "LONG": 1800,  # 30분
    "EXTENDED": 3600,  # 1시간
}
