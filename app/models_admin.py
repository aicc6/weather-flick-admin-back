"""관리자 모델"""
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Integer, String
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models_rbac import admin_roles


class AdminStatus(enum.Enum):
    """관리자 계정 상태"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"


class Admin(Base):
    """
    관리자 계정 테이블
    사용처: weather-flick-admin-back
    설명: 관리자 계정 정보 및 권한 관리
    """
    __tablename__ = "admins"

    admin_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String)
    phone = Column(String)
    status = Column(Enum(AdminStatus), default=AdminStatus.ACTIVE)
    is_superuser = Column(Boolean, default=False)  # 슈퍼관리자 여부
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    
    # RBAC 관계
    roles = relationship(
        "Role", 
        secondary=admin_roles, 
        back_populates="admins",
        lazy="joined"
    )
    
    def has_permission(self, permission_name: str) -> bool:
        """권한 보유 여부 확인"""
        # 슈퍼유저는 모든 권한 보유
        if self.is_superuser:
            return True
        
        # RBAC 관계가 설정되면 roles를 통해 확인
        if hasattr(self, 'roles'):
            for role in self.roles:
                if role.has_permission(permission_name):
                    return True
        
        return False
    
    def get_all_permissions(self) -> set:
        """모든 권한 목록 반환"""
        if self.is_superuser:
            # 슈퍼유저는 모든 권한 반환
            from app.models_rbac import Permission
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                permissions = db.query(Permission).all()
                return {p.name for p in permissions}
            finally:
                db.close()
        
        # RBAC 관계가 설정되면 roles를 통해 수집
        permissions = set()
        if hasattr(self, 'roles'):
            for role in self.roles:
                permissions.update(p.name for p in role.permissions)
        
        return permissions
    
    def get_roles_display(self) -> str:
        """역할 표시 문자열 반환"""
        if self.is_superuser:
            return "최고 관리자"
        
        if hasattr(self, 'roles') and self.roles:
            return ", ".join(role.display_name for role in self.roles)
        
        return "일반 관리자"