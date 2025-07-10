"""
지역 정보 관리 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Region, UnifiedRegionNew
from pydantic import BaseModel


router = APIRouter(prefix="/regions", tags=["Regions"])


class RegionResponse(BaseModel):
    """지역 정보 응답 스키마"""
    region_code: str
    region_name: str
    parent_region_code: Optional[str] = None
    region_level: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        from_attributes = True


class RegionMapResponse(BaseModel):
    """지역 코드 매핑 응답 스키마"""
    region_map: dict[str, str]
    sigungu_map: dict[str, str]


@router.get("/", response_model=List[RegionResponse])
def get_regions(
    level: Optional[int] = Query(None, description="지역 레벨 필터 (1: 시도, 2: 시군구)"),
    parent_code: Optional[str] = Query(None, description="상위 지역 코드"),
    db: Session = Depends(get_db),
):
    """지역 목록 조회"""
    query = db.query(Region)
    
    if level is not None:
        query = query.filter(Region.region_level == level)
    
    if parent_code:
        query = query.filter(Region.parent_region_code == parent_code)
    
    regions = query.order_by(Region.region_code).all()
    return regions


@router.get("/provinces", response_model=List[RegionResponse])
def get_provinces(db: Session = Depends(get_db)):
    """시도 목록 조회 (level 1)"""
    provinces = (
        db.query(Region)
        .filter(Region.region_level == 1)
        .order_by(Region.region_code)
        .all()
    )
    return provinces


@router.get("/sigungu/{province_code}", response_model=List[RegionResponse])
def get_sigungu_by_province(
    province_code: str,
    db: Session = Depends(get_db),
):
    """특정 시도의 시군구 목록 조회"""
    sigungu = (
        db.query(Region)
        .filter(Region.parent_region_code == province_code)
        .filter(Region.region_level == 2)
        .order_by(Region.region_code)
        .all()
    )
    return sigungu


@router.get("/map", response_model=RegionMapResponse)
def get_region_map(db: Session = Depends(get_db)):
    """지역 코드 매핑 정보 조회 (프론트엔드 호환성)"""
    # 시도 정보
    provinces = (
        db.query(Region)
        .filter(Region.region_level == 1)
        .all()
    )
    region_map = {region.region_code: region.region_name for region in provinces}
    
    # 서울시 구 정보 (하드코딩 대체용)
    seoul_sigungu = (
        db.query(Region)
        .filter(Region.parent_region_code == "1")  # 서울특별시
        .filter(Region.region_level == 2)
        .all()
    )
    sigungu_map = {region.region_code: region.region_name for region in seoul_sigungu}
    
    return RegionMapResponse(
        region_map=region_map,
        sigungu_map=sigungu_map
    )


@router.get("/{region_code}")
def get_region(region_code: str, db: Session = Depends(get_db)):
    """특정 지역 정보 조회"""
    region = db.query(Region).filter(Region.region_code == region_code).first()
    if not region:
        raise HTTPException(status_code=404, detail="지역을 찾을 수 없습니다.")
    return region


@router.get("/search/")
def search_regions(
    name: str = Query(..., description="지역명 검색어"),
    db: Session = Depends(get_db),
):
    """지역명으로 검색"""
    regions = (
        db.query(Region)
        .filter(Region.region_name.contains(name))
        .order_by(Region.region_level, Region.region_code)
        .all()
    )
    return regions