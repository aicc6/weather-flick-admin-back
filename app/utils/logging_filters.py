"""
로그 필터링 및 민감정보 마스킹 유틸리티
"""

import logging
import re
from typing import Any, Dict, Union


class SensitiveDataFilter(logging.Filter):
    """민감정보 마스킹 로그 필터"""

    def __init__(self, name: str = ""):
        super().__init__(name)
        
        # 민감정보 패턴 정의
        self.sensitive_patterns = {
            # API 키 패턴들
            'weather_api_key': re.compile(r'([a-zA-Z0-9]{26})', re.IGNORECASE),
            'google_api_key': re.compile(r'(AIza[0-9A-Za-z_-]{35})', re.IGNORECASE),
            'bearer_token': re.compile(r'(Bearer\s+[A-Za-z0-9_-]+)', re.IGNORECASE),
            'authorization': re.compile(r'(Authorization:\s*[^\s]+)', re.IGNORECASE),
            
            # JWT 토큰 패턴
            'jwt_token': re.compile(r'(eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*)', re.IGNORECASE),
            
            # 임시 인증 코드 (8자리 이상의 랜덤 문자열)
            'temp_auth_code': re.compile(r'([A-Za-z0-9]{8,})', re.IGNORECASE),
            
            # 비밀번호 패턴 (키워드 주변)
            'password': re.compile(r'(password[\'\":\s]*[\'\"]\w+[\'\"]\s*)', re.IGNORECASE),
            'passwd': re.compile(r'(passwd[\'\":\s]*[\'\"]\w+[\'\"]\s*)', re.IGNORECASE),
            
            # 이메일 일부 마스킹
            'email': re.compile(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', re.IGNORECASE),
            
            # API 키 헤더
            'x_api_key': re.compile(r'(x-api-key:\s*[^\s]+)', re.IGNORECASE),
            
            # 클라이언트 시크릿
            'client_secret': re.compile(r'(client_secret[\'\":\s]*[\'\"]\w+[\'\"]\s*)', re.IGNORECASE),
        }

    def mask_sensitive_data(self, message: str) -> str:
        """민감정보 마스킹 처리"""
        if not isinstance(message, str):
            return message
            
        masked_message = message
        
        # 각 패턴에 대해 마스킹 적용
        for pattern_name, pattern in self.sensitive_patterns.items():
            if pattern_name == 'email':
                # 이메일은 부분 마스킹 (첫 2글자 + *** + 도메인)
                def mask_email(match):
                    email = match.group(1)
                    if '@' in email:
                        local, domain = email.split('@', 1)
                        if len(local) > 2:
                            masked_local = local[:2] + '*' * (len(local) - 2)
                        else:
                            masked_local = local[0] + '*' * (len(local) - 1)
                        return f"{masked_local}@{domain}"
                    return email
                
                masked_message = pattern.sub(mask_email, masked_message)
                
            elif pattern_name == 'temp_auth_code':
                # 임시 인증 코드는 처음 4글자만 표시
                def mask_auth_code(match):
                    code = match.group(1)
                    if len(code) >= 8:  # 8자리 이상만 마스킹
                        return code[:4] + '*' * (len(code) - 4)
                    return code
                
                masked_message = pattern.sub(mask_auth_code, masked_message)
                
            elif pattern_name in ['weather_api_key', 'google_api_key']:
                # API 키는 처음 4글자 + *** + 마지막 4글자
                def mask_api_key(match):
                    key = match.group(1)
                    if len(key) > 8:
                        return key[:4] + '*' * (len(key) - 8) + key[-4:]
                    return '*' * len(key)
                
                masked_message = pattern.sub(mask_api_key, masked_message)
                
            elif pattern_name == 'jwt_token':
                # JWT 토큰은 헤더.페이로드.*** 형태로 마스킹
                def mask_jwt(match):
                    token = match.group(1)
                    parts = token.split('.')
                    if len(parts) == 3:
                        return f"{parts[0]}.{parts[1][:10]}...***"
                    return "***"
                
                masked_message = pattern.sub(mask_jwt, masked_message)
                
            else:
                # 기타 민감정보는 완전 마스킹
                masked_message = pattern.sub(lambda m: '***[REDACTED]***', masked_message)
        
        return masked_message

    def filter(self, record: logging.LogRecord) -> bool:
        """로그 레코드 필터링"""
        # 메시지 마스킹
        if hasattr(record, 'msg') and record.msg:
            record.msg = self.mask_sensitive_data(str(record.msg))
        
        # args 마스킹 (format string arguments)
        if hasattr(record, 'args') and record.args:
            masked_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    masked_args.append(self.mask_sensitive_data(arg))
                else:
                    masked_args.append(arg)
            record.args = tuple(masked_args)
        
        return True


class HTTPRequestFilter(logging.Filter):
    """HTTP 요청 로그 전용 필터"""

    def __init__(self, name: str = ""):
        super().__init__(name)
        self.sensitive_filter = SensitiveDataFilter()

    def filter(self, record: logging.LogRecord) -> bool:
        """HTTP 요청 관련 로그 필터링"""
        # 특정 로그 포맷만 처리
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            msg = record.msg.lower()
            
            # HTTP 요청 관련 로그인지 확인
            http_indicators = [
                'request', 'response', 'api', 'http', 'header', 'query', 
                'post', 'get', 'put', 'delete', 'patch', 'authorization'
            ]
            
            if any(indicator in msg for indicator in http_indicators):
                # 민감정보 마스킹 적용
                record.msg = self.sensitive_filter.mask_sensitive_data(record.msg)
                
                if hasattr(record, 'args') and record.args:
                    masked_args = []
                    for arg in record.args:
                        if isinstance(arg, str):
                            masked_args.append(self.sensitive_filter.mask_sensitive_data(arg))
                        else:
                            masked_args.append(arg)
                    record.args = tuple(masked_args)
        
        return True


def mask_dict_values(data: Dict[str, Any], keys_to_mask: list = None) -> Dict[str, Any]:
    """딕셔너리 값 마스킹 유틸리티"""
    if keys_to_mask is None:
        keys_to_mask = [
            'password', 'passwd', 'secret', 'token', 'key', 'auth', 
            'authorization', 'api_key', 'client_secret', 'refresh_token',
            'access_token', 'temp_code', 'verification_code'
        ]
    
    masked_data = {}
    sensitive_filter = SensitiveDataFilter()
    
    for key, value in data.items():
        key_lower = key.lower()
        
        # 키 이름으로 민감정보 판단
        if any(mask_key in key_lower for mask_key in keys_to_mask):
            if isinstance(value, str) and len(value) > 4:
                masked_data[key] = value[:2] + '*' * (len(value) - 4) + value[-2:]
            else:
                masked_data[key] = '***'
        elif isinstance(value, str):
            # 값 자체에서 민감정보 패턴 검사
            masked_data[key] = sensitive_filter.mask_sensitive_data(value)
        elif isinstance(value, dict):
            # 중첩 딕셔너리 재귀 처리
            masked_data[key] = mask_dict_values(value, keys_to_mask)
        else:
            masked_data[key] = value
    
    return masked_data


# 보안 로그용 전용 포맷터
class SecurityLogFormatter(logging.Formatter):
    """보안 이벤트 전용 로그 포맷터"""
    
    def format(self, record: logging.LogRecord) -> str:
        # 기본 포맷팅
        formatted = super().format(record)
        
        # 보안 이벤트 태그 추가
        if hasattr(record, 'security_event'):
            formatted = f"[SECURITY:{record.security_event}] {formatted}"
        
        return formatted