from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_admin
from ..database import get_db
from ..services.data_quality_service import (
    DataQualityAnalyzer,
    calculate_and_update_quality_scores,
)

router = APIRouter(prefix="/data-quality", tags=["Data Quality Management"])


# 데이터 품질 개요 조회 API
@router.get("/overview")
def get_data_quality_overview(
    db: Session = Depends(get_db), current_admin=Depends(get_current_admin)
):
    """
    전체 데이터 품질 현황을 조회하는 API
    """
    try:
        # 테이블별 품질 점수 통계
        tables = [
            "destinations",
            "restaurants",
            "accommodations",
        ]
        table_stats = {}

        for table in tables:
            # 테이블별 기본 통계 쿼리
            if table == "destinations":
                stats_query = text(
                    """
                    SELECT 
                        COUNT(*) as total_count,
                        COUNT(CASE WHEN data_quality_score IS NOT NULL THEN 1 END) as scored_count,
                        AVG(data_quality_score) as avg_score,
                        MIN(data_quality_score) as min_score,
                        MAX(data_quality_score) as max_score,
                        COUNT(CASE WHEN data_quality_score >= 90 THEN 1 END) as grade_a,
                        COUNT(CASE WHEN data_quality_score >= 80 AND data_quality_score < 90 THEN 1 END) as grade_b,
                        COUNT(CASE WHEN data_quality_score >= 70 AND data_quality_score < 80 THEN 1 END) as grade_c,
                        COUNT(CASE WHEN data_quality_score >= 60 AND data_quality_score < 70 THEN 1 END) as grade_d,
                        COUNT(CASE WHEN data_quality_score < 60 THEN 1 END) as grade_f
                    FROM destinations
                """
                )
            else:
                stats_query = text(
                    f"""
                    SELECT 
                        COUNT(*) as total_count,
                        COUNT(CASE WHEN data_quality_score IS NOT NULL THEN 1 END) as scored_count,
                        AVG(data_quality_score) as avg_score,
                        MIN(data_quality_score) as min_score,
                        MAX(data_quality_score) as max_score,
                        COUNT(CASE WHEN data_quality_score >= 90 THEN 1 END) as grade_a,
                        COUNT(CASE WHEN data_quality_score >= 80 AND data_quality_score < 90 THEN 1 END) as grade_b,
                        COUNT(CASE WHEN data_quality_score >= 70 AND data_quality_score < 80 THEN 1 END) as grade_c,
                        COUNT(CASE WHEN data_quality_score >= 60 AND data_quality_score < 70 THEN 1 END) as grade_d,
                        COUNT(CASE WHEN data_quality_score < 60 THEN 1 END) as grade_f
                    FROM {table}
                """
                )

            try:
                result = db.execute(stats_query).fetchone()

                table_stats[table] = {
                    "total_count": result.total_count,
                    "scored_count": result.scored_count,
                    "coverage_percent": (
                        round((result.scored_count / result.total_count) * 100, 2)
                        if result.total_count > 0
                        else 0
                    ),
                    "average_score": round(float(result.avg_score or 0), 2),
                    "score_range": {
                        "min": round(float(result.min_score or 0), 2),
                        "max": round(float(result.max_score or 0), 2),
                    },
                    "grade_distribution": {
                        "A": result.grade_a,
                        "B": result.grade_b,
                        "C": result.grade_c,
                        "D": result.grade_d,
                        "F": result.grade_f,
                    },
                }
            except Exception:
                # 테이블이 존재하지 않는 경우 기본값 설정
                table_stats[table] = {
                    "total_count": 0,
                    "scored_count": 0,
                    "coverage_percent": 0,
                    "average_score": 0,
                    "score_range": {"min": 0, "max": 0},
                    "grade_distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0},
                }

        # 전체 통계 계산
        total_records = sum(stats["total_count"] for stats in table_stats.values())
        total_scored = sum(stats["scored_count"] for stats in table_stats.values())

        if total_scored > 0:
            weighted_avg_score = (
                sum(
                    stats["average_score"] * stats["scored_count"]
                    for stats in table_stats.values()
                )
                / total_scored
            )
        else:
            weighted_avg_score = 0

        # 전체 등급 분포
        total_grade_distribution = {
            "A": sum(
                stats["grade_distribution"]["A"] for stats in table_stats.values()
            ),
            "B": sum(
                stats["grade_distribution"]["B"] for stats in table_stats.values()
            ),
            "C": sum(
                stats["grade_distribution"]["C"] for stats in table_stats.values()
            ),
            "D": sum(
                stats["grade_distribution"]["D"] for stats in table_stats.values()
            ),
            "F": sum(
                stats["grade_distribution"]["F"] for stats in table_stats.values()
            ),
        }

        # 품질 이슈 요약
        quality_issues = []

        for table_name, stats in table_stats.items():
            if stats["coverage_percent"] < 50:
                quality_issues.append(
                    f"{table_name}: 품질 점수 미산정 비율이 높음 ({100-stats['coverage_percent']:.1f}%)"
                )

            if stats["average_score"] < 70:
                quality_issues.append(
                    f"{table_name}: 평균 품질 점수가 낮음 ({stats['average_score']:.1f}점)"
                )

            if stats["grade_distribution"]["F"] > stats["scored_count"] * 0.2:
                quality_issues.append(
                    f"{table_name}: F등급 데이터 비율이 높음 ({stats['grade_distribution']['F']}건)"
                )

        return {
            "summary": {
                "total_records": total_records,
                "scored_records": total_scored,
                "coverage_percent": (
                    round((total_scored / total_records) * 100, 2)
                    if total_records > 0
                    else 0
                ),
                "overall_average_score": round(weighted_avg_score, 2),
                "overall_grade": _get_quality_grade(weighted_avg_score),
            },
            "by_table": table_stats,
            "overall_grade_distribution": total_grade_distribution,
            "quality_issues": quality_issues,
            "last_updated": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"데이터 품질 개요 조회 실패: {str(e)}"
        )


