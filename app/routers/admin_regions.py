"""
관리자 지역 관리 API 라우터
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.database import get_db
from app.models.region import Region
from app.auth import require_admin_permission
from app.schemas.region_schemas import (
    RegionResponse, 
    RegionUpdateRequest,
    RegionStatsResponse,
    CoordinateUpdateRequest
)

router = APIRouter(prefix="/admin/regions", tags=["Admin - Regions"])


@router.get("/", response_model=Dict[str, Any])
async def get_all_regions(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(50, ge=1, le=200, description="페이지당 항목 수"),
    search: Optional[str] = Query(None, description="검색어"),
    region_level: Optional[int] = Query(None, ge=1, le=2, description="지역 레벨 필터"),
    is_active: Optional[bool] = Query(None, description="활성 상태 필터"),
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin_permission(["region:read"]))
):
    """
    모든 지역 정보 조회 (관리자용)
    - 페이지네이션 지원
    - 검색 및 필터링 기능
    """
    try:
        # 기본 쿼리
        query = db.query(Region)
        
        # 검색 필터
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Region.region_name.ilike(search_pattern),
                    Region.region_name_full.ilike(search_pattern),
                    Region.region_code.ilike(search_pattern)
                )
            )
        
        # 지역 레벨 필터
        if region_level is not None:
            query = query.filter(Region.region_level == region_level)
        
        # 활성 상태 필터
        if is_active is not None:
            query = query.filter(Region.is_active == is_active)
        
        # 전체 개수 계산
        total_count = query.count()
        
        # 페이지네이션 적용
        offset = (page - 1) * page_size
        regions = query.offset(offset).limit(page_size).all()
        
        # 응답 데이터 구성
        region_list = []
        for region in regions:
            region_data = {
                "region_id": str(region.region_id),
                "region_code": region.region_code,
                "region_name": region.region_name,
                "region_name_full": region.region_name_full,
                "parent_region_code": region.parent_region_code,
                "region_level": region.region_level,
                "latitude": float(region.latitude) if region.latitude else None,
                "longitude": float(region.longitude) if region.longitude else None,
                "grid_x": region.grid_x,
                "grid_y": region.grid_y,
                "is_active": region.is_active,
                "api_mappings": region.api_mappings or {},
                "coordinate_info": region.coordinate_info or {},
                "created_at": region.created_at.isoformat() if region.created_at else None,
                "updated_at": region.updated_at.isoformat() if region.updated_at else None,
            }
            region_list.append(region_data)
        
        # 페이지네이션 정보
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "regions": region_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "filters": {
                "search": search,
                "region_level": region_level,
                "is_active": is_active,
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"지역 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/{region_code}", response_model=RegionResponse)
async def get_region_detail(
    region_code: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin_permission(["region:read"]))
):
    """특정 지역 상세 정보 조회"""
    region = db.query(Region).filter(Region.region_code == region_code).first()
    
    if not region:
        raise HTTPException(
            status_code=404,
            detail=f"지역 코드 '{region_code}'를 찾을 수 없습니다."
        )
    
    return RegionResponse.from_orm(region)


@router.put("/{region_code}", response_model=RegionResponse)
async def update_region(
    region_code: str,
    region_data: RegionUpdateRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin_permission(["region:write"]))
):
    """지역 정보 업데이트"""
    region = db.query(Region).filter(Region.region_code == region_code).first()
    
    if not region:
        raise HTTPException(
            status_code=404,
            detail=f"지역 코드 '{region_code}'를 찾을 수 없습니다."
        )
    
    try:
        # 업데이트할 필드만 적용
        update_data = region_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(region, field):
                setattr(region, field, value)
        
        db.commit()
        db.refresh(region)
        
        return RegionResponse.from_orm(region)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"지역 정보 업데이트 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/stats/overview", response_model=RegionStatsResponse)
async def get_region_statistics(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin_permission(["region:read"]))
):
    """지역 통계 정보 조회"""
    try:
        # 기본 통계
        total_regions = db.query(Region).count()
        active_regions = db.query(Region).filter(Region.is_active == True).count()
        inactive_regions = total_regions - active_regions
        
        # 레벨별 통계
        provinces = db.query(Region).filter(Region.region_level == 1).count()
        cities = db.query(Region).filter(Region.region_level == 2).count()
        
        # 좌표 정보 통계
        with_coordinates = db.query(Region).filter(
            and_(Region.latitude.isnot(None), Region.longitude.isnot(None))
        ).count()
        
        with_grid_coordinates = db.query(Region).filter(
            and_(Region.grid_x.isnot(None), Region.grid_y.isnot(None))
        ).count()
        
        # API 매핑 통계
        with_api_mappings = db.query(Region).filter(
            Region.api_mappings.isnot(None)
        ).count()
        
        return RegionStatsResponse(
            total_regions=total_regions,
            active_regions=active_regions,
            inactive_regions=inactive_regions,
            provinces=provinces,
            cities=cities,
            with_coordinates=with_coordinates,
            with_grid_coordinates=with_grid_coordinates,
            with_api_mappings=with_api_mappings,
            coordinate_coverage=round((with_coordinates / total_regions) * 100, 1) if total_regions > 0 else 0,
            grid_coverage=round((with_grid_coordinates / total_regions) * 100, 1) if total_regions > 0 else 0,
            api_mapping_coverage=round((with_api_mappings / total_regions) * 100, 1) if total_regions > 0 else 0,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/coordinates/bulk-update")
async def bulk_update_coordinates(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin_permission(["region:write"]))
):
    """
    좌표 정보 일괄 업데이트
    하드코딩된 좌표 데이터를 데이터베이스에 반영
    """
    try:
        from app.data.region_coordinates import REGION_COORDINATES
        
        updated_count = 0
        
        for region_code, coord_data in REGION_COORDINATES.items():
            region = db.query(Region).filter(Region.region_code == region_code).first()
            
            if region:
                # 좌표 정보 업데이트
                if 'latitude' in coord_data and 'longitude' in coord_data:
                    region.latitude = coord_data['latitude']
                    region.longitude = coord_data['longitude']
                
                # 격자 좌표 업데이트
                if 'grid_x' in coord_data and 'grid_y' in coord_data:
                    region.grid_x = coord_data['grid_x']
                    region.grid_y = coord_data['grid_y']
                
                updated_count += 1
        
        db.commit()
        
        return {
            "message": f"{updated_count}개 지역의 좌표 정보가 업데이트되었습니다.",
            "updated_count": updated_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"좌표 정보 일괄 업데이트 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/coordinates/validate")
async def validate_coordinates(
    coordinates: List[CoordinateUpdateRequest] = Body(...),
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin_permission(["region:read"]))
):
    """좌표 정보 유효성 검증"""
    validation_results = []
    
    for coord in coordinates:
        result = {
            "region_code": coord.region_code,
            "valid": True,
            "errors": []
        }
        
        # 지역 존재 확인
        region = db.query(Region).filter(Region.region_code == coord.region_code).first()
        if not region:
            result["valid"] = False
            result["errors"].append("존재하지 않는 지역 코드")
            validation_results.append(result)
            continue
        
        # 좌표 범위 검증 (한국 영역)
        if coord.latitude is not None:
            if not (33.0 <= coord.latitude <= 38.6):
                result["valid"] = False
                result["errors"].append("위도가 한국 영역을 벗어남")
        
        if coord.longitude is not None:
            if not (124.6 <= coord.longitude <= 131.9):
                result["valid"] = False
                result["errors"].append("경도가 한국 영역을 벗어남")
        
        # 격자 좌표 검증
        if coord.grid_x is not None:
            if not (1 <= coord.grid_x <= 200):
                result["valid"] = False
                result["errors"].append("격자 X 좌표 범위 초과")
        
        if coord.grid_y is not None:
            if not (1 <= coord.grid_y <= 200):
                result["valid"] = False
                result["errors"].append("격자 Y 좌표 범위 초과")
        
        validation_results.append(result)
    
    valid_count = sum(1 for r in validation_results if r["valid"])
    
    return {
        "validation_results": validation_results,
        "summary": {
            "total": len(validation_results),
            "valid": valid_count,
            "invalid": len(validation_results) - valid_count
        }
    }


@router.get("/hierarchy/tree")
async def get_region_hierarchy(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin_permission(["region:read"]))
):
    """지역 계층 구조 트리 조회"""
    try:
        # 모든 활성 지역 조회
        regions = db.query(Region).filter(Region.is_active == True).order_by(
            Region.region_level, Region.region_name
        ).all()
        
        # 계층 구조 구성
        region_dict = {region.region_code: region for region in regions}
        tree = []
        
        # 1차 지역 (광역시도) 찾기
        for region in regions:
            if region.region_level == 1:
                region_node = {
                    "region_code": region.region_code,
                    "region_name": region.region_name,
                    "region_level": region.region_level,
                    "children": []
                }
                
                # 하위 지역 찾기
                for child_region in regions:
                    if child_region.parent_region_code == region.region_code:
                        child_node = {
                            "region_code": child_region.region_code,
                            "region_name": child_region.region_name,
                            "region_level": child_region.region_level,
                            "children": []
                        }
                        region_node["children"].append(child_node)
                
                tree.append(region_node)
        
        return {
            "tree": tree,
            "total_provinces": len([r for r in regions if r.region_level == 1]),
            "total_cities": len([r for r in regions if r.region_level == 2])
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"지역 계층 구조 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/api-compatibility/check")
async def check_api_compatibility(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin_permission(["region:read"]))
):
    """외부 API와의 호환성 확인"""
    try:
        regions = db.query(Region).filter(Region.is_active == True).all()
        
        compatibility_report = {
            "weather_api": {
                "compatible": 0,
                "incompatible": 0,
                "issues": []
            },
            "tour_api": {
                "compatible": 0,
                "incompatible": 0,
                "issues": []
            }
        }
        
        for region in regions:
            # 기상청 API 호환성 확인
            if region.grid_x and region.grid_y:
                compatibility_report["weather_api"]["compatible"] += 1
            else:
                compatibility_report["weather_api"]["incompatible"] += 1
                compatibility_report["weather_api"]["issues"].append({
                    "region_code": region.region_code,
                    "region_name": region.region_name,
                    "issue": "격자 좌표 정보 없음"
                })
            
            # 관광공사 API 호환성 확인
            if region.api_mappings and region.api_mappings.get("tour_api"):
                compatibility_report["tour_api"]["compatible"] += 1
            else:
                compatibility_report["tour_api"]["incompatible"] += 1
                compatibility_report["tour_api"]["issues"].append({
                    "region_code": region.region_code,
                    "region_name": region.region_name,
                    "issue": "관광공사 API 매핑 정보 없음"
                })
        
        return compatibility_report
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"API 호환성 확인 중 오류가 발생했습니다: {str(e)}"
        )