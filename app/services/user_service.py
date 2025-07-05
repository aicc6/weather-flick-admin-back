from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc
from typing import List, Optional
from datetime import datetime, timedelta
import logging
import math
import uuid
from passlib.context import CryptContext
from fastapi import Depends

from ..models import User, UserRole as DBUserRole
from ..schemas.user_schemas import (
    UserCreate, UserUpdate, UserListResponse,
    UserStats, UserSearchParams, UserRole
)
from ..database import get_db

logger = logging.getLogger(__name__)

# 비밀번호 해싱을 위한 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """사용자 관리 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user_create: UserCreate) -> User:
        """새 사용자 생성"""
        try:
            # 이메일 중복 확인
            existing_user = self.get_user_by_email(user_create.email)
            if existing_user:
                raise ValueError("이미 사용 중인 이메일입니다.")

            # 비밀번호 해싱
            hashed_password = pwd_context.hash(user_create.password)

            # 새 사용자 생성
            new_user = User(
                user_id=uuid.uuid4(),
                email=user_create.email,
                hashed_password=hashed_password,
                nickname=user_create.nickname,
                profile_image=user_create.profile_image,
                preferences=user_create.preferences,
                preferred_region=user_create.preferred_region,
                preferred_theme=user_create.preferred_theme,
                bio=user_create.bio,
                is_active=True,
                is_email_verified=False,
                role=DBUserRole.USER if user_create.role == UserRole.USER else DBUserRole.ADMIN,
                login_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)

            logger.info(f"새 사용자 생성 완료: {new_user.email}")
            return new_user

        except Exception as e:
            logger.error(f"사용자 생성 실패: {e}")
            self.db.rollback()
            raise

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
            # 삭제된 사용자 제외 (소프트 삭제된 사용자)
            query = self.db.query(User).filter(~User.email.like('deleted_%'))

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
            # 간단한 개별 쿼리로 안정성 확보 (복잡한 CASE 문 대신)
            total_users = self.db.query(User).count()
            active_users = self.db.query(User).filter(User.is_active == True).count()
            verified_users = self.db.query(User).filter(User.is_email_verified == True).count()
            admin_users = self.db.query(User).filter(User.role == DBUserRole.ADMIN).count()
            
            # 최근 30일 가입자
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_registrations = self.db.query(User).filter(
                User.created_at >= thirty_days_ago
            ).count()
            
            # 최근 7일 로그인 사용자 (NULL 값 제외)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_logins = self.db.query(User).filter(
                User.last_login.isnot(None),
                User.last_login >= seven_days_ago
            ).count()

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
            self.db.rollback()
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
        """사용자 삭제 (소프트 삭제 - 비활성화)"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            # 소프트 삭제: 비활성화 + 이메일에 삭제 표시
            user.is_active = False
            user.email = f"deleted_{user_id}_{user.email}"  # 이메일 충돌 방지
            user.updated_at = datetime.utcnow()
            
            self.db.commit()

            logger.info(f"사용자 삭제 완료 (소프트 삭제): {user_id}")
            return True

        except Exception as e:
            logger.error(f"사용자 삭제 실패 (ID: {user_id}): {e}")
            self.db.rollback()
            raise

    def reset_user_password(self, user_id: str, new_password: str = "123456789a") -> bool:
        """사용자 비밀번호 초기화 (레거시 메서드)"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            # 새 비밀번호 해싱
            hashed_password = pwd_context.hash(new_password)
            user.hashed_password = hashed_password
            user.updated_at = datetime.utcnow()

            self.db.commit()

            logger.info(f"사용자 비밀번호 초기화 완료: {user_id}")
            return True

        except Exception as e:
            logger.error(f"사용자 비밀번호 초기화 실패 (ID: {user_id}): {e}")
            self.db.rollback()
            return False

    def reset_user_password_with_temp(self, user_id: str, temp_password: str) -> bool:
        """사용자 비밀번호를 임시 비밀번호로 초기화"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            # 임시 비밀번호 해싱
            hashed_password = pwd_context.hash(temp_password)
            user.hashed_password = hashed_password
            user.updated_at = datetime.utcnow()

            self.db.commit()

            logger.info(f"사용자 임시 비밀번호 설정 완료: {user_id}")
            return True

        except Exception as e:
            logger.error(f"사용자 임시 비밀번호 설정 실패 (ID: {user_id}): {e}")
            self.db.rollback()
            return False

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