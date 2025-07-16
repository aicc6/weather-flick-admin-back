-- RBAC (Role-Based Access Control) 테이블 생성
-- 작성일: 2025-07-15
-- 설명: 관리자 권한 시스템을 위한 테이블 구조

-- 1. 역할(Roles) 테이블
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,  -- 시스템 기본 역할 여부
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 리소스(Resources) 테이블
CREATE TABLE IF NOT EXISTS resources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    module VARCHAR(50),  -- 모듈 그룹핑 (user_management, content_management 등)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 권한(Permissions) 테이블
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,  -- 형식: resource.action (예: users.read)
    resource_id INTEGER REFERENCES resources(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,  -- read, write, delete, export 등
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 역할-권한 매핑 테이블
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id)
);

-- 5. 관리자-역할 매핑 테이블
CREATE TABLE IF NOT EXISTS admin_roles (
    admin_id INTEGER REFERENCES admins(admin_id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by INTEGER REFERENCES admins(admin_id),
    PRIMARY KEY (admin_id, role_id)
);

-- 6. 권한 위임 테이블 (선택적 - 임시 권한 부여)
CREATE TABLE IF NOT EXISTS permission_delegations (
    id SERIAL PRIMARY KEY,
    from_admin_id INTEGER REFERENCES admins(admin_id) ON DELETE CASCADE,
    to_admin_id INTEGER REFERENCES admins(admin_id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    revoked_by INTEGER REFERENCES admins(admin_id)
);

-- 7. 권한 사용 로그 테이블 (감사 목적)
CREATE TABLE IF NOT EXISTS permission_audit_logs (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES admins(admin_id),
    permission_id INTEGER REFERENCES permissions(id),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    success BOOLEAN DEFAULT TRUE,
    failure_reason TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_permissions_resource_action ON permissions(resource_id, action);
CREATE INDEX IF NOT EXISTS idx_delegations_valid ON permission_delegations(to_admin_id, valid_from, valid_until);
CREATE INDEX IF NOT EXISTS idx_audit_admin_date ON permission_audit_logs(admin_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_permission_date ON permission_audit_logs(permission_id, created_at);
CREATE INDEX IF NOT EXISTS idx_admin_roles_admin ON admin_roles(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_roles_role ON admin_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission ON role_permissions(permission_id);

-- 트리거: updated_at 자동 업데이트
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 뷰: 관리자별 권한 조회
CREATE OR REPLACE VIEW admin_permissions_view AS
SELECT 
    a.admin_id,
    a.email,
    a.name as admin_name,
    r.name as role_name,
    r.display_name as role_display_name,
    p.name as permission_name,
    p.action,
    res.name as resource_name,
    res.module
FROM admins a
JOIN admin_roles ar ON a.admin_id = ar.admin_id
JOIN roles r ON ar.role_id = r.id
JOIN role_permissions rp ON r.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id
JOIN resources res ON p.resource_id = res.id
WHERE a.status = 'ACTIVE'
ORDER BY a.admin_id, r.name, res.module, res.name, p.action;

-- 함수: 관리자 권한 체크
CREATE OR REPLACE FUNCTION check_admin_permission(
    p_admin_id INTEGER,
    p_permission_name VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    has_permission BOOLEAN;
BEGIN
    -- 슈퍼유저는 모든 권한 보유
    SELECT is_superuser INTO has_permission
    FROM admins 
    WHERE admin_id = p_admin_id AND status = 'ACTIVE';
    
    IF has_permission THEN
        RETURN TRUE;
    END IF;
    
    -- 일반 권한 체크
    SELECT EXISTS (
        SELECT 1
        FROM admin_permissions_view
        WHERE admin_id = p_admin_id 
        AND permission_name = p_permission_name
    ) INTO has_permission;
    
    -- 위임된 권한 체크
    IF NOT has_permission THEN
        SELECT EXISTS (
            SELECT 1
            FROM permission_delegations pd
            JOIN permissions p ON pd.permission_id = p.id
            WHERE pd.to_admin_id = p_admin_id
            AND p.name = p_permission_name
            AND pd.valid_from <= CURRENT_TIMESTAMP
            AND pd.valid_until >= CURRENT_TIMESTAMP
            AND pd.revoked_at IS NULL
        ) INTO has_permission;
    END IF;
    
    RETURN has_permission;
END;
$$ LANGUAGE plpgsql;

-- 코멘트 추가
COMMENT ON TABLE roles IS '관리자 역할 정의';
COMMENT ON TABLE resources IS '보호된 리소스 정의';
COMMENT ON TABLE permissions IS '세부 권한 정의';
COMMENT ON TABLE role_permissions IS '역할-권한 매핑';
COMMENT ON TABLE admin_roles IS '관리자-역할 매핑';
COMMENT ON TABLE permission_delegations IS '임시 권한 위임';
COMMENT ON TABLE permission_audit_logs IS '권한 사용 감사 로그';

COMMENT ON COLUMN roles.is_system IS '시스템 기본 역할 여부 (삭제 불가)';
COMMENT ON COLUMN permissions.name IS '권한명 형식: resource.action (예: users.read)';
COMMENT ON COLUMN resources.module IS '리소스 그룹 (user_management, content_management, system_settings, analytics)';