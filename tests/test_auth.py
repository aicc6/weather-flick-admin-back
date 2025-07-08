"""
Authentication 관련 테스트
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Admin, AdminStatus
from app.auth.utils import get_password_hash


class TestAuth:
    """인증 관련 테스트"""
    
    def test_login_success(self, client: TestClient, db_session: Session):
        """정상적인 로그인 테스트"""
        # 테스트 사용자 생성
        test_password = "TestPassword123!"
        admin = Admin(
            email="test@admin.com",
            name="Test Admin",
            password_hash=get_password_hash(test_password),
            status=AdminStatus.ACTIVE
        )
        db_session.add(admin)
        db_session.commit()
        
        # 로그인 요청
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@admin.com",
                "password": test_password
            }
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert "admin" in data
        assert "token" in data
        assert data["admin"]["email"] == "test@admin.com"
        assert data["token"]["access_token"] is not None
    
    def test_login_invalid_password(self, client: TestClient, db_session: Session):
        """잘못된 비밀번호로 로그인 시도"""
        # 테스트 사용자 생성
        admin = Admin(
            email="test@admin.com",
            name="Test Admin",
            password_hash=get_password_hash("CorrectPassword123!"),
            status=AdminStatus.ACTIVE
        )
        db_session.add(admin)
        db_session.commit()
        
        # 잘못된 비밀번호로 로그인 시도
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@admin.com",
                "password": "WrongPassword123!"
            }
        )
        
        # 검증
        assert response.status_code == 401
        assert "이메일 또는 비밀번호가 올바르지 않습니다" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client: TestClient):
        """존재하지 않는 사용자로 로그인 시도"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@admin.com",
                "password": "Password123!"
            }
        )
        
        # 검증
        assert response.status_code == 401
        assert "이메일 또는 비밀번호가 올바르지 않습니다" in response.json()["detail"]
    
    def test_login_inactive_user(self, client: TestClient, db_session: Session):
        """비활성화된 사용자로 로그인 시도"""
        # 비활성 사용자 생성
        test_password = "TestPassword123!"
        admin = Admin(
            email="inactive@admin.com",
            name="Inactive Admin",
            password_hash=get_password_hash(test_password),
            status=AdminStatus.INACTIVE
        )
        db_session.add(admin)
        db_session.commit()
        
        # 로그인 시도
        response = client.post(
            "/api/auth/login",
            json={
                "email": "inactive@admin.com",
                "password": test_password
            }
        )
        
        # 검증
        assert response.status_code == 403
        assert "비활성화된 계정입니다" in response.json()["detail"]
    
    def test_get_current_user_profile(self, client: TestClient, db_session: Session):
        """현재 사용자 프로필 조회 테스트"""
        # 테스트 사용자 생성 및 로그인
        test_password = "TestPassword123!"
        admin = Admin(
            email="profile@admin.com",
            name="Profile Admin",
            password_hash=get_password_hash(test_password),
            status=AdminStatus.ACTIVE
        )
        db_session.add(admin)
        db_session.commit()
        
        # 로그인하여 토큰 획득
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "profile@admin.com",
                "password": test_password
            }
        )
        token = login_response.json()["token"]["access_token"]
        
        # 프로필 조회
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "profile@admin.com"
        assert data["name"] == "Profile Admin"
    
    def test_get_current_user_profile_unauthorized(self, client: TestClient):
        """인증 없이 프로필 조회 시도"""
        response = client.get("/api/auth/me")
        
        # 검증
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"
    
    def test_logout(self, client: TestClient):
        """로그아웃 테스트"""
        response = client.post("/api/auth/logout")
        
        # 검증
        assert response.status_code == 200
        assert response.json()["message"] == "로그아웃되었습니다"
    
    def test_oauth2_token_endpoint(self, client: TestClient, db_session: Session):
        """OAuth2 호환 토큰 엔드포인트 테스트 (Swagger UI용)"""
        # 테스트 사용자 생성
        test_password = "TestPassword123!"
        admin = Admin(
            email="oauth@admin.com",
            name="OAuth Admin",
            password_hash=get_password_hash(test_password),
            status=AdminStatus.ACTIVE
        )
        db_session.add(admin)
        db_session.commit()
        
        # OAuth2 형식으로 로그인
        response = client.post(
            "/api/auth/token",
            data={
                "username": "oauth@admin.com",
                "password": test_password
            }
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"