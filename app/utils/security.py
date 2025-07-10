"""
보안 관련 유틸리티 함수
비밀번호 해싱, 토큰 생성, 암호화 등
"""

import secrets
import hashlib
import hmac
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import base64
import re


# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)


def generate_secure_token(length: int = 32) -> str:
    """보안 토큰 생성"""
    return secrets.token_urlsafe(length)


def generate_api_key() -> str:
    """API 키 생성"""
    prefix = "wf_"  # Weather Flick prefix
    token = secrets.token_hex(32)
    return f"{prefix}{token}"


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """JWT 리프레시 토큰 생성"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """JWT 토큰 검증"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None


def generate_csrf_token() -> str:
    """CSRF 토큰 생성"""
    return secrets.token_hex(32)


def verify_csrf_token(token: str, stored_token: str) -> bool:
    """CSRF 토큰 검증"""
    return hmac.compare_digest(token, stored_token)


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """입력값 정제"""
    # 길이 제한
    text = text[:max_length]
    
    # 위험한 문자 제거
    text = re.sub(r'[<>&"\'`]', '', text)
    
    # 제어 문자 제거
    text = ''.join(char for char in text if ord(char) >= 32)
    
    return text.strip()


def is_strong_password(password: str) -> Dict[str, Any]:
    """비밀번호 강도 검증"""
    errors = []
    
    # 최소 길이
    if len(password) < 8:
        errors.append("비밀번호는 최소 8자 이상이어야 합니다.")
    
    # 대문자 포함
    if not re.search(r'[A-Z]', password):
        errors.append("비밀번호에 대문자가 포함되어야 합니다.")
    
    # 소문자 포함
    if not re.search(r'[a-z]', password):
        errors.append("비밀번호에 소문자가 포함되어야 합니다.")
    
    # 숫자 포함
    if not re.search(r'\d', password):
        errors.append("비밀번호에 숫자가 포함되어야 합니다.")
    
    # 특수문자 포함
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("비밀번호에 특수문자가 포함되어야 합니다.")
    
    # 연속된 문자 검사
    if re.search(r'(.)\1{2,}', password):
        errors.append("같은 문자가 3번 이상 연속될 수 없습니다.")
    
    # 일반적인 패턴 검사
    common_patterns = ['123', 'abc', 'password', 'admin', 'qwerty']
    for pattern in common_patterns:
        if pattern in password.lower():
            errors.append(f"비밀번호에 일반적인 패턴 '{pattern}'이 포함되어 있습니다.")
    
    return {
        "is_strong": len(errors) == 0,
        "errors": errors,
        "score": max(0, 5 - len(errors))  # 0-5 점수
    }


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """민감한 데이터 마스킹"""
    if len(data) <= visible_chars * 2:
        return mask_char * len(data)
    
    start = data[:visible_chars]
    end = data[-visible_chars:]
    masked = mask_char * (len(data) - visible_chars * 2)
    
    return f"{start}{masked}{end}"


def encrypt_data(data: str, key: str) -> str:
    """간단한 데이터 암호화 (프로덕션에서는 더 강력한 암호화 사용)"""
    # 실제 프로덕션에서는 AES 등의 강력한 암호화 사용 권장
    key_bytes = key.encode()[:32].ljust(32, b'0')
    data_bytes = data.encode()
    
    encrypted = bytearray()
    for i, byte in enumerate(data_bytes):
        encrypted.append(byte ^ key_bytes[i % 32])
    
    return base64.b64encode(encrypted).decode()


def decrypt_data(encrypted_data: str, key: str) -> str:
    """데이터 복호화"""
    key_bytes = key.encode()[:32].ljust(32, b'0')
    encrypted_bytes = base64.b64decode(encrypted_data)
    
    decrypted = bytearray()
    for i, byte in enumerate(encrypted_bytes):
        decrypted.append(byte ^ key_bytes[i % 32])
    
    return decrypted.decode()


def generate_otp(length: int = 6) -> str:
    """일회용 비밀번호(OTP) 생성"""
    return ''.join(secrets.choice('0123456789') for _ in range(length))


def hash_file(file_path: str, algorithm: str = "sha256") -> str:
    """파일 해시 생성"""
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def generate_session_id() -> str:
    """세션 ID 생성"""
    timestamp = str(datetime.utcnow().timestamp())
    random_part = secrets.token_hex(16)
    
    session_data = f"{timestamp}:{random_part}"
    return hashlib.sha256(session_data.encode()).hexdigest()


def validate_ip_address(ip: str) -> bool:
    """IP 주소 유효성 검증"""
    # IPv4 패턴
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    
    if re.match(ipv4_pattern, ip):
        # 각 옥텟이 0-255 범위인지 확인
        octets = ip.split('.')
        return all(0 <= int(octet) <= 255 for octet in octets)
    
    # IPv6 간단 검증 (완전하지 않음)
    ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){7}[0-9a-fA-F]{0,4}$'
    return bool(re.match(ipv6_pattern, ip))


def rate_limit_key(user_id: Optional[str], ip: str, endpoint: str) -> str:
    """Rate limiting을 위한 키 생성"""
    if user_id:
        return f"rate_limit:user:{user_id}:{endpoint}"
    return f"rate_limit:ip:{ip}:{endpoint}"