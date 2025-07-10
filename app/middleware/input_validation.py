"""
입력 검증 및 보안 미들웨어
SQL Injection, XSS, Command Injection 등 보안 위협 방지
"""

import re
import html
import json
from typing import Dict, List, Optional, Set, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, validator
import logging


logger = logging.getLogger(__name__)


class SecurityConfig(BaseModel):
    """보안 설정"""
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    max_json_depth: int = 10
    max_array_length: int = 1000
    max_string_length: int = 10000
    max_parameter_count: int = 100
    block_file_extensions: List[str] = [".exe", ".bat", ".cmd", ".sh", ".ps1"]
    sanitize_html: bool = True
    check_sql_injection: bool = True
    check_xss: bool = True
    check_path_traversal: bool = True


class InputValidationMiddleware(BaseHTTPMiddleware):
    """입력 검증 미들웨어"""
    
    # SQL Injection 패턴
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|FROM|WHERE|ORDER BY|GROUP BY|HAVING)\b)",
        r"(--|#|\/\*|\*\/)",  # SQL 주석
        r"(\bOR\b\s*\d+\s*=\s*\d+)",  # OR 1=1
        r"(\bAND\b\s*\d+\s*=\s*\d+)",  # AND 1=1
        r"(;\s*(SELECT|INSERT|UPDATE|DELETE|DROP))",  # 명령어 체이닝
        r"(xp_cmdshell|sp_executesql)",  # SQL Server 위험 프로시저
        r"(CONCAT|CHAR|CHR|ASCII|SUBSTRING)",  # 문자열 조작 함수
    ]
    
    # XSS 패턴
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script 태그
        r"javascript:",  # JavaScript URL
        r"on\w+\s*=",  # 이벤트 핸들러
        r"<iframe[^>]*>",  # IFrame
        r"<object[^>]*>",  # Object 태그
        r"<embed[^>]*>",  # Embed 태그
        r"<img[^>]*onerror[^>]*>",  # 이미지 에러 핸들러
        r"vbscript:",  # VBScript URL
        r"data:text/html",  # Data URL
    ]
    
    # Path Traversal 패턴
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",  # ../
        r"\.\.\\" ,  # ..\
        r"%2e%2e/",  # URL 인코딩된 ../
        r"%2e%2e%5c",  # URL 인코딩된 ..\
        r"\.\.%2f",  # 혼합 인코딩
        r"\.\.%5c",  # 혼합 인코딩
    ]
    
    # Command Injection 패턴
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",  # 셸 메타문자
        r"\$\([^)]+\)",  # 명령 치환
        r"`[^`]+`",  # 백틱 명령 실행
        r">\s*\/dev\/null",  # 리다이렉션
        r"2>&1",  # 에러 리다이렉션
    ]
    
    def __init__(self, app, config: Optional[SecurityConfig] = None):
        super().__init__(app)
        self.config = config or SecurityConfig()
        
        # 컴파일된 정규식 패턴
        self.sql_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
        self.path_patterns = [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS]
        self.cmd_patterns = [re.compile(p) for p in self.COMMAND_INJECTION_PATTERNS]
    
    async def dispatch(self, request: Request, call_next):
        """요청 검증"""
        try:
            # Content-Length 검증
            if request.headers.get("content-length"):
                content_length = int(request.headers["content-length"])
                if content_length > self.config.max_request_size:
                    return self._error_response(
                        "REQUEST_TOO_LARGE",
                        f"요청 크기가 제한을 초과했습니다. (최대: {self.config.max_request_size} bytes)"
                    )
            
            # URL 경로 검증
            if self.config.check_path_traversal:
                if self._check_path_traversal(request.url.path):
                    return self._error_response(
                        "PATH_TRAVERSAL_DETECTED",
                        "잘못된 경로 요청입니다."
                    )
            
            # Query 파라미터 검증
            if request.query_params:
                validation_result = await self._validate_parameters(dict(request.query_params))
                if not validation_result["valid"]:
                    return self._error_response(
                        validation_result["error_code"],
                        validation_result["message"]
                    )
            
            # Request Body 검증 (JSON인 경우)
            if request.headers.get("content-type", "").startswith("application/json"):
                try:
                    body = await request.body()
                    if body:
                        json_data = json.loads(body)
                        
                        # JSON 깊이 검증
                        if self._get_json_depth(json_data) > self.config.max_json_depth:
                            return self._error_response(
                                "JSON_TOO_DEEP",
                                f"JSON 중첩 깊이가 제한을 초과했습니다. (최대: {self.config.max_json_depth})"
                            )
                        
                        # JSON 데이터 검증
                        validation_result = await self._validate_json_data(json_data)
                        if not validation_result["valid"]:
                            return self._error_response(
                                validation_result["error_code"],
                                validation_result["message"]
                            )
                        
                        # 검증된 body를 request state에 저장
                        request.state.validated_body = json_data
                
                except json.JSONDecodeError:
                    return self._error_response(
                        "INVALID_JSON",
                        "유효하지 않은 JSON 형식입니다."
                    )
            
            # 파일 업로드 검증
            if "multipart/form-data" in request.headers.get("content-type", ""):
                # TODO: 파일 업로드 검증 구현
                pass
            
            # 요청 처리
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"입력 검증 중 오류 발생: {e}")
            return self._error_response(
                "VALIDATION_ERROR",
                "요청 검증 중 오류가 발생했습니다."
            )
    
    async def _validate_parameters(self, params: Dict[str, str]) -> Dict[str, Any]:
        """파라미터 검증"""
        # 파라미터 개수 제한
        if len(params) > self.config.max_parameter_count:
            return {
                "valid": False,
                "error_code": "TOO_MANY_PARAMETERS",
                "message": f"파라미터 개수가 제한을 초과했습니다. (최대: {self.config.max_parameter_count})"
            }
        
        for key, value in params.items():
            # 키 검증
            if not self._is_valid_parameter_name(key):
                return {
                    "valid": False,
                    "error_code": "INVALID_PARAMETER_NAME",
                    "message": f"유효하지 않은 파라미터 이름입니다: {key}"
                }
            
            # 값 검증
            validation_result = self._validate_string(value)
            if not validation_result["valid"]:
                return validation_result
        
        return {"valid": True}
    
    async def _validate_json_data(self, data: Any, depth: int = 0) -> Dict[str, Any]:
        """JSON 데이터 재귀 검증"""
        if depth > self.config.max_json_depth:
            return {
                "valid": False,
                "error_code": "JSON_TOO_DEEP",
                "message": "JSON 중첩 깊이가 제한을 초과했습니다."
            }
        
        if isinstance(data, dict):
            for key, value in data.items():
                # 키 검증
                if not isinstance(key, str) or not self._is_valid_parameter_name(key):
                    return {
                        "valid": False,
                        "error_code": "INVALID_KEY",
                        "message": f"유효하지 않은 키입니다: {key}"
                    }
                
                # 값 재귀 검증
                result = await self._validate_json_data(value, depth + 1)
                if not result["valid"]:
                    return result
        
        elif isinstance(data, list):
            if len(data) > self.config.max_array_length:
                return {
                    "valid": False,
                    "error_code": "ARRAY_TOO_LONG",
                    "message": f"배열 길이가 제한을 초과했습니다. (최대: {self.config.max_array_length})"
                }
            
            for item in data:
                result = await self._validate_json_data(item, depth + 1)
                if not result["valid"]:
                    return result
        
        elif isinstance(data, str):
            return self._validate_string(data)
        
        return {"valid": True}
    
    def _validate_string(self, value: str) -> Dict[str, Any]:
        """문자열 검증"""
        # 길이 제한
        if len(value) > self.config.max_string_length:
            return {
                "valid": False,
                "error_code": "STRING_TOO_LONG",
                "message": f"문자열 길이가 제한을 초과했습니다. (최대: {self.config.max_string_length})"
            }
        
        # SQL Injection 검사
        if self.config.check_sql_injection:
            for pattern in self.sql_patterns:
                if pattern.search(value):
                    logger.warning(f"SQL Injection 패턴 감지: {value[:100]}")
                    return {
                        "valid": False,
                        "error_code": "SQL_INJECTION_DETECTED",
                        "message": "잠재적으로 위험한 SQL 패턴이 감지되었습니다."
                    }
        
        # XSS 검사
        if self.config.check_xss:
            for pattern in self.xss_patterns:
                if pattern.search(value):
                    logger.warning(f"XSS 패턴 감지: {value[:100]}")
                    return {
                        "valid": False,
                        "error_code": "XSS_DETECTED",
                        "message": "잠재적으로 위험한 스크립트 패턴이 감지되었습니다."
                    }
        
        # Command Injection 검사
        for pattern in self.cmd_patterns:
            if pattern.search(value):
                logger.warning(f"Command Injection 패턴 감지: {value[:100]}")
                return {
                    "valid": False,
                    "error_code": "COMMAND_INJECTION_DETECTED",
                    "message": "잠재적으로 위험한 명령어 패턴이 감지되었습니다."
                }
        
        return {"valid": True}
    
    def _check_path_traversal(self, path: str) -> bool:
        """Path Traversal 검사"""
        for pattern in self.path_patterns:
            if pattern.search(path):
                logger.warning(f"Path Traversal 패턴 감지: {path}")
                return True
        return False
    
    def _is_valid_parameter_name(self, name: str) -> bool:
        """파라미터 이름 유효성 검사"""
        # 영문, 숫자, 언더스코어, 대시만 허용
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", name))
    
    def _get_json_depth(self, obj: Any, current_depth: int = 0) -> int:
        """JSON 객체의 최대 깊이 계산"""
        if not isinstance(obj, (dict, list)):
            return current_depth
        
        if isinstance(obj, dict):
            return max(
                (self._get_json_depth(v, current_depth + 1) for v in obj.values()),
                default=current_depth
            )
        
        return max(
            (self._get_json_depth(item, current_depth + 1) for item in obj),
            default=current_depth
        )
    
    def _error_response(self, error_code: str, message: str) -> JSONResponse:
        """에러 응답 생성"""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": error_code,
                    "message": message
                }
            }
        )


