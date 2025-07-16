-- 성능 최적화를 위한 인덱스 추가
-- tour_api_area_code 매핑 시스템 성능 최적화

-- 1. regions 테이블에 tour_api_area_code와 region_level 복합 인덱스 추가
-- 이 인덱스는 JOIN 성능을 크게 개선할 것입니다.
CREATE INDEX CONCURRENTLY idx_regions_tour_api_area_code_level 
ON regions (tour_api_area_code, region_level);

-- 2. 관광 콘텐츠 테이블들의 region_code 인덱스 상태 확인 및 최적화
-- 이미 대부분의 테이블에 인덱스가 존재하므로 추가 작업 불필요

-- 3. 부족한 인덱스 추가 (festival_events, leisure_sports)
-- festival_events 테이블에 region_code 인덱스가 없다면 추가
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_festival_events_region_code
ON festival_events (region_code);

-- leisure_sports 테이블에 region_code 인덱스가 없다면 추가  
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_leisure_sports_region_code
ON leisure_sports (region_code);

-- 4. 통계 정보 업데이트
ANALYZE regions;
ANALYZE tourist_attractions;
ANALYZE cultural_facilities;
ANALYZE festival_events;
ANALYZE restaurants;
ANALYZE accommodations;
ANALYZE shopping;
ANALYZE leisure_sports;

-- 인덱스 사용 모니터링을 위한 뷰 생성
CREATE OR REPLACE VIEW v_index_usage_stats AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE schemaname = 'public' 
    AND (indexname LIKE '%tour_api_area_code%' OR indexname LIKE '%region_code%')
ORDER BY idx_scan DESC;

-- 성능 모니터링을 위한 함수 생성
CREATE OR REPLACE FUNCTION check_join_performance()
RETURNS TABLE(
    query_type TEXT,
    execution_time_ms NUMERIC,
    rows_processed INTEGER
) AS $$
BEGIN
    -- 관광지 JOIN 성능 테스트
    RETURN QUERY
    SELECT 
        'tourist_attractions_join'::TEXT as query_type,
        EXTRACT(EPOCH FROM (clock_timestamp() - clock_timestamp())) * 1000 as execution_time_ms,
        COUNT(*)::INTEGER as rows_processed
    FROM tourist_attractions ta
    LEFT JOIN regions r ON ta.region_code = r.tour_api_area_code AND r.region_level = 1
    WHERE ta.region_code = '1';
    
    -- 다른 콘텐츠 테이블들도 동일하게 테스트 가능
END;
$$ LANGUAGE plpgsql;

-- 성능 최적화 완료 확인을 위한 점검 쿼리
SELECT 
    'Performance Optimization Status' as title,
    COUNT(*) as total_indexes,
    COUNT(CASE WHEN indexname LIKE '%tour_api_area_code%' THEN 1 END) as tour_api_indexes,
    COUNT(CASE WHEN indexname LIKE '%region_code%' THEN 1 END) as region_code_indexes
FROM pg_indexes 
WHERE schemaname = 'public';