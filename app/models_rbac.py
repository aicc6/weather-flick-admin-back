"""RBAC (Role-Based Access Control) 모델"""

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, Integer, 
    String, Table, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

# 관리자-역할 다대다 관계 테이블
admin_roles = Table(
    'admin_roles',
    Base.metadata,
    Column('admin_id', Integer, ForeignKey('admins.admin_id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('assigned_at', DateTime, default=func.now()),
    Column('assigned_by', Integer),
    Index('idx_admin_roles_admin_id', 'admin_id'),
    Index('idx_admin_roles_role_id', 'role_id'),
    extend_existing=True
)

# 역할-권한 다대다 관계 테이블
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Column('granted_at', DateTime, default=func.now()),
    Column('granted_by', Integer),
    Index('idx_role_permissions_role_id', 'role_id'),
    Index('idx_role_permissions_permission_id', 'permission_id'),
    extend_existing=True
)


class Role(Base):
    """역할 정의"""
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    is_system = Column(Boolean, default=False)  # 시스템 정의 역할 여부
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    permissions = relationship(
        "Permission", 
        secondary=role_permissions, 
        back_populates="roles",
        lazy="joined"
    )
    admins = relationship(
        "Admin",
        secondary=admin_roles,
        back_populates="roles",
        lazy="joined"
    )
    
    def has_permission(self, permission_name: str) -> bool:
        """특정 권한 보유 여부 확인"""
        return any(p.name == permission_name for p in self.permissions)
    
    def add_permission(self, permission: 'Permission'):
        """권한 추가"""
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def remove_permission(self, permission: 'Permission'):
        """권한 제거"""
        if permission in self.permissions:
            self.permissions.remove(permission)


class Resource(Base):
    """보호된 리소스 정의"""
    __tablename__ = 'resources'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    module = Column(String(50))  # 모듈 그루핑 (user_management, content_management 등)
    created_at = Column(DateTime, default=func.now())
    
    # 관계 설정
    permissions = relationship("Permission", back_populates="resource", cascade="all, delete-orphan")


class Permission(Base):
    """권한 정의"""
    __tablename__ = 'permissions'
    __table_args__ = (
        UniqueConstraint('resource_id', 'action', name='uq_resource_action'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # 예: users.read, users.write
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)
    action = Column(String(50), nullable=False)  # read, write, delete, approve 등
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # 관계 설정
    resource = relationship("Resource", back_populates="permissions")
    roles = relationship(
        "Role", 
        secondary=role_permissions, 
        back_populates="permissions"
    )
    delegations_from = relationship(
        "PermissionDelegation",
        foreign_keys="PermissionDelegation.permission_id",
        back_populates="permission",
        cascade="all, delete-orphan"
    )


class PermissionDelegation(Base):
    """권한 위임 정보"""
    __tablename__ = 'permission_delegations'
    
    id = Column(Integer, primary_key=True, index=True)
    delegator_id = Column(Integer, ForeignKey('admins.admin_id'), nullable=False)
    delegatee_id = Column(Integer, ForeignKey('admins.admin_id'), nullable=False)
    permission_id = Column(Integer, ForeignKey('permissions.id'), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    reason = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    revoked_at = Column(DateTime)
    
    # 관계 설정
    permission = relationship("Permission", back_populates="delegations_from")
    
    # 인덱스
    __table_args__ = (
        Index('idx_delegation_delegator', 'delegator_id'),
        Index('idx_delegation_delegatee', 'delegatee_id'),
        Index('idx_delegation_dates', 'start_date', 'end_date'),
        Index('idx_delegation_active', 'is_active')
    )


class PermissionAuditLog(Base):
    """권한 사용 감사 로그"""
    __tablename__ = 'permission_audit_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey('admins.admin_id'))
    permission_id = Column(Integer, ForeignKey('permissions.id'))
    action = Column(String(50), nullable=False)  # 수행한 작업
    resource_type = Column(String(50))  # 리소스 타입
    resource_id = Column(String(100))  # 대상 리소스 ID
    success = Column(Boolean, default=True)  # 성공 여부
    failure_reason = Column(Text)  # 실패 사유
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # 인덱스
    __table_args__ = (
        Index('idx_audit_admin', 'admin_id'),
        Index('idx_audit_permission', 'permission_id'),
        Index('idx_audit_created', 'created_at'),
        Index('idx_audit_success', 'success')
    )


def extend_admin_model(Admin):
    """Admin 모델에 RBAC 관계 추가"""
    Admin.roles = relationship(
        "Role", 
        secondary=admin_roles, 
        back_populates="admins",
        lazy="joined"
    )