import logging
import math
import uuid
from datetime import datetime, timedelta

from fastapi import Depends
from passlib.context import CryptContext
from sqlalchemy import desc, or_, text
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..models import UserRole as DBUserRole
from ..schemas.user_schemas import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserRole,
    UserSearchParams,
    UserStats,
    UserUpdate,
)

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
                role=DBUserRole.USER
                if user_create.role == UserRole.USER
                else DBUserRole.ADMIN,
                login_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
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

    def get_user_by_id(self, user_id: str) -> User | None:
        """사용자 ID로 사용자 조회"""
        try:
            return self.db.query(User).filter(User.user_id == user_id).first()
        except Exception as e:
            logger.error(f"사용자 조회 실패 (ID: {user_id}): {e}")
            return None

    def get_user_by_email(self, email: str) -> User | None:
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
        search_params: UserSearchParams | None = None,
        include_deleted: bool = False,
        only_deleted: bool = False,
    ) -> UserListResponse:
        """사용자 목록 조회 (페이징, 필터링 지원)"""
        try:
            # 기본 쿼리
            query = self.db.query(User)

            # 삭제된 사용자 필터링
            if only_deleted:
                # 삭제된 사용자만 조회
                query = query.filter(User.email.like("deleted_%"))
            elif not include_deleted:
                # 삭제된 사용자 제외 (기본값)
                query = query.filter(~User.email.like("deleted_%"))

            # 검색 조건 적용
            if search_params:
                if search_params.email:
                    query = query.filter(User.email.ilike(f"%{search_params.email}%"))

                if search_params.nickname:
                    query = query.filter(
                        User.nickname.ilike(f"%{search_params.nickname}%")
                    )

                if search_params.role:
                    db_role = (
                        DBUserRole.USER
                        if search_params.role == UserRole.USER
                        else DBUserRole.ADMIN
                    )
                    query = query.filter(User.role == db_role)

                if search_params.is_active is not None:
                    query = query.filter(User.is_active == search_params.is_active)

                if search_params.is_email_verified is not None:
                    query = query.filter(
                        User.is_email_verified == search_params.is_email_verified
                    )

                if search_params.preferred_region:
                    query = query.filter(
                        User.preferred_region.ilike(
                            f"%{search_params.preferred_region}%"
                        )
                    )

                if search_params.created_after:
                    query = query.filter(User.created_at >= search_params.created_after)

                if search_params.created_before:
                    query = query.filter(
                        User.created_at <= search_params.created_before
                    )

            # 총 개수 계산
            total = query.count()

            # 페이징 적용
            offset = (page - 1) * size
            users = (
                query.order_by(desc(User.created_at)).offset(offset).limit(size).all()
            )

            user_responses = [UserResponse.model_validate(user) for user in users]

            # 총 페이지 수 계산
            total_pages = math.ceil(total / size)

            return UserListResponse(
                users=user_responses,
                total=total,
                page=page,
                size=size,
                total_pages=total_pages,
            )

        except Exception as e:
            logger.error(f"사용자 목록 조회 실패: {e}")
            raise

    def get_user_statistics(self) -> UserStats:
        """사용자 통계 조회"""
        try:
            # 간단한 개별 쿼리로 안정성 확보 (복잡한 CASE 문 대신)
            # 탈퇴한 사용자 제외 (deleted_로 시작하는 이메일)
            total_users = (
                self.db.query(User).filter(~User.email.like("deleted_%")).count()
            )
            active_users = (
                self.db.query(User)
                .filter(User.is_active == True, ~User.email.like("deleted_%"))
                .count()
            )
            verified_users = (
                self.db.query(User)
                .filter(User.is_email_verified == True, ~User.email.like("deleted_%"))
                .count()
            )
            admin_users = (
                self.db.query(User)
                .filter(User.role == DBUserRole.ADMIN, ~User.email.like("deleted_%"))
                .count()
            )

            # 최근 30일 가입자
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_registrations = (
                self.db.query(User)
                .filter(
                    User.created_at >= thirty_days_ago, ~User.email.like("deleted_%")
                )
                .count()
            )

            # 최근 7일 로그인 사용자 (NULL 값 제외)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_logins = (
                self.db.query(User)
                .filter(
                    User.last_login.isnot(None),
                    User.last_login >= seven_days_ago,
                    ~User.email.like("deleted_%"),
                )
                .count()
            )
            
            # 삭제된 사용자 수 (deleted_로 시작하는 이메일)
            deleted_users = (
                self.db.query(User).filter(User.email.like("deleted_%")).count()
            )

            return UserStats(
                total_users=total_users,
                active_users=active_users,
                verified_users=verified_users,
                admin_users=admin_users,
                recent_registrations=recent_registrations,
                recent_logins=recent_logins,
                deleted_users=deleted_users,
            )

        except Exception as e:
            logger.error(f"사용자 통계 조회 실패: {e}")
            self.db.rollback()
            raise

    def update_user(self, user_id: str, user_update: UserUpdate) -> User | None:
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

    def reset_user_password(
        self, user_id: str, new_password: str = "123456789a"
    ) -> bool:
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

    def search_users_by_keyword(self, keyword: str, limit: int = 20) -> list[User]:
        """키워드로 사용자 검색 (이메일, 닉네임)"""
        try:
            return (
                self.db.query(User)
                .filter(
                    or_(
                        User.email.ilike(f"%{keyword}%"),
                        User.nickname.ilike(f"%{keyword}%"),
                    )
                )
                .limit(limit)
                .all()
            )

        except Exception as e:
            logger.error(f"사용자 검색 실패 (키워드: {keyword}): {e}")
            raise

    def get_users_by_region(self, region: str) -> list[User]:
        """지역별 사용자 조회"""
        try:
            return (
                self.db.query(User)
                .filter(User.preferred_region.ilike(f"%{region}%"))
                .all()
            )

        except Exception as e:
            logger.error(f"지역별 사용자 조회 실패 (지역: {region}): {e}")
            raise

    def hard_delete_user(self, user_id: str) -> bool:
        """
        탈퇴 회원(이메일이 deleted_로 시작) 하드 삭제 (DB에서 완전 삭제)
        """
        logger.info(f"하드 삭제 시작: user_id={user_id}")
        
        try:
            # 사용자 조회
            user = self.get_user_by_id(user_id)
            if not user:
                logger.error(f"사용자를 찾을 수 없음: {user_id}")
                return False

            # deleted_로 시작하는 이메일만 하드 삭제 허용
            if not user.email or not user.email.startswith("deleted_"):
                logger.error(f"탈퇴 회원이 아님: {user.email}")
                raise ValueError("탈퇴 회원만 영구 삭제할 수 있습니다.")

            # 새로운 트랜잭션 시작
            logger.info("새로운 트랜잭션 시작")
            
            # 1. 먼저 사용자의 travel_plans 찾기
            travel_plan_ids = []
            try:
                result = self.db.execute(
                    text("SELECT plan_id FROM travel_plans WHERE user_id = :user_id"),
                    {"user_id": str(user_id)}
                )
                travel_plan_ids = [str(row[0]) for row in result]
                logger.info(f"사용자의 travel_plans 찾음: {len(travel_plan_ids)}개")
                if travel_plan_ids:
                    logger.debug(f"plan_ids: {travel_plan_ids[:3]}...")  # 처음 3개만 로그
            except Exception as e:
                logger.error(f"travel_plans 조회 중 오류: {e}")
                self.db.rollback()
                raise
            
            # 2. travel_plans와 관련된 테이블들 먼저 삭제
            if travel_plan_ids:
                for plan_id in travel_plan_ids:
                    # travel_plans를 참조하는 테이블들 먼저 삭제
                    # travel_routes가 가장 중요한 테이블이므로 먼저 삭제
                    try:
                        # travel_routes 삭제
                        logger.debug(f"travel_routes 삭제 시도: plan_id={plan_id}")
                        result = self.db.execute(
                            text("DELETE FROM travel_routes WHERE travel_plan_id = :plan_id"),
                            {"plan_id": plan_id}
                        )
                        if result.rowcount > 0:
                            logger.info(f"travel_routes에서 {result.rowcount}개 레코드 삭제")
                        else:
                            logger.debug(f"travel_routes에 삭제할 데이터 없음")
                    except Exception as e:
                        logger.error(f"travel_routes 삭제 중 오류 (plan_id={plan_id}): {e}")
                        # 트랜잭션 상태 확인
                        try:
                            # 간단한 쿼리로 트랜잭션 상태 테스트
                            self.db.execute(text("SELECT 1"))
                        except Exception as test_e:
                            logger.error(f"트랜잭션 상태 오류: {test_e}")
                            self.db.rollback()
                            # 새로운 트랜잭션 시작
                            logger.info("트랜잭션 재시작")
                        raise
                    
                    # 다른 travel_plan 관련 테이블들 삭제
                    related_tables = [
                        ("travel_plan_destinations", "plan_id"),
                        ("travel_plan_collaborators", "plan_id"),
                        ("travel_plan_comments", "plan_id"),
                        ("travel_plan_shares", "plan_id"),
                        ("travel_plan_versions", "plan_id"),
                        ("reviews", "travel_plan_id"),
                    ]
                    
                    for table_name, column_name in related_tables:
                        try:
                            logger.debug(f"{table_name} 삭제 시도: {column_name}={plan_id}")
                            query = text(f"DELETE FROM {table_name} WHERE {column_name} = :plan_id")
                            result = self.db.execute(query, {"plan_id": plan_id})
                            if result.rowcount > 0:
                                logger.info(f"{table_name}에서 {result.rowcount}개 레코드 삭제")
                        except Exception as e:
                            logger.warning(f"{table_name} 삭제 중 오류: {e}")
                            # 치명적인 오류가 아니면 계속 진행
            
            # 3. 사용자와 직접 관련된 travel_plan 관련 데이터 삭제
            logger.info("사용자 관련 travel_plan 데이터 삭제 시작")
            user_related_deletes = [
                ("DELETE FROM travel_plan_collaborators WHERE user_id = :user_id OR invited_by = :user_id", "travel_plan_collaborators"),
                ("DELETE FROM travel_plan_comments WHERE user_id = :user_id", "travel_plan_comments"),
                ("DELETE FROM travel_plan_shares WHERE created_by = :user_id", "travel_plan_shares"),
                ("DELETE FROM travel_plan_versions WHERE created_by = :user_id", "travel_plan_versions"),
            ]
            
            for query_str, table_name in user_related_deletes:
                try:
                    logger.debug(f"{table_name} 삭제 시도")
                    result = self.db.execute(text(query_str), {"user_id": str(user_id)})
                    if result.rowcount > 0:
                        logger.info(f"{table_name}에서 {result.rowcount}개 레코드 삭제")
                except Exception as e:
                    logger.warning(f"{table_name} 삭제 중 오류: {e}")
            
            # 4. 여행 계획 테이블 삭제
            try:
                logger.info("travel_plans 삭제 시작")
                result = self.db.execute(
                    text("DELETE FROM travel_plans WHERE user_id = :user_id"),
                    {"user_id": str(user_id)}
                )
                if result.rowcount > 0:
                    logger.info(f"travel_plans에서 {result.rowcount}개 레코드 삭제 완료")
            except Exception as e:
                logger.error(f"travel_plans 삭제 중 오류: {e}")
                self.db.rollback()
                raise
            
            # 5. reviews_recommend와 관련된 테이블 먼저 처리
            logger.info("reviews_recommend 관련 테이블 삭제 시작")
            try:
                # 먼저 review_likes 삭제 (reviews_recommend를 참조)
                result = self.db.execute(
                    text("DELETE FROM review_likes WHERE review_id IN (SELECT id FROM reviews_recommend WHERE user_id = :user_id)"),
                    {"user_id": str(user_id)}
                )
                if result.rowcount > 0:
                    logger.info(f"review_likes에서 {result.rowcount}개 레코드 삭제")
            except Exception as e:
                logger.warning(f"review_likes 삭제 중 오류: {e}")
            
            # 6. 기타 NO ACTION 제약이 있는 테이블들 (순서 중요)
            logger.info("기타 테이블 삭제 시작")
            other_tables = [
                # 외래키 참조가 없는 테이블부터 삭제
                "fcm_notification_logs",
                "notifications",
                "user_notification_settings",
                "user_activity_logs",
                "destination_ratings",
                "favorite_places",
                "likes_recommend",
                "reviews_recommend",  # review_likes를 먼저 삭제했으므로 이제 안전
                "travel_course_likes",
                "travel_course_saves",
                "chat_messages",
                "reviews",  # user_id로 추가 삭제
                # CASCADE로 자동 삭제되는 테이블들도 명시적으로 처리
                "user_tokens",
                "user_sessions",
                "user_preferences",
            ]
            
            for table_name in other_tables:
                try:
                    # 테이블 존재 여부 확인
                    check_query = text(f"SELECT 1 FROM information_schema.tables WHERE table_name = :table_name")
                    table_exists = self.db.execute(check_query, {"table_name": table_name}).scalar()
                    
                    if table_exists:
                        logger.debug(f"{table_name} 삭제 시도")
                        query = text(f"DELETE FROM {table_name} WHERE user_id = :user_id")
                        result = self.db.execute(query, {"user_id": str(user_id)})
                        if result.rowcount > 0:
                            logger.info(f"{table_name}에서 {result.rowcount}개 레코드 삭제")
                        else:
                            logger.debug(f"{table_name}에 삭제할 데이터 없음")
                except Exception as e:
                    logger.warning(f"{table_name} 삭제 중 오류: {e}")
                    # 테이블이 없거나 권한이 없는 경우 무시하고 계속
            
            # 7. 최종적으로 사용자 삭제
            try:
                logger.info("최종 사용자 삭제 시작")
                # SQLAlchemy ORM 대신 직접 SQL 사용하여 더 명확하게 삭제
                result = self.db.execute(
                    text("DELETE FROM users WHERE user_id = :user_id"),
                    {"user_id": str(user_id)}
                )
                
                if result.rowcount > 0:
                    logger.info(f"users 테이블에서 사용자 삭제 완료")
                    # 모든 작업이 성공하면 커밋
                    self.db.commit()
                    logger.info(f"트랜잭션 커밋 완료: 탈퇴 회원 하드 삭제 성공 (user_id={user_id})")
                    return True
                else:
                    logger.error(f"사용자 삭제 실패 - users 테이블에서 사용자를 찾을 수 없음: {user_id}")
                    self.db.rollback()
                    return False
                    
            except Exception as e:
                logger.error(f"사용자 삭제 중 오류: {e}")
                
                # 어떤 테이블에 데이터가 남아있는지 확인
                remaining_tables = []
                check_tables = [
                    ("travel_plans", "user_id = :user_id"),
                    ("travel_routes", "travel_plan_id IN (SELECT plan_id FROM travel_plans WHERE user_id = :user_id)"),
                    ("reviews", "user_id = :user_id"),
                    ("chat_messages", "user_id = :user_id"),
                    ("user_activity_logs", "user_id = :user_id"),
                ]
                
                for table_name, condition in check_tables:
                    try:
                        query = text(f"SELECT COUNT(*) FROM {table_name} WHERE {condition}")
                        result = self.db.execute(query, {"user_id": str(user_id)}).scalar()
                        if result and result > 0:
                            remaining_tables.append(f"{table_name}({result})")
                    except:
                        pass
                
                if remaining_tables:
                    logger.error(f"다음 테이블에 데이터가 남아있음: {', '.join(remaining_tables)}")
                
                self.db.rollback()
                raise

        except Exception as e:
            logger.error(f"탈퇴 회원 하드 삭제 실패 (ID: {user_id}): {e}", exc_info=True)
            self.db.rollback()
            logger.info("트랜잭션 롤백 완료")
            raise


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """UserService 인스턴스 반환"""
    return UserService(db)
