"""
관리자 백엔드용 타임존 처리 미들웨어
배치 작업, 로그, 사용자 관리 등에 특화된 타임존 처리
"""

import logging
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.timezone_utils import TimezoneUtils

logger = logging.getLogger(__name__)


class AdminTimezoneMiddleware(BaseHTTPMiddleware):
    """
    관리자 백엔드용 타임존 처리 미들웨어
    
    특화 기능:
    1. 배치 작업 시간 관리
    2. 사용자 활동 로그 시간 처리
    3. 관리자 작업 로그 기록
    4. 시스템 모니터링 시간 동기화
    """
    
    def __init__(self, app, admin_timezone: str = "Asia/Seoul"):
        super().__init__(app)
        self.admin_timezone = admin_timezone
    
    async def dispatch(self, request: Request, call_next):
        # 관리자 전용 타임존 정보 설정
        request.state.admin_timezone = self.admin_timezone
        request.state.server_timezone = "UTC"
        request.state.log_timezone = "UTC"  # 로그는 항상 UTC
        request.state.batch_timezone = "UTC"  # 배치 작업도 UTC
        request.state.display_timezone = self.admin_timezone  # 화면 표시용
        
        # 관리자 요청 시작 시간 기록
        request.state.request_start_time = TimezoneUtils.now_utc()
        
        # 다음 미들웨어/라우터 실행
        response = await call_next(request)
        
        # 관리자 전용 응답 헤더 추가
        self._add_admin_timezone_headers(response, request)
        
        # 중요한 관리자 액션 로깅
        await self._log_admin_action(request, response)
        
        return response
    
    def _add_admin_timezone_headers(self, response: Response, request: Request):
        """관리자 응답에 타임존 관련 헤더 추가"""
        
        current_utc = TimezoneUtils.now_utc()
        current_kst = TimezoneUtils.to_kst(current_utc)
        
        # 관리자 전용 헤더
        response.headers["X-Admin-Server-Timezone"] = "UTC"
        response.headers["X-Admin-Server-Time-UTC"] = current_utc.isoformat()
        
        if current_kst:
            response.headers["X-Admin-Server-Time-KST"] = current_kst.isoformat()
        
        response.headers["X-Admin-Display-Timezone"] = self.admin_timezone
        
        # 특수 목적 타임존 정보
        response.headers["X-Admin-Batch-Timezone"] = "UTC"
        response.headers["X-Admin-Log-Timezone"] = "UTC"
        response.headers["X-Admin-User-Activity-Timezone"] = "UTC"
        
        # 요청 처리 시간
        if hasattr(request.state, 'request_start_time'):
            processing_time = (current_utc - request.state.request_start_time).total_seconds()
            response.headers["X-Admin-Processing-Time"] = f"{processing_time:.3f}s"
        
        # 관리자 안내 메시지
        response.headers["X-Admin-Timezone-Guide"] = (
            "Server stores times in UTC. "
            "Frontend should display in KST (Asia/Seoul). "
            "Batch jobs and logs use UTC timestamps."
        )
        
        # 배치 작업 관련 추가 정보
        if "batch" in request.url.path:
            response.headers["X-Batch-Recommendation"] = (
                "Schedule batch jobs in KST, store execution times in UTC"
            )
        
        # CORS를 위한 헤더 노출
        admin_headers = [
            "X-Admin-Server-Timezone",
            "X-Admin-Server-Time-UTC",
            "X-Admin-Server-Time-KST", 
            "X-Admin-Display-Timezone",
            "X-Admin-Batch-Timezone",
            "X-Admin-Log-Timezone",
            "X-Admin-User-Activity-Timezone",
            "X-Admin-Processing-Time",
            "X-Admin-Timezone-Guide",
            "X-Batch-Recommendation"
        ]
        
        existing_expose = response.headers.get("Access-Control-Expose-Headers", "")
        if existing_expose:
            response.headers["Access-Control-Expose-Headers"] = f"{existing_expose}, {', '.join(admin_headers)}"
        else:
            response.headers["Access-Control-Expose-Headers"] = ", ".join(admin_headers)
    
    async def _log_admin_action(self, request: Request, response: Response):
        """중요한 관리자 작업 로깅"""
        
        # 로깅 대상 작업 정의
        important_actions = {
            "POST": ["users", "admins", "batch", "system"],
            "PUT": ["users", "admins", "batch", "system"],
            "DELETE": ["users", "admins", "batch"],
            "PATCH": ["users", "admins", "system"]
        }
        
        method = request.method
        path = request.url.path.lower()
        
        # 중요한 작업인지 확인
        should_log = False
        if method in important_actions:
            for action_path in important_actions[method]:
                if action_path in path:
                    should_log = True
                    break
        
        # 배치 작업은 항상 로깅
        if "batch" in path:
            should_log = True
        
        # 시스템 설정 변경도 항상 로깅
        if "system" in path and method in ["POST", "PUT", "PATCH"]:
            should_log = True
        
        if should_log:
            # 처리 시간 계산
            processing_time = "unknown"
            if hasattr(request.state, 'request_start_time'):
                elapsed = (TimezoneUtils.now_utc() - request.state.request_start_time).total_seconds()
                processing_time = f"{elapsed:.3f}s"
            
            # 클라이언트 정보
            client_ip = "unknown"
            if request.client:
                client_ip = request.client.host
            
            # User-Agent 정보
            user_agent = request.headers.get("User-Agent", "unknown")
            
            logger.info(
                f"[ADMIN_ACTION] "
                f"Method: {method}, "
                f"Path: {request.url.path}, "
                f"Status: {response.status_code}, "
                f"Time: {TimezoneUtils.now_utc().isoformat()}, "
                f"Processing: {processing_time}, "
                f"IP: {client_ip}, "
                f"UA: {user_agent[:100]}..."  # User-Agent는 100자로 제한
            )
    
    def get_admin_timezone_context(self, request: Request) -> dict:
        """관리자 요청의 타임존 컨텍스트 반환"""
        return {
            "admin_timezone": getattr(request.state, 'admin_timezone', self.admin_timezone),
            "server_timezone": getattr(request.state, 'server_timezone', 'UTC'),
            "log_timezone": getattr(request.state, 'log_timezone', 'UTC'),
            "batch_timezone": getattr(request.state, 'batch_timezone', 'UTC'),
            "display_timezone": getattr(request.state, 'display_timezone', self.admin_timezone)
        }


