"""
핵심 보안 설정 및 의존성
JWT, 인증, 권한 관리
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import settings
from app.database import SessionLocal
from app.models import Admin
from sqlalchemy.orm import Session


# 비밀번호 암호화 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer 스키마
security = HTTPBearer()


class TokenData(BaseModel):
    """토큰 데이터 모델"""
    sub: str
    exp: datetime
    type: str
    permissions: List[str] = []
    role: str = "user"


class SecurityService:
    """보안 관련 서비스"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """비밀번호 해싱"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """액세스 토큰 생성"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.access_token_expire_minutes
            )
        
        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """리프레시 토큰 생성"""
        to_encode = data.copy()
        
        expire = datetime.utcnow() + timedelta(days=7)  # 7일
        
        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow()
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm
        )
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[TokenData]:
        """토큰 디코드"""
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            
            token_data = TokenData(
                sub=payload.get("sub"),
                exp=datetime.fromtimestamp(payload.get("exp")),
                type=payload.get("type", "access"),
                permissions=payload.get("permissions", []),
                role=payload.get("role", "user")
            )
            
            return token_data
            
        except JWTError:
            return None
    
    @staticmethod
    def verify_token_type(token_data: TokenData, expected_type: str) -> bool:
        """토큰 타입 검증"""
        return token_data.type == expected_type


# 의존성 함수들
def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Admin:
    """현재 인증된 사용자 가져오기"""
    token = credentials.credentials
    
    # 토큰 디코드
    token_data = SecurityService.decode_token(token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 유효하지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 토큰 타입 확인
    if not SecurityService.verify_token_type(token_data, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 토큰 타입입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 토큰 만료 확인
    if token_data.exp < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 사용자 조회
    user = db.query(Admin).filter(Admin.id == int(token_data.sub)).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다."
        )
    
    # Request state에 사용자 정보 저장 (미들웨어에서 사용)
    request.state.user = user
    
    return user


async def get_current_active_superuser(
    current_user: Admin = Depends(get_current_user),
) -> Admin:
    """현재 활성 슈퍼유저 가져오기"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="슈퍼유저 권한이 필요합니다."
        )
    return current_user


class PermissionChecker:
    """권한 확인 의존성 클래스"""
    
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
    
    async def __call__(
        self,
        current_user: Admin = Depends(get_current_user)
    ) -> Admin:
        """권한 확인"""
        # 슈퍼유저는 모든 권한 보유
        if current_user.is_superuser:
            return current_user
        
        # 사용자 권한 확인 (RBAC 시스템과 연동)
        user_permissions = getattr(current_user, 'permissions', [])
        
        for permission in self.required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"권한이 부족합니다: {permission}"
                )
        
        return current_user


# 권한 상수
class Permissions:
    """시스템 권한 상수"""
    # 사용자 관리
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # 관리자 관리
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    ADMIN_DELETE = "admin:delete"
    
    # 시스템 관리
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    SYSTEM_ADMIN = "system:admin"
    
    # 컨텐츠 관리
    CONTENT_READ = "content:read"
    CONTENT_WRITE = "content:write"
    CONTENT_DELETE = "content:delete"
    
    # 로그 관리
    LOG_READ = "log:read"
    LOG_DELETE = "log:delete"
    
    # 분석
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"


# 권한 체크 함수
def require_permissions(*permissions: str):
    """권한 요구 데코레이터/의존성"""
    return PermissionChecker(list(permissions))


# 보안 관련 유틸리티 함수
def validate_password_strength(password: str) -> Dict[str, Any]:
    """비밀번호 강도 검증"""
    errors = []
    
    if len(password) < 8:
        errors.append("비밀번호는 최소 8자 이상이어야 합니다.")
    
    if not any(c.isupper() for c in password):
        errors.append("비밀번호에 대문자가 포함되어야 합니다.")
    
    if not any(c.islower() for c in password):
        errors.append("비밀번호에 소문자가 포함되어야 합니다.")
    
    if not any(c.isdigit() for c in password):
        errors.append("비밀번호에 숫자가 포함되어야 합니다.")
    
    special_chars = "!@#$%^&*(),.?\":{}|<>"
    if not any(c in special_chars for c in password):
        errors.append("비밀번호에 특수문자가 포함되어야 합니다.")
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "strength": "strong" if len(errors) == 0 else "weak"
    }


def generate_temp_password(length: int = 12) -> str:
    """임시 비밀번호 생성"""
    import string
    import secrets
    
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    # 최소 요구사항 충족 확인
    while True:
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*" for c in password)
        
        if all([has_upper, has_lower, has_digit, has_special]):
            break
        
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    return password