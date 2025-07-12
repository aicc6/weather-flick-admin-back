from fastapi import APIRouter, HTTPException, Query, Depends, Path
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from ..services.user_service import get_user_service, UserService
from ..schemas.user_schemas import (
    UserCreate, UserResponse, UserListResponse, UserStats, UserUpdate,
    UserSearchParams, UserRole
)
from ..database import get_db
from ..services.email_service import send_temp_password_email
from ..auth.utils import generate_temporary_password
from ..auth.dependencies import require_admin, require_super_admin
from ..auth.logging import log_admin_activity
from ..schemas.common import SuccessResponse
from ..models import Admin

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
    include_deleted: bool = Query(False, description="삭제된 사용자 포함 여부"),
    only_deleted: bool = Query(False, description="삭제된 사용자만 조회"),
    user_service: UserService = Depends(get_user_service),
    admin_user: Admin = Depends(require_admin)  # 관리자 권한 필수
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

        return user_service.get_users(
            page=page, 
            size=size, 
            search_params=search_params, 
            include_deleted=include_deleted,
            only_deleted=only_deleted
        )

    except Exception as e:
        logger.error(f"사용자 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 목록 조회 중 오류가 발생했습니다.")


@router.post("/", response_model=UserResponse)
async def create_user(
    user_create: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    새 사용자 생성

    - **email**: 이메일 주소 (고유해야 함)
    - **nickname**: 사용자 닉네임
    - **password**: 비밀번호 (최소 8자)
    - **role**: 사용자 역할 (USER 또는 ADMIN)
    """
    try:
        return user_service.create_user(user_create)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"사용자 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 생성 중 오류가 발생했습니다.")


@router.get("/stats")
async def get_user_statistics(
    user_service: UserService = Depends(get_user_service),
    admin_user: Admin = Depends(require_admin),  # 관리자 권한 필수
    db: Session = Depends(get_db)
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
        stats = user_service.get_user_statistics()

        # 관리자 활동 로그 (데이터베이스 저장 포함)
        await log_admin_activity(
            admin_user.admin_id,
            "USER_STATS_VIEW",
            f"사용자 통계 조회 (전체: {stats.total_users}명, 활성: {stats.active_users}명)",
            db=db
        )

        return {
            "success": True,
            "data": stats,
            "message": "사용자 통계를 성공적으로 조회했습니다.",
            "error": None,
            "meta": None,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"사용자 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 통계 조회 중 오류가 발생했습니다.")


@router.get("/search")
async def search_users(
    keyword: str = Query(..., description="검색 키워드"),
    limit: int = Query(20, ge=1, le=100, description="결과 제한"),
    user_service: UserService = Depends(get_user_service)
):
    """
    키워드로 사용자 검색

    - **keyword**: 이메일 또는 닉네임 검색 키워드
    - **limit**: 결과 개수 제한 (1-100)
    """
    try:
        users = user_service.search_users_by_keyword(keyword, limit)
        return {
            "success": True,
            "data": users,
            "message": f"'{keyword}' 검색 결과 {len(users)}명을 찾았습니다.",
            "error": None,
            "meta": None,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"사용자 검색 실패 (키워드: {keyword}): {e}")
        raise HTTPException(status_code=500, detail="사용자 검색 중 오류가 발생했습니다.")


@router.get("/region/{region}")
async def get_users_by_region(
    region: str = Path(..., description="지역명"),
    user_service: UserService = Depends(get_user_service)
):
    """
    지역별 사용자 조회

    - **region**: 선호 지역명
    """
    try:
        users = user_service.get_users_by_region(region)
        return {"users": users, "count": len(users), "region": region}

    except Exception as e:
        logger.error(f"지역별 사용자 조회 실패 (지역: {region}): {e}")
        raise HTTPException(status_code=500, detail="지역별 사용자 조회 중 오류가 발생했습니다.")




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


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_update: UserUpdate,
    user_id: str = Path(..., description="사용자 ID"),
    user_service: UserService = Depends(get_user_service)
):
    """
    사용자 정보 수정

    - **user_id**: 수정할 사용자의 UUID
    - 수정 가능한 필드: nickname, profile_image, preferences, preferred_region, preferred_theme, bio
    """
    try:
        user = user_service.update_user(user_id, user_update)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 정보 수정 실패 (ID: {user_id}): {e}")
        raise HTTPException(status_code=500, detail="사용자 정보 수정 중 오류가 발생했습니다.")


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str = Path(..., description="사용자 ID"),
    user_service: UserService = Depends(get_user_service)
):
    """
    사용자 활성화

    - **user_id**: 활성화할 사용자의 UUID
    """
    try:
        success = user_service.activate_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        return {"message": "사용자가 활성화되었습니다.", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 활성화 실패 (ID: {user_id}): {e}")
        raise HTTPException(status_code=500, detail="사용자 활성화 중 오류가 발생했습니다.")


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str = Path(..., description="사용자 ID"),
    user_service: UserService = Depends(get_user_service)
):
    """
    사용자 비활성화

    - **user_id**: 비활성화할 사용자의 UUID
    """
    try:
        success = user_service.deactivate_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        return {"message": "사용자가 비활성화되었습니다.", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 비활성화 실패 (ID: {user_id}): {e}")
        raise HTTPException(status_code=500, detail="사용자 비활성화 중 오류가 발생했습니다.")


@router.delete("/{user_id}")
async def delete_user(
    user_id: str = Path(..., description="사용자 ID"),
    user_service: UserService = Depends(get_user_service),
    admin_user: Admin = Depends(require_super_admin)  # 슈퍼관리자 권한 필수
):
    """
    사용자 삭제

    - **user_id**: 삭제할 사용자의 UUID
    - **주의**: 이 작업은 되돌릴 수 없습니다.
    """
    try:
        success = user_service.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        return {"message": "사용자가 삭제되었습니다.", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 삭제 실패 (ID: {user_id}): {e}")
        raise HTTPException(status_code=500, detail="사용자 삭제 중 오류가 발생했습니다.")


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: str = Path(..., description="사용자 ID"),
    user_service: UserService = Depends(get_user_service),
    db: Session = Depends(get_db)
):
    """
    사용자 비밀번호 초기화 (이메일 전송)

    - **user_id**: 비밀번호를 초기화할 사용자의 UUID
    - 임시 비밀번호가 사용자 이메일로 전송됩니다.
    """
    try:
        # 사용자 정보 조회
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        if not user.email:
            raise HTTPException(
                status_code=400,
                detail="이메일 주소가 등록되지 않은 사용자입니다."
            )

        # 보안 강화된 임시 비밀번호 생성
        temp_password = generate_temporary_password()

        # 비밀번호 업데이트
        success = user_service.reset_user_password_with_temp(user_id, temp_password)
        if not success:
            raise HTTPException(status_code=500, detail="비밀번호 업데이트에 실패했습니다.")

        # 이메일 전송 시도
        try:
            email_sent = await send_temp_password_email(
                email=user.email,
                temp_password=temp_password,
                user_name=user.nickname or user.email
            )

            if email_sent:
                return {
                    "message": f"사용자 '{user.nickname or user.email}' 비밀번호가 초기화되었습니다.",
                    "user_id": user_id,
                    "email_sent": True,
                    "email": user.email,
                    "note": "임시 비밀번호가 이메일로 전송되었습니다. 24시간 후 만료됩니다."
                }
            else:
                # 이메일 전송 실패 시 응답에 비밀번호 포함 (백업 옵션)
                return {
                    "message": f"사용자 '{user.nickname or user.email}' 비밀번호가 초기화되었습니다.",
                    "user_id": user_id,
                    "email_sent": False,
                    "temporary_password": temp_password,
                    "note": "이메일 전송에 실패했습니다. 임시 비밀번호를 안전하게 전달해주세요."
                }

        except Exception as email_error:
            logger.error(f"이메일 전송 실패 (User: {user_id}): {email_error}")
            # 이메일 전송 중 오류 발생 시
            return {
                "message": f"사용자 '{user.nickname or user.email}' 비밀번호가 초기화되었습니다.",
                "user_id": user_id,
                "email_sent": False,
                "temporary_password": temp_password,
                "note": f"이메일 전송 중 오류가 발생했습니다: {str(email_error)}"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 비밀번호 초기화 실패 (ID: {user_id}): {e}")
        raise HTTPException(status_code=500, detail="사용자 비밀번호 초기화 중 오류가 발생했습니다.")

@router.delete("/{user_id}/hard")
async def hard_delete_user(
    user_id: str = Path(..., description="사용자 ID"),
    user_service: UserService = Depends(get_user_service),
    admin_user: Admin = Depends(require_super_admin)  # 슈퍼관리자 권한 필수
):
    """
    탈퇴 회원(이메일이 deleted_로 시작) 영구 삭제 (DB에서 완전 삭제)

    - **user_id**: 삭제할 사용자의 UUID
    - **주의**: 이 작업은 되돌릴 수 없습니다.
    """
    try:
        success = user_service.hard_delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        # 관리자 활동 로그
        await log_admin_activity(
            admin_user.admin_id,
            "USER_HARD_DELETE",
            f"탈퇴 회원 영구 삭제 (ID: {user_id})"
        )

        return {"message": "탈퇴 회원이 영구 삭제되었습니다.", "user_id": user_id}

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"탈퇴 회원 하드 삭제 실패 (ID: {user_id}): {e}")
        raise HTTPException(status_code=500, detail="탈퇴 회원 영구 삭제 중 오류가 발생했습니다.")
