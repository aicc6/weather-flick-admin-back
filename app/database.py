from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# PostgreSQL 데이터베이스 URL
SQLALCHEMY_DATABASE_URL = settings.database_url

# 엔진 생성 - 안정성 개선
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,  # 관리자용 연결 풀 크기
    max_overflow=15,  # 추가 연결 수 제한
    pool_timeout=60,  # 연결 대기 시간
    pool_pre_ping=True,  # 연결 상태 확인 활성화
    pool_recycle=1800,  # 30분마다 연결 재생성
    echo=settings.debug,  # 디버그 모드에서 SQL 로그 출력
    # 추가 안정성 옵션
    connect_args={
        "connect_timeout": 30,  # 연결 타임아웃
        "application_name": "weather_flick_admin",  # 애플리케이션 식별
        "options": "-c statement_timeout=30000",  # 쿼리 타임아웃 (30초)
    },
    # 연결 검증 강화
    pool_reset_on_return='commit',  # 연결 반환 시 커밋 상태로 리셋
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스
Base = declarative_base()

# 데이터베이스 의존성 - 안정성 개선
def get_db():
    db = SessionLocal()
    try:
        # 연결 상태 확인
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        db.rollback()
        print(f"Admin Database error: {e}")
        raise
    finally:
        db.close()


# 헬스체크용 데이터베이스 연결 함수
def check_db_connection():
    """데이터베이스 연결 상태 확인"""
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1")).fetchone()
        db.close()
        return True, "Admin database connection successful"
    except Exception as e:
        return False, f"Admin database connection failed: {str(e)}"


# 연결 풀 상태 확인
def get_pool_status():
    """연결 풀 상태 정보 반환"""
    pool = engine.pool
    pool_info = {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }
    
    # SQLAlchemy 2.0+ 호환성: invalid() 메서드가 제거됨
    try:
        pool_info["invalid"] = pool.invalid()
    except AttributeError:
        # 최신 버전에서는 invalid 정보를 다른 방식으로 확인
        pool_info["invalid"] = 0
    
    return pool_info