def sanitize_html(text: str) -> str:
    """HTML 특수문자 이스케이프"""
    return html.escape(text)


def sanitize_filename(filename: str) -> str:
    """파일명 정제"""
    # 위험한 문자 제거
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    # 경로 구분자 제거
    filename = filename.replace("..", "")
    # 공백 처리
    filename = filename.strip()
    return filename


def validate_email(email: str) -> bool:
    """이메일 형식 검증"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """전화번호 형식 검증"""
    # 한국 전화번호 형식
    pattern = r'^(\+82-?|0)(1[0-9]|2|3[1-3]|4[1-4]|5[1-5]|6[1-4]|70)-?\d{3,4}-?\d{4}$'
    return bool(re.match(pattern, phone.replace(" ", "")))


def validate_url(url: str) -> bool:
    """URL 형식 검증"""
    pattern = r'^https?://[a-zA-Z0-9-._~:/?#[\]@!$&\'()*+,;=]+$'
    return bool(re.match(pattern, url))


def create_input_validator(
    check_sql: bool = True,
    check_xss: bool = True,
    check_path: bool = True,
    max_length: int = 10000
) -> InputValidationMiddleware:
    """입력 검증기 생성 헬퍼"""
    config = SecurityConfig(
        check_sql_injection=check_sql,
        check_xss=check_xss,
        check_path_traversal=check_path,
        max_string_length=max_length
    )
    return InputValidationMiddleware(None, config)