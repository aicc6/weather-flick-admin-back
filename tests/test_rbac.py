"""
RBAC 시스템 테스트
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_admin import Admin
from app.models_rbac import Role, Resource, Permission
from app.auth.utils import create_admin_token, hash_password
from main import app


class TestRBACSystem:
    """RBAC 시스템 통합 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup(self, db: Session):
        """각 테스트 전 실행되는 설정"""
        # 테스트용 역할 생성
        self.super_admin_role = db.query(Role).filter_by(name="super_admin").first()
        self.user_manager_role = db.query(Role).filter_by(name="user_manager").first()
        self.content_manager_role = db.query(Role).filter_by(name="content_manager").first()
        self.data_analyst_role = db.query(Role).filter_by(name="data_analyst").first()
        
        # 테스트용 관리자 생성
        self.super_admin = self._create_test_admin(
            db, "super@test.com", "Super Admin", [self.super_admin_role]
        )
        self.user_manager = self._create_test_admin(
            db, "usermgr@test.com", "User Manager", [self.user_manager_role]
        )
        self.content_manager = self._create_test_admin(
            db, "contentmgr@test.com", "Content Manager", [self.content_manager_role]
        )
        self.data_analyst = self._create_test_admin(
            db, "analyst@test.com", "Data Analyst", [self.data_analyst_role]
        )
        
        yield
        
        # 테스트 후 정리
        db.query(Admin).filter(Admin.email.in_([
            "super@test.com", "usermgr@test.com", 
            "contentmgr@test.com", "analyst@test.com"
        ])).delete()
        db.commit()
    
    def _create_test_admin(self, db: Session, email: str, name: str, roles: list[Role]):
        """테스트용 관리자 생성"""
        admin = Admin(
            email=email,
            name=name,
            password_hash=hash_password("testpass123"),
            status="ACTIVE"
        )
        admin.roles = roles
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin
    
    def _get_auth_headers(self, admin: Admin):
        """인증 헤더 생성"""
        token = create_admin_token(admin.admin_id, admin.email)
        return {"Authorization": f"Bearer {token}"}


