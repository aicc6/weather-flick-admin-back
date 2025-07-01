from fastapi import APIRouter, HTTPException, Query, Depends, Path
from typing import List, Optional
from sqlalchemy.orm import Session
import logging

from .service import get_user_service, UserService
from .schemas import (
    UserResponse, UserListResponse, UserStats, UserUpdate,
    UserSearchParams, UserRole
)
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    email: Optional[str] = Query(None, description="이메일 필터"),
    nickname: Optional[str] = Query(None, description="닉네임 필터"),
    role: Optional[UserRole] = Query(None, description="역할 필터"),
    is_active: Optional[bool] = Query(None, description="활성 상태 필터"),
    is_email_verified: Optional[bool] = Query(None, description="이메일 인증 상태 필터"),
    preferred_region: Optional[str] = Query(None, description="선호 지역 필터"),
    user_service: UserService = Depends(get_user_service)
):
    """
    사용자 목록 조회

    - **page**: 페이지 번호 (1부터 시작)
    - **size**: 페이지 크기 (1-100)
    - 다양한 필터 옵션 지원
    """
    try:
        search_params = UserSearchParams(
            email=email,
            nickname=nickname,
            role=role,
            is_active=is_active,
            is_email_verified=is_email_verified,
            preferred_region=preferred_region
        )

        return user_service.get_users(page=page, size=size, search_params=search_params)

    except Exception as e:
        logger.error(f"사용자 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 목록 조회 중 오류가 발생했습니다.")


@router.get("/stats", response_model=UserStats)
async def get_user_statistics(
    user_service: UserService = Depends(get_user_service)
):
    """
    사용자 통계 조회

    - 전체 사용자 수
    - 활성 사용자 수
    - 이메일 인증 사용자 수
    - 관리자 수
    - 최근 가입자 수 (30일)
    - 최근 로그인 사용자 수 (7일)
    """
    try:
        return user_service.get_user_statistics()

    except Exception as e:
        logger.error(f"사용자 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 통계 조회 중 오류가 발생했습니다.")


@router.get("/health")
async def users_health_check():
    """사용자 서비스 상태 확인"""
    return {
        "status": "healthy",
        "service": "users",
        "timestamp": "2025-07-01T12:30:00"
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str = Path(..., description="사용자 ID"),
    user_service: UserService = Depends(get_user_service)
):
    """
    사용자 ID로 사용자 정보 조회

    - **user_id**: 조회할 사용자의 UUID
    """
    try:
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 조회 실패 (ID: {user_id}): {e}")
        raise HTTPException(status_code=500, detail="사용자 조회 중 오류가 발생했습니다.")
