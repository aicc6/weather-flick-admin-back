-- 008_create_admin_activity_logs.sql
-- 관리자 활동 로그 테이블 생성

-- 관리자 활동 로그 테이블
CREATE TABLE IF NOT EXISTS admin_activity_logs (
    log_id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES admins(admin_id),
    action VARCHAR(100) NOT NULL,
    description TEXT,
    severity VARCHAR(20) DEFAULT 'INFO',
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    user_agent TEXT,
    ip_address VARCHAR(45),
    request_data JSONB,
    response_data JSONB,
    error_message TEXT,
    status_code INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX idx_admin_activity_logs_admin_id ON admin_activity_logs(admin_id);
CREATE INDEX idx_admin_activity_logs_action ON admin_activity_logs(action);
CREATE INDEX idx_admin_activity_logs_created_at ON admin_activity_logs(created_at DESC);
CREATE INDEX idx_admin_activity_logs_severity ON admin_activity_logs(severity);
CREATE INDEX idx_admin_activity_logs_resource ON admin_activity_logs(resource_type, resource_id);

-- 코멘트 추가
COMMENT ON TABLE admin_activity_logs IS '관리자 활동 로그';
COMMENT ON COLUMN admin_activity_logs.log_id IS '로그 ID';
COMMENT ON COLUMN admin_activity_logs.admin_id IS '관리자 ID';
COMMENT ON COLUMN admin_activity_logs.action IS '수행한 작업';
COMMENT ON COLUMN admin_activity_logs.description IS '작업 설명';
COMMENT ON COLUMN admin_activity_logs.severity IS '중요도 (INFO, WARNING, ERROR, CRITICAL)';
COMMENT ON COLUMN admin_activity_logs.resource_type IS '대상 리소스 타입';
COMMENT ON COLUMN admin_activity_logs.resource_id IS '대상 리소스 ID';
COMMENT ON COLUMN admin_activity_logs.user_agent IS '사용자 에이전트';
COMMENT ON COLUMN admin_activity_logs.ip_address IS 'IP 주소';
COMMENT ON COLUMN admin_activity_logs.request_data IS '요청 데이터';
COMMENT ON COLUMN admin_activity_logs.response_data IS '응답 데이터';
COMMENT ON COLUMN admin_activity_logs.error_message IS '에러 메시지';
COMMENT ON COLUMN admin_activity_logs.status_code IS 'HTTP 상태 코드';
COMMENT ON COLUMN admin_activity_logs.created_at IS '생성 시간';