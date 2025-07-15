from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.utils import verify_token
from app.database import get_db
from app.models import Admin

# HTTP Bearer 토큰 스키마
security = HTTPBearer()

def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Admin:
    """현재 인증된 관리자 정보 가져오기"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증이 필요합니다",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 토큰 검증
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    # 토큰 데이터 추출
    admin_id: int = payload.get("sub")
    email: str = payload.get("email")
    token_type: str = payload.get("type")

    if admin_id is None or email is None or token_type != "admin":
        raise credentials_exception

    # 데이터베이스에서 관리자 정보 조회 (admin_id 컬럼 사용)
    admin = db.query(Admin).filter(Admin.admin_id == int(admin_id)).first()
    if admin is None:
        raise credentials_exception

    # 계정 상태 확인 - INACTIVE나 LOCKED 상태일 때만 차단
    if admin.status and admin.status in ["INACTIVE", "LOCKED"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )

    return admin

def get_current_active_admin(
    current_admin: Admin = Depends(get_current_admin)
) -> Admin:
    """현재 활성화된 관리자 정보 가져오기"""
    # get_current_admin에서 이미 상태 체크를 했으므로 중복 체크 제거
    return current_admin

# Cursor 규칙에 따른 권한 관리 함수들
async def require_admin(
    current_admin: Admin = Depends(get_current_active_admin)
) -> Admin:
    """일반 관리자 이상 권한 필요"""
    # Admin 모델에서는 모든 사용자가 관리자이므로 활성 상태만 확인
    return current_admin

async def require_super_admin(
    current_admin: Admin = Depends(get_current_active_admin)
) -> Admin:
    """슈퍼관리자 권한 필요"""
    # 슈퍼관리자 판별: is_superuser 필드 확인
    if not current_admin.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="슈퍼관리자 권한이 필요합니다"
        )
    return current_admin
