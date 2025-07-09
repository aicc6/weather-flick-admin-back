import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_admin
from ..database import get_db

router = APIRouter(prefix="/duplicates", tags=["Duplicate Management"])


# 중복 목록 조회 API
@router.get("/")
def get_duplicates_list(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
    status: str | None = Query(
        "DETECTED", description="중복 상태 필터 (DETECTED, REVIEWING, MERGED, IGNORED)"
    ),
    method: str | None = Query(
        None, description="감지 방법 필터 (exact_name, geographical, similar_name)"
    ),
    similarity_min: float | None = Query(0.0, description="최소 유사도"),
    similarity_max: float | None = Query(1.0, description="최대 유사도"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    sort_by: str = Query(
        "detected_at", description="정렬 기준 (detected_at, similarity_score)"
    ),
    sort_order: str = Query("desc", description="정렬 순서 (asc, desc)"),
):
    """
    감지된 중복 목록을 조회하는 API

    관리자가 중복으로 감지된 여행지들을 확인하고 관리할 수 있습니다.
    """
    try:
        # 기본 쿼리 구성
        base_query = text(
            """
            SELECT 
                dd.id,
                dd.primary_destination_id,
                dd.duplicate_destination_id,
                dd.similarity_score,
                dd.merge_status,
                dd.merge_rules,
                dd.detected_at,
                dd.resolved_at,
                -- Primary destination 정보
                d1.name as primary_name,
                d1.province as primary_province,
                d1.region as primary_region,
                d1.latitude as primary_latitude,
                d1.longitude as primary_longitude,
                -- Duplicate destination 정보
                d2.name as duplicate_name,
                d2.province as duplicate_province,
                d2.region as duplicate_region,
                d2.latitude as duplicate_latitude,
                d2.longitude as duplicate_longitude
            FROM destination_duplicates dd
            LEFT JOIN destinations d1 ON dd.primary_destination_id = d1.destination_id
            LEFT JOIN destinations d2 ON dd.duplicate_destination_id = d2.destination_id
            WHERE 1=1
        """
        )

        # 동적 필터 조건 추가
        filter_conditions = []
        params = {}

        if status:
            filter_conditions.append("dd.merge_status = :status")
            params["status"] = status

        if method:
            filter_conditions.append("dd.merge_rules->>'detection_method' = :method")
            params["method"] = method

        if similarity_min is not None:
            filter_conditions.append("dd.similarity_score >= :similarity_min")
            params["similarity_min"] = similarity_min

        if similarity_max is not None:
            filter_conditions.append("dd.similarity_score <= :similarity_max")
            params["similarity_max"] = similarity_max

        # 필터 조건을 쿼리에 추가
        if filter_conditions:
            filter_sql = " AND " + " AND ".join(filter_conditions)
            base_query = text(str(base_query) + filter_sql)

        # 정렬 조건 추가
        sort_column = (
            "dd.detected_at" if sort_by == "detected_at" else "dd.similarity_score"
        )
        sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
        order_sql = f" ORDER BY {sort_column} {sort_direction}"

        # 페이징 조건 추가
        offset = (page - 1) * page_size
        limit_sql = f" LIMIT {page_size} OFFSET {offset}"

        final_query = text(str(base_query) + order_sql + limit_sql)

        # 전체 개수 조회
        count_query = text(
            """
            SELECT COUNT(*) as total
            FROM destination_duplicates dd
            WHERE 1=1
        """
        )

        if filter_conditions:
            count_query = text(
                str(count_query) + " AND " + " AND ".join(filter_conditions)
            )

        # 쿼리 실행
        result = db.execute(final_query, params)
        duplicates = result.fetchall()

        count_result = db.execute(count_query, params)
        total_count = count_result.fetchone().total

        # 결과 포맷팅
        formatted_duplicates = []
        for dup in duplicates:
            merge_rules = json.loads(dup.merge_rules) if dup.merge_rules else {}

            formatted_dup = {
                "id": str(dup.id),
                "similarity_score": float(dup.similarity_score),
                "merge_status": dup.merge_status,
                "detection_method": merge_rules.get("detection_method", "auto"),
                "detected_at": dup.detected_at.isoformat() if dup.detected_at else None,
                "resolved_at": dup.resolved_at.isoformat() if dup.resolved_at else None,
                "primary_destination": {
                    "id": str(dup.primary_destination_id),
                    "name": dup.primary_name,
                    "province": dup.primary_province,
                    "region": dup.primary_region,
                    "latitude": (
                        float(dup.primary_latitude) if dup.primary_latitude else None
                    ),
                    "longitude": (
                        float(dup.primary_longitude) if dup.primary_longitude else None
                    ),
                },
                "duplicate_destination": {
                    "id": str(dup.duplicate_destination_id),
                    "name": dup.duplicate_name,
                    "province": dup.duplicate_province,
                    "region": dup.duplicate_region,
                    "latitude": (
                        float(dup.duplicate_latitude)
                        if dup.duplicate_latitude
                        else None
                    ),
                    "longitude": (
                        float(dup.duplicate_longitude)
                        if dup.duplicate_longitude
                        else None
                    ),
                },
                "distance_meters": merge_rules.get("distance_meters"),
                "name_similarity": merge_rules.get("name_similarity"),
            }
            formatted_duplicates.append(formatted_dup)

        return {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size,
            "items": formatted_duplicates,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"중복 목록 조회 실패: {str(e)}")


# 중복 상세 조회 API
@router.get("/{duplicate_id}")
def get_duplicate_detail(
    duplicate_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    특정 중복의 상세 정보를 조회하는 API
    """
    try:
        query = text(
            """
            SELECT 
                dd.*,
                -- Primary destination 상세 정보
                d1.name as primary_name,
                d1.province as primary_province,
                d1.region as primary_region,
                d1.category as primary_category,
                d1.latitude as primary_latitude,
                d1.longitude as primary_longitude,
                d1.amenities as primary_amenities,
                d1.image_url as primary_image_url,
                d1.rating as primary_rating,
                d1.created_at as primary_created_at,
                -- Duplicate destination 상세 정보
                d2.name as duplicate_name,
                d2.province as duplicate_province,
                d2.region as duplicate_region,
                d2.category as duplicate_category,
                d2.latitude as duplicate_latitude,
                d2.longitude as duplicate_longitude,
                d2.amenities as duplicate_amenities,
                d2.image_url as duplicate_image_url,
                d2.rating as duplicate_rating,
                d2.created_at as duplicate_created_at
            FROM destination_duplicates dd
            LEFT JOIN destinations d1 ON dd.primary_destination_id = d1.destination_id
            LEFT JOIN destinations d2 ON dd.duplicate_destination_id = d2.destination_id
            WHERE dd.id = :duplicate_id
        """
        )

        result = db.execute(query, {"duplicate_id": duplicate_id})
        duplicate_data = result.fetchone()

        if not duplicate_data:
            raise HTTPException(
                status_code=404, detail="중복 데이터를 찾을 수 없습니다."
            )

        merge_rules = (
            json.loads(duplicate_data.merge_rules) if duplicate_data.merge_rules else {}
        )

        return {
            "id": str(duplicate_data.id),
            "similarity_score": float(duplicate_data.similarity_score),
            "merge_status": duplicate_data.merge_status,
            "detection_method": merge_rules.get("detection_method", "auto"),
            "detected_at": (
                duplicate_data.detected_at.isoformat()
                if duplicate_data.detected_at
                else None
            ),
            "resolved_at": (
                duplicate_data.resolved_at.isoformat()
                if duplicate_data.resolved_at
                else None
            ),
            "merge_rules": merge_rules,
            "primary_destination": {
                "id": str(duplicate_data.primary_destination_id),
                "name": duplicate_data.primary_name,
                "province": duplicate_data.primary_province,
                "region": duplicate_data.primary_region,
                "category": duplicate_data.primary_category,
                "latitude": (
                    float(duplicate_data.primary_latitude)
                    if duplicate_data.primary_latitude
                    else None
                ),
                "longitude": (
                    float(duplicate_data.primary_longitude)
                    if duplicate_data.primary_longitude
                    else None
                ),
                "amenities": duplicate_data.primary_amenities,
                "image_url": duplicate_data.primary_image_url,
                "rating": (
                    float(duplicate_data.primary_rating)
                    if duplicate_data.primary_rating
                    else None
                ),
                "created_at": (
                    duplicate_data.primary_created_at.isoformat()
                    if duplicate_data.primary_created_at
                    else None
                ),
            },
            "duplicate_destination": {
                "id": str(duplicate_data.duplicate_destination_id),
                "name": duplicate_data.duplicate_name,
                "province": duplicate_data.duplicate_province,
                "region": duplicate_data.duplicate_region,
                "category": duplicate_data.duplicate_category,
                "latitude": (
                    float(duplicate_data.duplicate_latitude)
                    if duplicate_data.duplicate_latitude
                    else None
                ),
                "longitude": (
                    float(duplicate_data.duplicate_longitude)
                    if duplicate_data.duplicate_longitude
                    else None
                ),
                "amenities": duplicate_data.duplicate_amenities,
                "image_url": duplicate_data.duplicate_image_url,
                "rating": (
                    float(duplicate_data.duplicate_rating)
                    if duplicate_data.duplicate_rating
                    else None
                ),
                "created_at": (
                    duplicate_data.duplicate_created_at.isoformat()
                    if duplicate_data.duplicate_created_at
                    else None
                ),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"중복 상세 조회 실패: {str(e)}")


# 중복 병합 API
@router.post("/{duplicate_id}/merge")
def merge_duplicate(
    duplicate_id: str,
    merge_strategy: dict[str, Any] = Body(..., description="병합 전략"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    중복된 여행지를 병합하는 API

    merge_strategy 예시:
    {
        "keep_primary": true,  // true: primary 유지, false: duplicate 유지
        "merge_fields": ["amenities", "rating", "image_url"],  // 병합할 필드들
        "admin_notes": "수동 병합 - 더 상세한 정보로 통합"
    }
    """
    try:
        # 중복 데이터 조회
        duplicate_query = text(
            """
            SELECT * FROM destination_duplicates 
            WHERE id = :duplicate_id AND merge_status = 'DETECTED'
        """
        )

        duplicate_result = db.execute(duplicate_query, {"duplicate_id": duplicate_id})
        duplicate_data = duplicate_result.fetchone()

        if not duplicate_data:
            raise HTTPException(
                status_code=404, detail="병합 가능한 중복 데이터를 찾을 수 없습니다."
            )

        keep_primary = merge_strategy.get("keep_primary", True)
        merge_fields = merge_strategy.get("merge_fields", [])
        admin_notes = merge_strategy.get("admin_notes", "")

        # 유지할 destination과 삭제할 destination 결정
        if keep_primary:
            keep_id = duplicate_data.primary_destination_id
            remove_id = duplicate_data.duplicate_destination_id
        else:
            keep_id = duplicate_data.duplicate_destination_id
            remove_id = duplicate_data.primary_destination_id

        # 병합 트랜잭션 시작
        try:
            # 1. 유지할 destination 조회
            keep_dest_query = text(
                "SELECT * FROM destinations WHERE destination_id = :dest_id"
            )
            keep_dest = db.execute(keep_dest_query, {"dest_id": keep_id}).fetchone()

            # 2. 제거할 destination 조회
            remove_dest_query = text(
                "SELECT * FROM destinations WHERE destination_id = :dest_id"
            )
            remove_dest = db.execute(
                remove_dest_query, {"dest_id": remove_id}
            ).fetchone()

            if not keep_dest or not remove_dest:
                raise HTTPException(
                    status_code=404, detail="병합할 여행지를 찾을 수 없습니다."
                )

            # 3. 지정된 필드들을 병합
            update_fields = {}

            for field in merge_fields:
                if hasattr(remove_dest, field):
                    remove_value = getattr(remove_dest, field)
                    keep_value = getattr(keep_dest, field)

                    # 필드별 병합 로직
                    if field == "amenities":
                        # JSONB 필드 병합
                        keep_amenities = keep_value or {}
                        remove_amenities = remove_value or {}
                        merged_amenities = {**keep_amenities, **remove_amenities}
                        update_fields["amenities"] = json.dumps(merged_amenities)
                    elif field == "rating":
                        # 평점은 더 높은 값 선택
                        if remove_value and (
                            not keep_value or remove_value > keep_value
                        ):
                            update_fields["rating"] = remove_value
                    elif field == "image_url":
                        # 이미지 URL은 비어있지 않은 값 선택
                        if remove_value and not keep_value:
                            update_fields["image_url"] = remove_value

            # 4. 유지할 destination 업데이트
            if update_fields:
                set_clauses = []
                update_params = {"dest_id": keep_id}

                for field, value in update_fields.items():
                    set_clauses.append(f"{field} = :{field}")
                    update_params[field] = value

                update_query = text(
                    f"""
                    UPDATE destinations 
                    SET {', '.join(set_clauses)}, updated_at = NOW()
                    WHERE destination_id = :dest_id
                """
                )

                db.execute(update_query, update_params)

            # 5. 관련 데이터 이전 (리뷰, 여행 계획 등)
            # 리뷰 이전
            review_update = text(
                """
                UPDATE reviews 
                SET destination_id = :keep_id
                WHERE destination_id = :remove_id
            """
            )
            db.execute(review_update, {"keep_id": keep_id, "remove_id": remove_id})

            # 여행 계획 목적지 이전 (테이블이 존재한다면)
            try:
                travel_update = text(
                    """
                    UPDATE travel_day_destinations 
                    SET destination_id = :keep_id
                    WHERE destination_id = :remove_id
                """
                )
                db.execute(travel_update, {"keep_id": keep_id, "remove_id": remove_id})
            except:
                pass  # 테이블이 없으면 무시

            # 6. 제거할 destination 삭제
            delete_dest = text(
                "DELETE FROM destinations WHERE destination_id = :dest_id"
            )
            db.execute(delete_dest, {"dest_id": remove_id})

            # 7. 중복 상태 업데이트
            merge_rules = (
                json.loads(duplicate_data.merge_rules)
                if duplicate_data.merge_rules
                else {}
            )
            merge_rules.update(
                {
                    "merged_by_admin": current_admin.admin_id,
                    "merge_strategy": merge_strategy,
                    "admin_notes": admin_notes,
                    "merged_at": datetime.now().isoformat(),
                    "kept_destination": str(keep_id),
                    "removed_destination": str(remove_id),
                }
            )

            update_duplicate = text(
                """
                UPDATE destination_duplicates 
                SET merge_status = 'MERGED',
                    resolved_at = NOW(),
                    merge_rules = :merge_rules
                WHERE id = :duplicate_id
            """
            )

            db.execute(
                update_duplicate,
                {"duplicate_id": duplicate_id, "merge_rules": json.dumps(merge_rules)},
            )

            # 8. 같은 destination과 관련된 다른 중복들도 처리
            related_duplicates = text(
                """
                UPDATE destination_duplicates 
                SET merge_status = 'MERGED',
                    resolved_at = NOW(),
                    merge_rules = jsonb_set(
                        COALESCE(merge_rules, '{}'::jsonb),
                        '{auto_resolved}',
                        '"true"'
                    )
                WHERE (primary_destination_id = :remove_id OR duplicate_destination_id = :remove_id)
                AND merge_status = 'DETECTED'
                AND id != :duplicate_id
            """
            )

            db.execute(
                related_duplicates,
                {"remove_id": remove_id, "duplicate_id": duplicate_id},
            )

            db.commit()

            return {
                "success": True,
                "message": "중복 병합이 완료되었습니다.",
                "kept_destination_id": str(keep_id),
                "removed_destination_id": str(remove_id),
                "merge_details": merge_rules,
            }

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"병합 처리 중 오류 발생: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"중복 병합 실패: {str(e)}")


# 중복 무시 API
@router.post("/{duplicate_id}/ignore")
def ignore_duplicate(
    duplicate_id: str,
    ignore_reason: dict[str, str] = Body(..., description="무시 사유"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    중복을 무시(거짓 양성)로 처리하는 API

    ignore_reason 예시:
    {
        "reason": "실제로는 다른 장소임",
        "admin_notes": "상세 주소가 다르고 실제 방문 확인 결과 별개 장소"
    }
    """
    try:
        # 중복 데이터 조회
        duplicate_query = text(
            """
            SELECT * FROM destination_duplicates 
            WHERE id = :duplicate_id AND merge_status = 'DETECTED'
        """
        )

        duplicate_result = db.execute(duplicate_query, {"duplicate_id": duplicate_id})
        duplicate_data = duplicate_result.fetchone()

        if not duplicate_data:
            raise HTTPException(
                status_code=404, detail="처리 가능한 중복 데이터를 찾을 수 없습니다."
            )

        # merge_rules 업데이트
        merge_rules = (
            json.loads(duplicate_data.merge_rules) if duplicate_data.merge_rules else {}
        )
        merge_rules.update(
            {
                "ignored_by_admin": current_admin.admin_id,
                "ignore_reason": ignore_reason.get("reason", ""),
                "admin_notes": ignore_reason.get("admin_notes", ""),
                "ignored_at": datetime.now().isoformat(),
            }
        )

        # 중복 상태 업데이트
        update_query = text(
            """
            UPDATE destination_duplicates 
            SET merge_status = 'IGNORED',
                resolved_at = NOW(),
                merge_rules = :merge_rules
            WHERE id = :duplicate_id
        """
        )

        db.execute(
            update_query,
            {"duplicate_id": duplicate_id, "merge_rules": json.dumps(merge_rules)},
        )

        db.commit()

        return {
            "success": True,
            "message": "중복이 무시 처리되었습니다.",
            "duplicate_id": duplicate_id,
            "ignore_details": merge_rules,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"중복 무시 처리 실패: {str(e)}")


# 중복 상태 통계 API
@router.get("/statistics/overview")
def get_duplicate_statistics(
    db: Session = Depends(get_db), current_admin=Depends(get_current_admin)
):
    """
    중복 감지 및 처리 통계를 조회하는 API
    """
    try:
        # 상태별 통계
        status_stats_query = text(
            """
            SELECT 
                merge_status,
                COUNT(*) as count,
                AVG(similarity_score) as avg_similarity,
                MIN(similarity_score) as min_similarity,
                MAX(similarity_score) as max_similarity
            FROM destination_duplicates
            GROUP BY merge_status
            ORDER BY count DESC
        """
        )

        status_results = db.execute(status_stats_query)
        status_stats = {}
        total_duplicates = 0

        for row in status_results:
            status_stats[row.merge_status] = {
                "count": row.count,
                "avg_similarity": round(float(row.avg_similarity), 3),
                "min_similarity": round(float(row.min_similarity), 3),
                "max_similarity": round(float(row.max_similarity), 3),
            }
            total_duplicates += row.count

        # 감지 방법별 통계
        method_stats_query = text(
            """
            SELECT 
                merge_rules->>'detection_method' as method,
                COUNT(*) as count,
                AVG(similarity_score) as avg_similarity
            FROM destination_duplicates
            WHERE merge_rules->>'detection_method' IS NOT NULL
            GROUP BY merge_rules->>'detection_method'
            ORDER BY count DESC
        """
        )

        method_results = db.execute(method_stats_query)
        method_stats = {}

        for row in method_results:
            method_stats[row.method] = {
                "count": row.count,
                "avg_similarity": round(float(row.avg_similarity), 3),
            }

        # 일별 감지 통계 (최근 30일)
        daily_stats_query = text(
            """
            SELECT 
                DATE(detected_at) as date,
                COUNT(*) as count
            FROM destination_duplicates
            WHERE detected_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(detected_at)
            ORDER BY date DESC
            LIMIT 30
        """
        )

        daily_results = db.execute(daily_stats_query)
        daily_stats = []

        for row in daily_results:
            daily_stats.append({"date": row.date.isoformat(), "count": row.count})

        # 처리 효율성 통계
        efficiency_query = text(
            """
            SELECT 
                COUNT(CASE WHEN merge_status = 'DETECTED' THEN 1 END) as pending_count,
                COUNT(CASE WHEN merge_status IN ('MERGED', 'IGNORED') THEN 1 END) as resolved_count,
                COUNT(*) as total_count,
                AVG(CASE 
                    WHEN resolved_at IS NOT NULL AND detected_at IS NOT NULL 
                    THEN EXTRACT(EPOCH FROM (resolved_at - detected_at))/3600 
                END) as avg_resolution_hours
            FROM destination_duplicates
        """
        )

        efficiency_result = db.execute(efficiency_query).fetchone()

        resolution_rate = 0
        if efficiency_result.total_count > 0:
            resolution_rate = round(
                (efficiency_result.resolved_count / efficiency_result.total_count)
                * 100,
                2,
            )

        return {
            "overview": {
                "total_duplicates": total_duplicates,
                "pending_count": efficiency_result.pending_count,
                "resolved_count": efficiency_result.resolved_count,
                "resolution_rate_percent": resolution_rate,
                "avg_resolution_hours": round(
                    float(efficiency_result.avg_resolution_hours or 0), 2
                ),
            },
            "by_status": status_stats,
            "by_detection_method": method_stats,
            "daily_detections": daily_stats,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


# 중복 배치 처리 API
@router.post("/batch-process")
def batch_process_duplicates(
    action_data: dict[str, Any] = Body(..., description="배치 처리 데이터"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    여러 중복을 배치로 처리하는 API

    action_data 예시:
    {
        "action": "ignore",  // "ignore" 또는 "merge"
        "duplicate_ids": ["uuid1", "uuid2", "uuid3"],
        "reason": "모두 거짓 양성",
        "merge_strategy": {  // merge 액션인 경우만
            "keep_primary": true,
            "merge_fields": ["amenities"]
        }
    }
    """
    try:
        action = action_data.get("action")
        duplicate_ids = action_data.get("duplicate_ids", [])
        reason = action_data.get("reason", "")

        if action not in ["ignore", "merge"]:
            raise HTTPException(
                status_code=400, detail="action은 'ignore' 또는 'merge'여야 합니다."
            )

        if not duplicate_ids:
            raise HTTPException(
                status_code=400, detail="처리할 중복 ID 목록이 필요합니다."
            )

        results = {"success_count": 0, "failed_count": 0, "details": []}

        for duplicate_id in duplicate_ids:
            try:
                if action == "ignore":
                    # 개별 무시 처리
                    ignore_reason = {
                        "reason": reason,
                        "admin_notes": f"배치 처리: {reason}",
                    }
                    ignore_duplicate(duplicate_id, ignore_reason, db, current_admin)

                elif action == "merge":
                    # 개별 병합 처리
                    merge_strategy = action_data.get(
                        "merge_strategy",
                        {
                            "keep_primary": True,
                            "merge_fields": [],
                            "admin_notes": f"배치 처리: {reason}",
                        },
                    )
                    merge_duplicate(duplicate_id, merge_strategy, db, current_admin)

                results["success_count"] += 1
                results["details"].append(
                    {
                        "duplicate_id": duplicate_id,
                        "status": "success",
                        "message": f"{action} 처리 완료",
                    }
                )

            except Exception as e:
                results["failed_count"] += 1
                results["details"].append(
                    {
                        "duplicate_id": duplicate_id,
                        "status": "failed",
                        "message": f"{action} 처리 실패: {str(e)}",
                    }
                )

        return {
            "success": True,
            "message": f"배치 처리 완료: 성공 {results['success_count']}건, 실패 {results['failed_count']}건",
            "results": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배치 처리 실패: {str(e)}")