# 배치 작업 특화 타임존 유틸리티
class BatchTimezoneHelper:
    """배치 작업을 위한 타임존 헬퍼 클래스"""
    
    @staticmethod
    def format_batch_schedule_time(schedule_time, display_timezone: str = "Asia/Seoul") -> dict:
        """
        배치 작업 스케줄 시간을 다양한 형식으로 포맷팅
        
        Returns:
            dict: UTC, KST, 표시용 시간 등을 포함한 딕셔너리
        """
        if not schedule_time:
            return {
                "utc": None,
                "kst": None,
                "display": "설정되지 않음",
                "next_run": None
            }
        
        # UTC 시간으로 변환
        utc_time = TimezoneUtils.to_utc(schedule_time)
        
        # KST 시간으로 변환
        kst_time = TimezoneUtils.to_kst(schedule_time)
        
        return {
            "utc": TimezoneUtils.format_for_api(utc_time) if utc_time else None,
            "kst": TimezoneUtils.format_for_api(kst_time) if kst_time else None,
            "display": kst_time.strftime("%Y년 %m월 %d일 %H:%M") if kst_time else "시간 오류",
            "next_run": utc_time.isoformat() if utc_time else None
        }
    
    @staticmethod
    def create_batch_time_summary(batch_job_data: dict) -> dict:
        """배치 작업 데이터의 시간 정보를 요약"""
        
        time_fields = ['created_at', 'started_at', 'finished_at', 'last_run_at', 'next_run_at']
        summary = {}
        
        for field in time_fields:
            if field in batch_job_data and batch_job_data[field]:
                field_data = BatchTimezoneHelper.format_batch_schedule_time(
                    batch_job_data[field]
                )
                summary[field] = field_data
        
        # 실행 시간 계산
        if 'started_at' in summary and 'finished_at' in summary:
            if summary['started_at']['utc'] and summary['finished_at']['utc']:
                try:
                    start = TimezoneUtils.parse_api_datetime(summary['started_at']['utc'])
                    end = TimezoneUtils.parse_api_datetime(summary['finished_at']['utc'])
                    if start and end:
                        duration = (end - start).total_seconds()
                        summary['duration'] = {
                            "seconds": duration,
                            "display": f"{duration:.2f}초" if duration < 60 else f"{duration/60:.1f}분"
                        }
                except:
                    summary['duration'] = {"seconds": 0, "display": "계산 불가"}
        
        return summary


