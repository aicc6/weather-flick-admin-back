-- is_superuser 컬럼을 admins 테이블에 추가
ALTER TABLE admins 
ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE;

-- 기존 admin@weatherflick.com 계정을 슈퍼관리자로 설정
UPDATE admins 
SET is_superuser = TRUE 
WHERE email = 'admin@weatherflick.com';

-- 컬럼에 인덱스 추가 (성능 향상)
CREATE INDEX IF NOT EXISTS idx_admins_is_superuser ON admins(is_superuser);

-- 변경사항 확인
SELECT admin_id, email, name, status, is_superuser 
FROM admins 
WHERE is_superuser = TRUE;