import secrets
import string
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# 패스워드 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> dict | None:
    """JWT 토큰 검증"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None

def create_admin_token(admin_id: int, email: str) -> str:
    """관리자용 JWT 토큰 생성"""
    token_data = {
        "sub": str(admin_id),
        "email": email,
        "type": "admin"
    }
    return create_access_token(token_data)

def create_refresh_token(admin_id: int, email: str) -> str:
    """리프레시 토큰 생성"""
    token_data = {
        "sub": str(admin_id),
        "email": email,
        "type": "refresh"
    }
    # 리프레시 토큰은 30일 유효
    return create_access_token(token_data, expires_delta=timedelta(days=30))

def generate_temporary_password(length: int = 12) -> str:
    """보안 강화된 임시 비밀번호 생성"""
    # 각 문자 유형별로 최소 1개씩 포함
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special_chars = "!@#$%^&*"

    # 최소 요구사항: 각 유형별로 1개씩
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special_chars)
    ]

    # 나머지 길이만큼 모든 문자에서 랜덤 선택
    all_chars = lowercase + uppercase + digits + special_chars
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))

    # 리스트를 섞어서 패턴 예측 방지
    secrets.SystemRandom().shuffle(password)

    return ''.join(password)