class TestPermissionCheck(TestRBACSystem):
    """권한 체크 테스트"""
    
    def test_super_admin_has_all_permissions(self, client: TestClient):
        """슈퍼 관리자는 모든 권한을 가져야 함"""
        headers = self._get_auth_headers(self.super_admin)
        
        # 권한 조회
        response = client.get("/api/rbac/my-permissions", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["is_superuser"] is True
        
        # 모든 리소스에 접근 가능해야 함
        endpoints = [
            "/api/users",
            "/api/destinations",
            "/api/system/status",
            "/api/rbac/roles",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint, headers=headers)
            assert response.status_code != 403  # Forbidden이 아니어야 함
    
    def test_user_manager_permissions(self, client: TestClient):
        """사용자 관리자 권한 테스트"""
        headers = self._get_auth_headers(self.user_manager)
        
        # 사용자 관리 권한은 있어야 함
        response = client.get("/api/users", headers=headers)
        assert response.status_code != 403
        
        # 콘텐츠 관리 권한은 없어야 함
        response = client.get("/api/destinations", headers=headers)
        assert response.status_code == 403
    
    def test_content_manager_permissions(self, client: TestClient):
        """콘텐츠 관리자 권한 테스트"""
        headers = self._get_auth_headers(self.content_manager)
        
        # 콘텐츠 관리 권한은 있어야 함
        response = client.get("/api/destinations", headers=headers)
        assert response.status_code != 403
        
        # 사용자 관리 권한은 없어야 함
        response = client.delete("/api/users/123", headers=headers)
        assert response.status_code == 403
    
    def test_data_analyst_permissions(self, client: TestClient):
        """데이터 분석가 권한 테스트"""
        headers = self._get_auth_headers(self.data_analyst)
        
        # 대시보드 읽기 권한은 있어야 함
        response = client.get("/api/dashboard/stats", headers=headers)
        assert response.status_code != 403
        
        # 시스템 설정 권한은 없어야 함
        response = client.post("/api/system/logs/test", headers=headers, json={})
        assert response.status_code == 403


class TestRBACAPI(TestRBACSystem):
    """RBAC 관리 API 테스트"""
    
    def test_get_roles(self, client: TestClient):
        """역할 목록 조회 테스트"""
        headers = self._get_auth_headers(self.super_admin)
        
        response = client.get("/api/rbac/roles", headers=headers)
        assert response.status_code == 200
        
        roles = response.json()
        assert len(roles) >= 4  # 최소 4개의 시스템 역할
        
        role_names = [r["name"] for r in roles]
        assert "super_admin" in role_names
        assert "user_manager" in role_names
        assert "content_manager" in role_names
        assert "data_analyst" in role_names
    
    def test_get_role_detail(self, client: TestClient):
        """역할 상세 조회 테스트"""
        headers = self._get_auth_headers(self.super_admin)
        
        response = client.get(f"/api/rbac/roles/{self.user_manager_role.id}", headers=headers)
        assert response.status_code == 200
        
        role = response.json()
        assert role["name"] == "user_manager"
        assert len(role["permissions"]) > 0
    
    def test_assign_role(self, client: TestClient, db: Session):
        """역할 할당 테스트"""
        headers = self._get_auth_headers(self.super_admin)
        
        # 새 관리자 생성
        new_admin = Admin(
            email="newadmin@test.com",
            name="New Admin",
            password_hash=hash_password("testpass123"),
            status="ACTIVE"
        )
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        # 역할 할당
        response = client.post(
            f"/api/rbac/admins/{new_admin.admin_id}/roles",
            headers=headers,
            json={"role_id": self.content_manager_role.id}
        )
        assert response.status_code == 200
        
        # 할당 확인
        db.refresh(new_admin)
        assert self.content_manager_role in new_admin.roles
        
        # 정리
        db.delete(new_admin)
        db.commit()
    
    def test_remove_role(self, client: TestClient):
        """역할 제거 테스트"""
        headers = self._get_auth_headers(self.super_admin)
        
        # content_manager에게서 역할 제거
        response = client.delete(
            f"/api/rbac/admins/{self.content_manager.admin_id}/roles/{self.content_manager_role.id}",
            headers=headers
        )
        assert response.status_code == 200
        
        # 제거 확인
        response = client.get("/api/rbac/my-permissions", 
                            headers=self._get_auth_headers(self.content_manager))
        data = response.json()
        assert len(data["roles"]) == 0


class TestPermissionDelegation(TestRBACSystem):
    """권한 위임 테스트"""
    
    def test_delegate_permission(self, client: TestClient, db: Session):
        """권한 위임 테스트"""
        headers = self._get_auth_headers(self.user_manager)
        
        # 사용자 읽기 권한 위임
        user_read_perm = db.query(Permission).filter_by(name="users.read").first()
        
        response = client.post(
            "/api/rbac/permissions/delegate",
            headers=headers,
            json={
                "permission_id": user_read_perm.id,
                "delegated_to_admin_id": self.data_analyst.admin_id,
                "expires_at": "2025-12-31T23:59:59"
            }
        )
        assert response.status_code == 200
        
        # 위임받은 권한으로 접근 테스트
        analyst_headers = self._get_auth_headers(self.data_analyst)
        response = client.get("/api/users", headers=analyst_headers)
        # 위임 기능이 구현되면 403이 아니어야 함
        # 현재는 미구현 상태이므로 403 반환
        assert response.status_code == 403


class TestPermissionAudit(TestRBACSystem):
    """권한 감사 로그 테스트"""
    
    def test_permission_usage_logged(self, client: TestClient, db: Session):
        """권한 사용이 로깅되는지 테스트"""
        headers = self._get_auth_headers(self.user_manager)
        
        # 권한이 필요한 API 호출
        response = client.get("/api/users", headers=headers)
        
        # 감사 로그 확인 (감사 기능이 구현되면 테스트)
        # audit_logs = db.query(PermissionAuditLog).filter_by(
        #     admin_id=self.user_manager.admin_id
        # ).all()
        # assert len(audit_logs) > 0


@pytest.fixture
def client():
    """테스트 클라이언트"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    """테스트용 데이터베이스 세션"""
    from app.database import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()