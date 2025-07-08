"""
Pytest configuration and fixtures for Weather Flick Admin Backend tests.
"""

import os
import sys
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import get_db
from app.models import Base
from main import app

# 테스트용 데이터베이스 URL (SQLite in-memory)
TEST_DATABASE_URL = "sqlite:///:memory:"

# 테스트용 엔진 생성
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# JSONB를 JSON으로 변환하는 이벤트 리스너 추가
@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite에서 JSONB 타입을 처리하기 위한 설정"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# JSONB 타입을 JSON으로 변환
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

# 테스트용 세션 팩토리
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    각 테스트 함수마다 새로운 데이터베이스 세션을 생성합니다.
    테스트가 끝나면 데이터베이스를 초기화합니다.
    """
    # 테이블 생성
    Base.metadata.create_all(bind=test_engine)
    
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # 테이블 삭제
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    테스트용 FastAPI 클라이언트를 생성합니다.
    데이터베이스 의존성을 테스트용 세션으로 오버라이드합니다.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # 의존성 오버라이드 제거
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """테스트용 사용자 데이터"""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "name": "Test User"
    }


@pytest.fixture
def auth_headers(client: TestClient, test_user_data: dict) -> dict:
    """
    인증된 사용자의 헤더를 반환합니다.
    먼저 사용자를 생성하고 로그인하여 토큰을 받습니다.
    """
    # 사용자 생성
    response = client.post("/api/users/", json=test_user_data)
    assert response.status_code == 201
    
    # 로그인
    login_data = {
        "username": test_user_data["email"],
        "password": test_user_data["password"]
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == 200
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_settings(monkeypatch):
    """테스트용 설정을 모킹합니다."""
    # 테스트용 설정 오버라이드
    monkeypatch.setattr(settings, "database_url", TEST_DATABASE_URL)
    monkeypatch.setattr(settings, "secret_key", "test_secret_key_for_testing_only")
    monkeypatch.setattr(settings, "environment", "testing")
    monkeypatch.setattr(settings, "debug", True)
    
    return settings