-- 지역 코드 매핑 문제 해결을 위한 마이그레이션
-- regions 테이블에 tour_api_area_code 컬럼 추가

-- 1. tour_api_area_code 컬럼 추가
ALTER TABLE regions ADD COLUMN tour_api_area_code VARCHAR(10);

-- 2. 기존 API 매핑 데이터를 새 컬럼으로 이전
UPDATE regions 
SET tour_api_area_code = CAST(api_mappings->'tour_api'->>'area_code' AS VARCHAR)
WHERE api_mappings->'tour_api'->>'area_code' IS NOT NULL;

-- 3. 표준 코드가 이미 있는 경우 직접 매핑
UPDATE regions 
SET tour_api_area_code = region_code 
WHERE region_code IN ('1', '2', '3', '4', '5', '6', '7', '8', '31', '32', '33', '34', '35', '36', '37', '38', '39');

-- 4. 인덱스 추가 (성능 향상)
CREATE INDEX idx_regions_tour_api_area_code ON regions(tour_api_area_code);

-- 5. 데이터 확인을 위한 조회
-- SELECT region_code, region_name, tour_api_area_code FROM regions WHERE tour_api_area_code IS NOT NULL ORDER BY tour_api_area_code;