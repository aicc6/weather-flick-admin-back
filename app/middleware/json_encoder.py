"""
관리자 백엔드용 JSON 직렬화 미들웨어
타임존 정보가 포함된 datetime 객체를 일관되게 직렬화
"""

import json
from datetime import datetime, timezone
from typing import Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.timezone_utils import TimezoneUtils


class AdminDateTimeEncoder(json.JSONEncoder):
    """
    관리자 백엔드용 datetime 객체 JSON 인코더
    배치 작업, 로그, 사용자 관리 등의 시간 데이터를 정확하게 직렬화
    """
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            if obj.tzinfo is None:
                # naive datetime을 UTC로 가정하고 타임존 정보 추가
                obj = obj.replace(tzinfo=timezone.utc)
            
            # ISO 8601 형식으로 직렬화 (타임존 정보 포함)
            return obj.isoformat()
        
        return super().default(obj)


class AdminTimezoneJSONMiddleware(BaseHTTPMiddleware):
    """
    관리자 백엔드 JSON 응답에서 datetime 객체를 타임존 정보와 함께 직렬화하는 미들웨어
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # JSON 응답이 아닌 경우 그대로 반환
        if not isinstance(response, JSONResponse):
            return response
        
        # 관리자 전용 헤더 추가
        response.headers['X-Admin-Server-Timezone'] = 'UTC'
        response.headers['X-Admin-Client-Timezone'] = 'Asia/Seoul'
        response.headers['X-Admin-Datetime-Format'] = 'ISO8601'
        
        return response


def setup_admin_json_encoding(app):
    """
    관리자 FastAPI 앱에 JSON 인코딩 설정 적용
    """
    
    # 타임존 미들웨어 추가
    app.add_middleware(AdminTimezoneJSONMiddleware)


# 관리자 전용 응답 데이터 후처리 함수
def process_admin_response_data(data: Any) -> Any:
    """
    관리자 응답 데이터에서 datetime 객체를 타임존 정보와 함께 포맷팅
    배치 작업, 사용자 관리, 시스템 로그 등에 특화
    """
    if isinstance(data, dict):
        return {key: process_admin_response_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [process_admin_response_data(item) for item in data]
    elif isinstance(data, datetime):
        return TimezoneUtils.format_for_api(data)
    else:
        return data


# 관리자 API 응답용 헬퍼 함수
def create_admin_timezone_aware_response(data: Any, status_code: int = 200) -> JSONResponse:
    """
    관리자용 타임존 정보가 포함된 JSON 응답 생성
    """
    processed_data = process_admin_response_data(data)
    
    response = JSONResponse(
        content=processed_data,
        status_code=status_code
    )
    
    # 관리자 전용 타임존 관련 헤더 추가
    response.headers['X-Admin-Server-Timezone'] = 'UTC'
    response.headers['X-Admin-Client-Timezone'] = 'Asia/Seoul'
    response.headers['X-Admin-Datetime-Format'] = 'ISO8601'
    response.headers['X-Admin-Timezone-Note'] = 'All timestamps are in UTC, display in KST'
    
    return response


# 배치 작업용 특화 함수
def format_batch_job_response(batch_data: dict) -> dict:
    """
    배치 작업 데이터의 시간 필드를 관리자 친화적으로 포맷팅
    """
    time_fields = [
        'created_at', 'updated_at', 'started_at', 'finished_at', 
        'last_run_at', 'next_run_at', 'scheduled_at', 'completed_at'
    ]
    
    result = batch_data.copy()
    
    for field in time_fields:
        if field in result and result[field]:
            if isinstance(result[field], datetime):
                result[field] = TimezoneUtils.format_for_api(result[field])
            elif isinstance(result[field], str):
                # 이미 문자열인 경우, 파싱 후 재포맷
                try:
                    dt = TimezoneUtils.parse_api_datetime(result[field])
                    if dt:
                        result[field] = TimezoneUtils.format_for_api(dt)
                except:
                    pass  # 파싱 실패시 원본 유지
    
    return result


# 사용자 관리용 특화 함수
def format_user_management_response(user_data: dict) -> dict:
    """
    사용자 관리 데이터의 시간 필드를 관리자 친화적으로 포맷팅
    """
    time_fields = [
        'created_at', 'updated_at', 'last_login', 'last_login_at',
        'email_verified_at', 'password_changed_at'
    ]
    
    result = user_data.copy()
    
    for field in time_fields:
        if field in result and result[field]:
            if isinstance(result[field], datetime):
                result[field] = TimezoneUtils.format_for_api(result[field])
    
    return result


# 관리자 FastAPI 의존성 주입용 함수
def get_admin_timezone_headers() -> dict:
    """
    관리자용 타임존 관련 헤더를 반환하는 의존성 함수
    """
    return {
        'X-Admin-Server-Timezone': 'UTC',
        'X-Admin-Client-Timezone': 'Asia/Seoul',
        'X-Admin-Datetime-Format': 'ISO8601',
        'X-Admin-Timezone-Note': 'All timestamps are in UTC, display in KST'
    }