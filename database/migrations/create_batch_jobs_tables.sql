-- 먼저 관리자 테이블의 ID 컬럼 확인
-- admins 테이블이 admin_id를 사용하는지 id를 사용하는지 체크 필요

-- 배치 작업 테이블 생성 (admin_batch_jobs로 명명하여 기존 테이블과 구분)
CREATE TABLE IF NOT EXISTS admin_batch_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    parameters JSONB DEFAULT '{}',
    progress FLOAT DEFAULT 0.0,
    current_step VARCHAR(255),
    total_steps INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES admins(admin_id),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    result_summary JSONB,
    stopped_by INTEGER REFERENCES admins(admin_id),
    priority INTEGER DEFAULT 5,
    notification_email VARCHAR(255)
);

-- 배치 작업 상세 로그 테이블 생성 (admin_batch_job_details로 명명)
CREATE TABLE IF NOT EXISTS admin_batch_job_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES admin_batch_jobs(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    details JSONB
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_admin_batch_jobs_job_type ON admin_batch_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_admin_batch_jobs_status ON admin_batch_jobs(status);
CREATE INDEX IF NOT EXISTS idx_admin_batch_jobs_type_status ON admin_batch_jobs(job_type, status);
CREATE INDEX IF NOT EXISTS idx_admin_batch_jobs_created_at ON admin_batch_jobs(created_at);

CREATE INDEX IF NOT EXISTS idx_admin_batch_job_details_job_id ON admin_batch_job_details(job_id);
CREATE INDEX IF NOT EXISTS idx_admin_batch_job_details_level ON admin_batch_job_details(level);
CREATE INDEX IF NOT EXISTS idx_admin_batch_job_details_job_level ON admin_batch_job_details(job_id, level);
CREATE INDEX IF NOT EXISTS idx_admin_batch_job_details_timestamp ON admin_batch_job_details(timestamp);

-- 코멘트 추가
COMMENT ON TABLE admin_batch_jobs IS '관리자 페이지용 배치 작업 실행 이력';
COMMENT ON COLUMN admin_batch_jobs.job_type IS '작업 유형 (KTO_DATA_COLLECTION, WEATHER_DATA_COLLECTION 등)';
COMMENT ON COLUMN admin_batch_jobs.status IS '작업 상태 (PENDING, RUNNING, COMPLETED, FAILED, STOPPED)';
COMMENT ON COLUMN admin_batch_jobs.parameters IS '작업 실행 매개변수';
COMMENT ON COLUMN admin_batch_jobs.progress IS '작업 진행률 (0-100)';
COMMENT ON COLUMN admin_batch_jobs.priority IS '작업 우선순위 (1-10, 10이 가장 높음)';

COMMENT ON TABLE admin_batch_job_details IS '관리자 페이지용 배치 작업 상세 로그';
COMMENT ON COLUMN admin_batch_job_details.level IS '로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)';