# 사용자 관리 특화 타임존 유틸리티
class UserManagementTimezoneHelper:
    """사용자 관리를 위한 타임존 헬퍼 클래스"""
    
    @staticmethod
    def format_user_activity_time(activity_time, admin_timezone: str = "Asia/Seoul") -> dict:
        """사용자 활동 시간을 관리자 친화적으로 포맷팅"""
        
        if not activity_time:
            return {
                "utc": None,
                "display": "활동 없음",
                "relative": "활동 없음"
            }
        
        utc_time = TimezoneUtils.to_utc(activity_time)
        admin_time = TimezoneUtils.to_kst(activity_time) if admin_timezone == "Asia/Seoul" else utc_time
        
        # 상대적 시간 계산
        now = TimezoneUtils.now_utc()
        diff = (now - utc_time).total_seconds()
        
        if diff < 60:
            relative = "방금 전"
        elif diff < 3600:
            relative = f"{int(diff/60)}분 전"
        elif diff < 86400:
            relative = f"{int(diff/3600)}시간 전"
        elif diff < 2592000:
            relative = f"{int(diff/86400)}일 전"
        else:
            relative = admin_time.strftime("%Y년 %m월 %d일") if admin_time else "오래 전"
        
        return {
            "utc": TimezoneUtils.format_for_api(utc_time) if utc_time else None,
            "display": admin_time.strftime("%Y-%m-%d %H:%M") if admin_time else "시간 오류",
            "relative": relative
        }


# 미들웨어 설정 헬퍼 함수
def setup_admin_timezone_middleware(app):
    """관리자 앱에 타임존 미들웨어 추가"""
    
    app.add_middleware(AdminTimezoneMiddleware, admin_timezone="Asia/Seoul")
    logger.info("관리자용 타임존 미들웨어가 추가되었습니다.")


# 의존성 주입용 함수들
def get_admin_timezone_context(request: Request) -> dict:
    """관리자 요청의 타임존 컨텍스트 반환"""
    return {
        "admin_timezone": getattr(request.state, 'admin_timezone', 'Asia/Seoul'),
        "server_timezone": getattr(request.state, 'server_timezone', 'UTC'),
        "log_timezone": getattr(request.state, 'log_timezone', 'UTC'),
        "batch_timezone": getattr(request.state, 'batch_timezone', 'UTC'),
        "display_timezone": getattr(request.state, 'display_timezone', 'Asia/Seoul')
    }


def get_batch_timezone_helper() -> BatchTimezoneHelper:
    """배치 타임존 헬퍼 반환"""
    return BatchTimezoneHelper()


def get_user_management_timezone_helper() -> UserManagementTimezoneHelper:
    """사용자 관리 타임존 헬퍼 반환"""
    return UserManagementTimezoneHelper()