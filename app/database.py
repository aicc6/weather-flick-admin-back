"""
v3 스키마 데이터베이스 연결 설정
weather-flick-admin-back를 v3 스키마에 연동
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# v3 스키마 임포트

# v3 데이터베이스 엔진 (기존 settings.database_url 사용)
engine = create_engine(
    settings.database_url, pool_pre_ping=True, pool_recycle=300, echo=settings.debug
)

# v3 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# v3 데이터베이스 의존성
def get_db():
    """v3 데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