# 특정 테이블의 품질 점수 계산 실행 API
@router.post("/calculate/{table_name}")
def calculate_quality_scores(
    table_name: str,
    limit: int = Query(100, ge=1, le=1000, description="처리할 레코드 수"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    특정 테이블의 데이터 품질 점수를 계산하고 업데이트하는 API
    """
    valid_tables = [
        "destinations",
        "restaurants",
        "accommodations",
    ]

    if table_name not in valid_tables:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 테이블입니다. 사용 가능한 테이블: {', '.join(valid_tables)}",
        )

    try:
        result = calculate_and_update_quality_scores(db, table_name, limit)

        if result["success"]:
            return {
                "success": True,
                "message": f"{table_name} 테이블의 품질 점수 계산이 완료되었습니다.",
                "statistics": result,
                "processed_at": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(
                status_code=500, detail=f"품질 점수 계산 실패: {result['error']}"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"품질 점수 계산 중 오류 발생: {str(e)}"
        )


# 모든 테이블의 품질 점수 계산 (배치 처리)
@router.post("/calculate-all")
def calculate_all_quality_scores(
    limit_per_table: int = Query(
        100, ge=1, le=500, description="테이블당 처리할 레코드 수"
    ),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    모든 테이블의 데이터 품질 점수를 배치로 계산하는 API
    """
    try:
        tables = [
            "destinations",
                "restaurants",
            "accommodations",
        ]
        results = {}
        total_processed = 0

        for table_name in tables:
            try:
                result = calculate_and_update_quality_scores(
                    db, table_name, limit_per_table
                )
                results[table_name] = result

                if result["success"]:
                    total_processed += result["processed_count"]

            except Exception as e:
                results[table_name] = {
                    "success": False,
                    "error": str(e),
                    "processed_count": 0,
                }

        # 성공한 테이블 수 계산
        successful_tables = sum(1 for result in results.values() if result["success"])

        return {
            "success": True,
            "message": f"전체 품질 점수 계산 완료: {successful_tables}/{len(tables)} 테이블 성공",
            "total_processed_records": total_processed,
            "results_by_table": results,
            "processed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"배치 품질 점수 계산 실패: {str(e)}"
        )


# 품질 점수 기준으로 데이터 조회 API
@router.get("/records/{table_name}")
def get_records_by_quality(
    table_name: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
    min_score: float | None = Query(
        None, ge=0, le=100, description="최소 품질 점수"
    ),
    max_score: float | None = Query(
        None, ge=0, le=100, description="최대 품질 점수"
    ),
    grade: str | None = Query(
        None, regex="^[ABCDF]$", description="품질 등급 (A, B, C, D, F)"
    ),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    sort_by: str = Query("score", description="정렬 기준 (score, name, updated_at)"),
    sort_order: str = Query("desc", description="정렬 순서 (asc, desc)"),
):
    """
    품질 점수 기준으로 레코드를 조회하는 API
    """
    valid_tables = [
        "destinations",
        "restaurants",
        "accommodations",
    ]

    if table_name not in valid_tables:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 테이블입니다. 사용 가능한 테이블: {', '.join(valid_tables)}",
        )

    try:
        # 기본 쿼리 구성
        if table_name == "destinations":
            base_query = """
                SELECT destination_id as id, name, province, region, 
                       data_quality_score, updated_at
                FROM destinations
                WHERE data_quality_score IS NOT NULL
            """
            count_query = "SELECT COUNT(*) as total FROM destinations WHERE data_quality_score IS NOT NULL"
        else:
            name_field = {
                "restaurants": "restaurant_name",
                "accommodations": "name",
            }.get(table_name, "name")

            base_query = f"""
                SELECT content_id as id, {name_field} as name, region_code,
                       data_quality_score, updated_at
                FROM {table_name}
                WHERE data_quality_score IS NOT NULL
            """
            count_query = f"SELECT COUNT(*) as total FROM {table_name} WHERE data_quality_score IS NOT NULL"

        # 필터 조건 추가
        filter_conditions = []
        params = {}

        if min_score is not None:
            filter_conditions.append("data_quality_score >= :min_score")
            params["min_score"] = min_score

        if max_score is not None:
            filter_conditions.append("data_quality_score <= :max_score")
            params["max_score"] = max_score

        if grade:
            score_ranges = {
                "A": (90, 100),
                "B": (80, 89.99),
                "C": (70, 79.99),
                "D": (60, 69.99),
                "F": (0, 59.99),
            }
            min_range, max_range = score_ranges[grade]
            filter_conditions.append(
                "data_quality_score >= :grade_min AND data_quality_score <= :grade_max"
            )
            params["grade_min"] = min_range
            params["grade_max"] = max_range

        # 필터 조건을 쿼리에 추가
        if filter_conditions:
            filter_sql = " AND " + " AND ".join(filter_conditions)
            base_query += filter_sql
            count_query += filter_sql

        # 정렬 조건 추가
        sort_columns = {
            "score": "data_quality_score",
            "name": name_field if table_name != "destinations" else "name",
            "updated_at": "updated_at",
        }

        sort_column = sort_columns.get(sort_by, "data_quality_score")
        sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
        order_sql = f" ORDER BY {sort_column} {sort_direction}"

        # 페이징 추가
        offset = (page - 1) * page_size
        limit_sql = f" LIMIT {page_size} OFFSET {offset}"

        final_query = base_query + order_sql + limit_sql

        # 쿼리 실행
        records_result = db.execute(text(final_query), params)
        records = records_result.fetchall()

        count_result = db.execute(text(count_query), params)
        total_count = count_result.fetchone().total

        # 결과 포맷팅
        formatted_records = []
        for record in records:
            formatted_record = {
                "id": str(record.id),
                "name": record.name,
                "data_quality_score": round(float(record.data_quality_score), 2),
                "quality_grade": _get_quality_grade(record.data_quality_score),
                "updated_at": (
                    record.updated_at.isoformat() if record.updated_at else None
                ),
            }

            # 테이블별 추가 필드
            if table_name == "destinations":
                formatted_record.update(
                    {"province": record.province, "region": record.region}
                )
            else:
                formatted_record["region_code"] = record.region_code

            formatted_records.append(formatted_record)

        return {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size,
            "items": formatted_records,
            "table_name": table_name,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"품질 기준 레코드 조회 실패: {str(e)}"
        )


# 특정 레코드의 품질 상세 분석 API
@router.get("/analyze/{table_name}/{record_id}")
def analyze_record_quality(
    table_name: str,
    record_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    특정 레코드의 품질을 상세 분석하는 API
    """
    valid_tables = [
        "destinations",
        "restaurants",
        "accommodations",
    ]

    if table_name not in valid_tables:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 테이블입니다. 사용 가능한 테이블: {', '.join(valid_tables)}",
        )

    try:
        # 레코드 조회
        if table_name == "destinations":
            query = text(
                """
                SELECT destination_id, name, province, region, category,
                       latitude, longitude, amenities, image_url, rating,
                       created_at, updated_at
                FROM destinations 
                WHERE destination_id = :record_id
            """
            )
        else:
            # 각 테이블에 맞는 쿼리 (모든 필드 포함)
            if table_name == "restaurants":
                query = text(
                    """
                    SELECT content_id, restaurant_name, region_code, cuisine_type,
                           address, latitude, longitude, tel, homepage, operating_hours,
                           created_at, updated_at, last_sync_at
                    FROM restaurants 
                    WHERE content_id = :record_id
                """
                )
            elif table_name == "accommodations":
                query = text(
                    """
                    SELECT destination_id as content_id, name, province as region_code, 
                           category as type, NULL as address, latitude, longitude,
                           CASE WHEN amenities ? 'tel' THEN amenities->>'tel' ELSE NULL END as phone,
                           rating, amenities, created_at, NULL as updated_at, NULL as last_sync_at
                    FROM destinations 
                    WHERE category = '숙박' AND destination_id::text = :record_id
                """
                )

        result = db.execute(query, {"record_id": record_id})
        record = result.fetchone()

        if not record:
            raise HTTPException(status_code=404, detail="레코드를 찾을 수 없습니다.")

        # 레코드를 딕셔너리로 변환
        record_dict = dict(record._mapping)

        # 품질 분석 실행
        analyzer = DataQualityAnalyzer(db)
        quality_analysis = analyzer.calculate_destination_quality_score(record_dict)

        # 결과에 레코드 정보 추가
        quality_analysis["record_info"] = {
            "table_name": table_name,
            "record_id": record_id,
            "record_data": record_dict,
        }

        return quality_analysis

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"품질 분석 실패: {str(e)}")


# 품질 개선 제안 API
@router.get("/improvement-suggestions")
def get_quality_improvement_suggestions(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
    limit: int = Query(50, ge=1, le=200, description="분석할 레코드 수"),
):
    """
    전체적인 데이터 품질 개선 제안을 제공하는 API
    """
    try:
        suggestions = []

        # 각 테이블별 낮은 품질 레코드 분석
        tables = [
            "destinations",
                "restaurants",
            "accommodations",
        ]

        for table in tables:
            try:
                # F등급 데이터 개수 확인
                if table == "destinations":
                    low_quality_query = text(
                        """
                        SELECT COUNT(*) as count
                        FROM destinations 
                        WHERE data_quality_score < 60
                    """
                    )
                else:
                    low_quality_query = text(
                        f"""
                        SELECT COUNT(*) as count
                        FROM {table} 
                        WHERE data_quality_score < 60
                    """
                    )

                result = db.execute(low_quality_query)
                low_quality_count = result.fetchone().count

                if low_quality_count > 0:
                    suggestions.append(
                        {
                            "type": "low_quality_data",
                            "table": table,
                            "issue": f"{table}에 F등급 데이터가 {low_quality_count}건 있습니다",
                            "suggestion": "데이터 보완 또는 삭제를 검토하세요",
                            "priority": "high" if low_quality_count > 100 else "medium",
                        }
                    )

                # 미채점 데이터 확인
                if table == "destinations":
                    unscored_query = text(
                        """
                        SELECT COUNT(*) as count
                        FROM destinations 
                        WHERE data_quality_score IS NULL
                    """
                    )
                else:
                    unscored_query = text(
                        f"""
                        SELECT COUNT(*) as count
                        FROM {table} 
                        WHERE data_quality_score IS NULL
                    """
                    )

                result = db.execute(unscored_query)
                unscored_count = result.fetchone().count

                if unscored_count > 0:
                    suggestions.append(
                        {
                            "type": "unscored_data",
                            "table": table,
                            "issue": f"{table}에 품질 점수가 미산정된 데이터가 {unscored_count}건 있습니다",
                            "suggestion": "품질 점수 계산을 실행하세요",
                            "priority": "medium",
                        }
                    )

            except Exception:
                continue  # 테이블이 없으면 건너뛰기

        # 전반적인 개선 제안
        general_suggestions = [
            {
                "type": "general",
                "issue": "데이터 수집 프로세스 개선",
                "suggestion": "API 수집 시 필수 필드 검증을 강화하세요",
                "priority": "medium",
            },
            {
                "type": "general",
                "issue": "정기적인 품질 모니터링",
                "suggestion": "주기적으로 품질 점수를 재계산하고 모니터링하세요",
                "priority": "low",
            },
        ]

        suggestions.extend(general_suggestions)

        # 우선순위별 정렬
        priority_order = {"high": 3, "medium": 2, "low": 1}
        suggestions.sort(
            key=lambda x: priority_order.get(x["priority"], 0), reverse=True
        )

        return {
            "total_suggestions": len(suggestions),
            "suggestions": suggestions,
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"개선 제안 생성 실패: {str(e)}")


def _get_quality_grade(score: float) -> str:
    """품질 점수를 등급으로 변환하는 헬퍼 함수"""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"
