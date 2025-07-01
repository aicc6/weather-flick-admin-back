from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import math
from fastapi import Depends

from ..models import User, UserRole as DBUserRole
from .schemas import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    UserStats, UserSearchParams, UserRole
)
from ..database import get_db

logger = logging.getLogger(__name__)


class UserService:
    """사용자 관리 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """사용자 ID로 사용자 조회"""
        try:
            return self.db.query(User).filter(User.user_id == user_id).first()
        except Exception as e:
            logger.error(f"사용자 조회 실패 (ID: {user_id}): {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        try:
            return self.db.query(User).filter(User.email == email).first()
        except Exception as e:
            logger.error(f"사용자 조회 실패 (Email: {email}): {e}")
            return None

    def get_users(
        self,
        page: int = 1,
        size: int = 20,
        search_params: Optional[UserSearchParams] = None
    ) -> UserListResponse:
        """사용자 목록 조회 (페이징, 필터링 지원)"""
        try:
            query = self.db.query(User)

            # 검색 조건 적용
            if search_params:
                if search_params.email:
                    query = query.filter(User.email.ilike(f"%{search_params.email}%"))

                if search_params.nickname:
                    query = query.filter(User.nickname.ilike(f"%{search_params.nickname}%"))

                if search_params.role:
                    db_role = DBUserRole.USER if search_params.role == UserRole.USER else DBUserRole.ADMIN
                    query = query.filter(User.role == db_role)

                if search_params.is_active is not None:
                    query = query.filter(User.is_active == search_params.is_active)

                if search_params.is_email_verified is not None:
                    query = query.filter(User.is_email_verified == search_params.is_email_verified)

                if search_params.preferred_region:
                    query = query.filter(User.preferred_region.ilike(f"%{search_params.preferred_region}%"))

                if search_params.created_after:
                    query = query.filter(User.created_at >= search_params.created_after)

                if search_params.created_before:
                    query = query.filter(User.created_at <= search_params.created_before)

            # 총 개수 계산
            total = query.count()

            # 페이징 적용
            offset = (page - 1) * size
            users = query.order_by(desc(User.created_at)).offset(offset).limit(size).all()

            # 총 페이지 수 계산
            total_pages = math.ceil(total / size)

            return UserListResponse(
                users=users,
                total=total,
                page=page,
                size=size,
                total_pages=total_pages
            )

        except Exception as e:
            logger.error(f"사용자 목록 조회 실패: {e}")
            raise

    def get_user_statistics(self) -> UserStats:
        """사용자 통계 조회"""
        try:
            # 기본 통계
            total_users = self.db.query(func.count(User.user_id)).scalar() or 0
            active_users = self.db.query(func.count(User.user_id)).filter(User.is_active == True).scalar() or 0
            verified_users = self.db.query(func.count(User.user_id)).filter(User.is_email_verified == True).scalar() or 0
            admin_users = self.db.query(func.count(User.user_id)).filter(User.role == DBUserRole.ADMIN).scalar() or 0

            # 최근 30일 가입자
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_registrations = self.db.query(func.count(User.user_id)).filter(
                User.created_at >= thirty_days_ago
            ).scalar() or 0

            # 최근 7일 로그인 사용자
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_logins = self.db.query(func.count(User.user_id)).filter(
                User.last_login >= seven_days_ago
            ).scalar() or 0

            return UserStats(
                total_users=total_users,
                active_users=active_users,
                verified_users=verified_users,
                admin_users=admin_users,
                recent_registrations=recent_registrations,
                recent_logins=recent_logins
            )

        except Exception as e:
            logger.error(f"사용자 통계 조회 실패: {e}")
            raise

    def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[User]:
        """사용자 정보 수정"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return None

            # 업데이트할 필드들 적용
            update_data = user_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user, field, value)

            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)

            logger.info(f"사용자 정보 수정 완료: {user_id}")
            return user

        except Exception as e:
            logger.error(f"사용자 정보 수정 실패 (ID: {user_id}): {e}")
            self.db.rollback()
            raise

    def deactivate_user(self, user_id: str) -> bool:
        """사용자 비활성화"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            user.is_active = False
            user.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"사용자 비활성화 완료: {user_id}")
            return True

        except Exception as e:
            logger.error(f"사용자 비활성화 실패 (ID: {user_id}): {e}")
            self.db.rollback()
            raise

    def activate_user(self, user_id: str) -> bool:
        """사용자 활성화"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            user.is_active = True
            user.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"사용자 활성화 완료: {user_id}")
            return True

        except Exception as e:
            logger.error(f"사용자 활성화 실패 (ID: {user_id}): {e}")
            self.db.rollback()
            raise

    def delete_user(self, user_id: str) -> bool:
        """사용자 삭제 (실제 DB에서 삭제)"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            self.db.delete(user)
            self.db.commit()

            logger.info(f"사용자 삭제 완료: {user_id}")
            return True

        except Exception as e:
            logger.error(f"사용자 삭제 실패 (ID: {user_id}): {e}")
            self.db.rollback()
            raise

    def search_users_by_keyword(self, keyword: str, limit: int = 20) -> List[User]:
        """키워드로 사용자 검색 (이메일, 닉네임)"""
        try:
            return self.db.query(User).filter(
                or_(
                    User.email.ilike(f"%{keyword}%"),
                    User.nickname.ilike(f"%{keyword}%")
                )
            ).limit(limit).all()

        except Exception as e:
            logger.error(f"사용자 검색 실패 (키워드: {keyword}): {e}")
            raise

    def get_users_by_region(self, region: str) -> List[User]:
        """지역별 사용자 조회"""
        try:
            return self.db.query(User).filter(
                User.preferred_region.ilike(f"%{region}%")
            ).all()

        except Exception as e:
            logger.error(f"지역별 사용자 조회 실패 (지역: {region}): {e}")
            raise


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """UserService 인스턴스 반환"""
    return UserService(db)
