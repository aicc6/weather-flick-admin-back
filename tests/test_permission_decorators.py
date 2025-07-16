"""
권한 데코레이터 단위 테스트
"""
import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException

from app.auth.dependencies import require_permission, require_any_permission, require_all_permissions
from app.models_admin import Admin
from app.models_rbac import Role, Permission


class TestPermissionDecorators:
    """권한 데코레이터 테스트"""
    
    @pytest.fixture
    def mock_admin_with_permissions(self):
        """권한을 가진 관리자 모의 객체"""
        admin = Mock(spec=Admin)
        admin.admin_id = 1
        admin.email = "test@admin.com"
        admin.is_superuser = False
        
        # 권한 설정
        permission1 = Mock(spec=Permission)
        permission1.name = "users.read"
        
        permission2 = Mock(spec=Permission)
        permission2.name = "users.write"
        
        role = Mock(spec=Role)
        role.permissions = [permission1, permission2]
        
        admin.roles = [role]
        admin.has_permission = lambda perm: perm in ["users.read", "users.write"]
        
        return admin
    
    @pytest.fixture
    def mock_super_admin(self):
        """슈퍼 관리자 모의 객체"""
        admin = Mock(spec=Admin)
        admin.admin_id = 1
        admin.email = "super@admin.com"
        admin.is_superuser = True
        admin.has_permission = lambda perm: True  # 모든 권한 허용
        
        return admin
    
    @pytest.fixture
    def mock_admin_no_permissions(self):
        """권한이 없는 관리자 모의 객체"""
        admin = Mock(spec=Admin)
        admin.admin_id = 2
        admin.email = "limited@admin.com"
        admin.is_superuser = False
        admin.roles = []
        admin.has_permission = lambda perm: False
        
        return admin
    
    def test_require_permission_success(self, mock_admin_with_permissions):
        """require_permission - 권한이 있는 경우"""
        decorator = require_permission("users.read")
        
        @decorator
        async def test_endpoint(current_admin: Admin):
            return {"success": True}
        
        # 권한이 있으므로 정상 실행
        result = test_endpoint(current_admin=mock_admin_with_permissions)
        assert result == {"success": True}
    
    def test_require_permission_forbidden(self, mock_admin_no_permissions):
        """require_permission - 권한이 없는 경우"""
        decorator = require_permission("users.delete")
        
        @decorator
        async def test_endpoint(current_admin: Admin):
            return {"success": True}
        
        # 권한이 없으므로 예외 발생
        with pytest.raises(HTTPException) as exc_info:
            test_endpoint(current_admin=mock_admin_no_permissions)
        
        assert exc_info.value.status_code == 403
        assert "권한이 없습니다" in str(exc_info.value.detail)
    
    def test_require_permission_super_admin(self, mock_super_admin):
        """require_permission - 슈퍼 관리자는 모든 권한 허용"""
        decorator = require_permission("any.permission")
        
        @decorator
        async def test_endpoint(current_admin: Admin):
            return {"success": True}
        
        # 슈퍼 관리자는 항상 통과
        result = test_endpoint(current_admin=mock_super_admin)
        assert result == {"success": True}
    
    def test_require_any_permission_success(self, mock_admin_with_permissions):
        """require_any_permission - 하나 이상의 권한이 있는 경우"""
        decorator = require_any_permission(["users.delete", "users.write"])
        
        @decorator
        async def test_endpoint(current_admin: Admin):
            return {"success": True}
        
        # users.write 권한이 있으므로 통과
        result = test_endpoint(current_admin=mock_admin_with_permissions)
        assert result == {"success": True}
    
    def test_require_any_permission_forbidden(self, mock_admin_no_permissions):
        """require_any_permission - 모든 권한이 없는 경우"""
        decorator = require_any_permission(["users.delete", "system.configure"])
        
        @decorator
        async def test_endpoint(current_admin: Admin):
            return {"success": True}
        
        # 모든 권한이 없으므로 예외 발생
        with pytest.raises(HTTPException) as exc_info:
            test_endpoint(current_admin=mock_admin_no_permissions)
        
        assert exc_info.value.status_code == 403
    
    def test_require_all_permissions_success(self, mock_admin_with_permissions):
        """require_all_permissions - 모든 권한이 있는 경우"""
        decorator = require_all_permissions(["users.read", "users.write"])
        
        @decorator
        async def test_endpoint(current_admin: Admin):
            return {"success": True}
        
        # 두 권한 모두 있으므로 통과
        result = test_endpoint(current_admin=mock_admin_with_permissions)
        assert result == {"success": True}
    
    def test_require_all_permissions_forbidden(self, mock_admin_with_permissions):
        """require_all_permissions - 일부 권한만 있는 경우"""
        decorator = require_all_permissions(["users.read", "users.delete"])
        
        @decorator
        async def test_endpoint(current_admin: Admin):
            return {"success": True}
        
        # users.delete 권한이 없으므로 예외 발생
        with pytest.raises(HTTPException) as exc_info:
            test_endpoint(current_admin=mock_admin_with_permissions)
        
        assert exc_info.value.status_code == 403
    
    def test_decorator_with_db_parameter(self, mock_admin_with_permissions):
        """데코레이터가 db 파라미터와 함께 작동하는지 테스트"""
        decorator = require_permission("users.read")
        
        @decorator
        async def test_endpoint(db: Mock, current_admin: Admin):
            return {"db": db, "admin": current_admin.email}
        
        mock_db = Mock()
        result = test_endpoint(db=mock_db, current_admin=mock_admin_with_permissions)
        
        assert result["db"] == mock_db
        assert result["admin"] == "test@admin.com"
    
    def test_permission_audit_logging(self, mock_admin_with_permissions):
        """권한 사용 시 감사 로그 기록 테스트"""
        with patch('app.auth.dependencies.log_permission_usage') as mock_log:
            decorator = require_permission("users.read", log_usage=True)
            
            @decorator
            async def test_endpoint(current_admin: Admin, db: Mock = None):
                return {"success": True}
            
            mock_db = Mock()
            test_endpoint(current_admin=mock_admin_with_permissions, db=mock_db)
            
            # 로그 함수가 호출되었는지 확인
            mock_log.assert_called_once()
            args = mock_log.call_args[0]
            assert args[0] == mock_admin_with_permissions
            assert args[1] == "users.read"
            assert args[2] == mock_db