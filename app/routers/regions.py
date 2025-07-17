import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.data.region_coordinates import get_all_coordinates
from app.database import get_db
from app.models import Region
from app.schemas.regions import (
    RegionCreate,
    RegionListResponse,
    RegionResponse,
    RegionUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("/missing-coordinates")
async def get_missing_coordinates(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """좌표가 없는 지역 목록 조회"""
    try:
        # 좌표가 없는 지역 조회
        regions = db.query(Region).filter(
            or_(
                Region.latitude == None,
                Region.longitude == None
            )
        ).order_by(Region.region_code).all()

        return {
            "total": len(regions),
            "regions": [{
                "region_code": r.region_code,
                "region_name": r.region_name,
                "region_level": r.region_level,
                "parent_region_code": r.parent_region_code
            } for r in regions]
        }
    except Exception as e:
        logger.error(f"Failed to get missing coordinates: {str(e)}")
        raise HTTPException(status_code=500, detail="좌표 누락 지역 조회 실패")


@router.post("/update-coordinates")
async def update_region_coordinates(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """모든 지역의 좌표를 일괄 업데이트"""
    try:
        # 관리자 권한 확인 (super_admin만 가능) - 일단 모든 관리자에게 허용
        # TODO: super_admin 역할 확인 로직 추가 필요

        # 좌표 데이터 가져오기
        coordinates_data = get_all_coordinates()

        updated_count = 0
        skipped_count = 0
        not_found_count = 0

        for region_code, coord_info in coordinates_data.items():
            region = db.query(Region).filter(Region.region_code == region_code).first()

            if region:
                # 이미 좌표가 있는 경우 스킵
                if region.latitude and region.longitude:
                    skipped_count += 1
                    continue

                # 좌표 업데이트
                region.latitude = coord_info["latitude"]
                region.longitude = coord_info["longitude"]
                updated_count += 1
            else:
                not_found_count += 1
                logger.warning(f"Region not found: {region_code} - {coord_info['name']}")

        db.commit()

        logger.info(f"Region coordinates updated by {current_admin.email}: "
                   f"updated={updated_count}, skipped={skipped_count}, not_found={not_found_count}")

        return {
            "message": "지역 좌표 업데이트 완료",
            "updated": updated_count,
            "skipped": skipped_count,
            "not_found": not_found_count,
            "total": len(coordinates_data)
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update region coordinates: {str(e)}")
        raise HTTPException(status_code=500, detail="지역 좌표 업데이트 실패")


@router.get("/tree/hierarchy")
async def get_region_tree(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """지역 계층 구조 조회"""
    try:
        # 모든 지역 조회
        regions = db.query(Region).order_by(Region.region_level, Region.region_code).all()

        # 계층 구조로 변환
        region_map = {r.region_code: {
            "region_code": r.region_code,
            "region_name": r.region_name,
            "region_level": r.region_level,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "children": []
        } for r in regions}

        # 트리 구성
        tree = []
        for region in regions:
            if region.parent_region_code and region.parent_region_code in region_map:
                region_map[region.parent_region_code]["children"].append(
                    region_map[region.region_code]
                )
            elif not region.parent_region_code:
                tree.append(region_map[region.region_code])

        return {"tree": tree}
    except Exception as e:
        logger.error(f"Failed to get region tree: {str(e)}")
        raise HTTPException(status_code=500, detail="지역 계층 구조 조회 실패")


@router.get("", response_model=RegionListResponse)
async def get_regions(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    search: str | None = None,
    parent_region_code: str | None = None,
    region_level: int | None = None,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """지역 목록 조회"""
    try:
        query = db.query(Region)

        # 검색 조건
        if search:
            query = query.filter(
                or_(
                    Region.region_name.ilike(f"%{search}%"),
                    Region.region_code.ilike(f"%{search}%")
                )
            )

        if parent_region_code:
            query = query.filter(Region.parent_region_code == parent_region_code)

        if region_level is not None:
            query = query.filter(Region.region_level == region_level)

        # 전체 개수
        total = query.count()

        # 페이징
        query = query.order_by(Region.region_code)
        query = query.offset((page - 1) * size).limit(size)

        regions = query.all()

        return {
            "regions": regions,
            "total": total,
            "page": page,
            "size": size,
            "total_pages": (total + size - 1) // size
        }
    except Exception as e:
        logger.error(f"Failed to get regions: {str(e)}")
        raise HTTPException(status_code=500, detail="지역 목록 조회 실패")


@router.get("/{region_code}", response_model=RegionResponse)
async def get_region(
    region_code: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """특정 지역 조회"""
    region = db.query(Region).filter(Region.region_code == region_code).first()
    if not region:
        raise HTTPException(status_code=404, detail="지역을 찾을 수 없습니다")
    return region


@router.post("", response_model=RegionResponse)
async def create_region(
    region_data: RegionCreate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """새 지역 생성"""
    try:
        # 중복 확인
        existing_region = db.query(Region).filter(
            Region.region_code == region_data.region_code
        ).first()
        if existing_region:
            raise HTTPException(status_code=400, detail="이미 존재하는 지역 코드입니다")

        region = Region(**region_data.dict())
        db.add(region)
        db.commit()
        db.refresh(region)

        logger.info(f"Region created: {region.region_code} by {current_admin.email}")
        return region
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create region: {str(e)}")
        raise HTTPException(status_code=500, detail="지역 생성 실패")


@router.put("/{region_code}", response_model=RegionResponse)
async def update_region(
    region_code: str,
    region_data: RegionUpdate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """지역 정보 수정"""
    try:
        region = db.query(Region).filter(Region.region_code == region_code).first()
        if not region:
            raise HTTPException(status_code=404, detail="지역을 찾을 수 없습니다")

        update_data = region_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(region, key, value)

        db.commit()
        db.refresh(region)

        logger.info(f"Region updated: {region_code} by {current_admin.email}")
        return region
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update region: {str(e)}")
        raise HTTPException(status_code=500, detail="지역 수정 실패")


@router.delete("/{region_code}")
async def delete_region(
    region_code: str,
    force: bool = Query(False, description="하위 지역과 함께 강제 삭제"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """지역 삭제"""
    try:
        region = db.query(Region).filter(Region.region_code == region_code).first()
        if not region:
            raise HTTPException(status_code=404, detail="지역을 찾을 수 없습니다")

        # 하위 지역이 있는지 확인
        child_regions_query = db.query(Region).filter(
            Region.parent_region_code == region_code
        )
        child_count = child_regions_query.count()
        
        if child_count > 0 and not force:
            # 하위 지역 정보도 함께 반환
            child_regions = child_regions_query.all()
            child_info = [{"region_code": c.region_code, "region_name": c.region_name} for c in child_regions[:5]]
            
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "하위 지역이 있는 지역은 삭제할 수 없습니다",
                    "child_count": child_count,
                    "child_regions": child_info,
                    "has_more": child_count > 5
                }
            )
        
        # 강제 삭제인 경우 하위 지역도 함께 삭제
        if force:
            # 삭제할 모든 지역 코드 수집 (순환 참조 방지)
            all_region_codes = []
            visited = set()
            
            def collect_children(parent_code):
                if parent_code in visited:
                    return  # 순환 참조 방지
                visited.add(parent_code)
                all_region_codes.append(parent_code)
                
                children = db.query(Region).filter(
                    Region.parent_region_code == parent_code
                ).all()
                for child in children:
                    if child.region_code not in visited:
                        collect_children(child.region_code)
            
            collect_children(region_code)
            
            # 관련 데이터 삭제 (외래 키 제약 조건 해결)
            # 각 테이블에서 해당 지역들과 관련된 데이터 삭제
            from app.models import (
                FestivalEvent, TouristAttraction, CulturalFacility,
                Accommodation, Restaurant, Shopping,
                WeatherData, WeatherForecast, WeatherInfo, PetTourInfo
            )
            
            # 관련 데이터 삭제 카운트
            related_counts = {}
            
            # festivals_events
            festivals_count = db.query(FestivalEvent).filter(
                FestivalEvent.region_code.in_(all_region_codes)
            ).count()
            if festivals_count > 0:
                db.query(FestivalEvent).filter(
                    FestivalEvent.region_code.in_(all_region_codes)
                ).delete(synchronize_session=False)
                related_counts['festivals_events'] = festivals_count
            
            # tourist_attractions
            attractions_count = db.query(TouristAttraction).filter(
                TouristAttraction.region_code.in_(all_region_codes)
            ).count()
            if attractions_count > 0:
                db.query(TouristAttraction).filter(
                    TouristAttraction.region_code.in_(all_region_codes)
                ).delete(synchronize_session=False)
                related_counts['tourist_attractions'] = attractions_count
            
            # cultural_facilities
            cultural_count = db.query(CulturalFacility).filter(
                CulturalFacility.region_code.in_(all_region_codes)
            ).count()
            if cultural_count > 0:
                db.query(CulturalFacility).filter(
                    CulturalFacility.region_code.in_(all_region_codes)
                ).delete(synchronize_session=False)
                related_counts['cultural_facilities'] = cultural_count
            
            # accommodations
            accommodations_count = db.query(Accommodation).filter(
                Accommodation.region_code.in_(all_region_codes)
            ).count()
            if accommodations_count > 0:
                db.query(Accommodation).filter(
                    Accommodation.region_code.in_(all_region_codes)
                ).delete(synchronize_session=False)
                related_counts['accommodations'] = accommodations_count
            
            # restaurants
            restaurants_count = db.query(Restaurant).filter(
                Restaurant.region_code.in_(all_region_codes)
            ).count()
            if restaurants_count > 0:
                db.query(Restaurant).filter(
                    Restaurant.region_code.in_(all_region_codes)
                ).delete(synchronize_session=False)
                related_counts['restaurants'] = restaurants_count
            
            # shopping
            shopping_count = db.query(Shopping).filter(
                Shopping.region_code.in_(all_region_codes)
            ).count()
            if shopping_count > 0:
                db.query(Shopping).filter(
                    Shopping.region_code.in_(all_region_codes)
                ).delete(synchronize_session=False)
                related_counts['shopping'] = shopping_count
            
            # weather_data
            weather_data_count = db.query(WeatherData).filter(
                WeatherData.region_code.in_(all_region_codes)
            ).count()
            if weather_data_count > 0:
                db.query(WeatherData).filter(
                    WeatherData.region_code.in_(all_region_codes)
                ).delete(synchronize_session=False)
                related_counts['weather_data'] = weather_data_count
            
            # weather_forecasts
            weather_forecasts_count = db.query(WeatherForecast).filter(
                WeatherForecast.region_code.in_(all_region_codes)
            ).count()
            if weather_forecasts_count > 0:
                db.query(WeatherForecast).filter(
                    WeatherForecast.region_code.in_(all_region_codes)
                ).delete(synchronize_session=False)
                related_counts['weather_forecasts'] = weather_forecasts_count
            
            # weather_info
            weather_info_count = db.query(WeatherInfo).filter(
                WeatherInfo.region_code.in_(all_region_codes)
            ).count()
            if weather_info_count > 0:
                db.query(WeatherInfo).filter(
                    WeatherInfo.region_code.in_(all_region_codes)
                ).delete(synchronize_session=False)
                related_counts['weather_info'] = weather_info_count
            
            # pet_tour_info
            pet_tour_count = db.query(PetTourInfo).filter(
                PetTourInfo.region_code.in_(all_region_codes)
            ).count()
            if pet_tour_count > 0:
                db.query(PetTourInfo).filter(
                    PetTourInfo.region_code.in_(all_region_codes)
                ).delete(synchronize_session=False)
                related_counts['pet_tour_info'] = pet_tour_count
            
            # 이제 지역들 삭제
            db.query(Region).filter(
                Region.region_code.in_(all_region_codes)
            ).delete(synchronize_session=False)
            
            deleted_count = len(all_region_codes)
            
            # 로그 기록
            if related_counts:
                logger.info(f"Related data deleted for regions {all_region_codes}: {related_counts}")
        else:
            # 일반 삭제인 경우 관련 데이터가 있는지 확인
            from app.models import (
                FestivalEvent, TouristAttraction, CulturalFacility,
                Accommodation, Restaurant, Shopping,
                WeatherData, WeatherForecast, WeatherInfo, PetTourInfo
            )
            
            # 관련 데이터 존재 여부 확인
            has_related_data = False
            related_data_info = []
            
            if db.query(FestivalEvent).filter(FestivalEvent.region_code == region_code).first():
                has_related_data = True
                related_data_info.append("축제/이벤트")
            if db.query(TouristAttraction).filter(TouristAttraction.region_code == region_code).first():
                has_related_data = True
                related_data_info.append("관광지")
            if db.query(CulturalFacility).filter(CulturalFacility.region_code == region_code).first():
                has_related_data = True
                related_data_info.append("문화시설")
            if db.query(Accommodation).filter(Accommodation.region_code == region_code).first():
                has_related_data = True
                related_data_info.append("숙박시설")
            if db.query(Restaurant).filter(Restaurant.region_code == region_code).first():
                has_related_data = True
                related_data_info.append("음식점")
            if db.query(Shopping).filter(Shopping.region_code == region_code).first():
                has_related_data = True
                related_data_info.append("쇼핑")
            if db.query(WeatherData).filter(WeatherData.region_code == region_code).first():
                has_related_data = True
                related_data_info.append("날씨 데이터")
            if db.query(PetTourInfo).filter(PetTourInfo.region_code == region_code).first():
                has_related_data = True
                related_data_info.append("반려동물 여행 정보")
            
            if has_related_data:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "관련 데이터가 있는 지역은 삭제할 수 없습니다",
                        "related_data": related_data_info
                    }
                )
            
            db.delete(region)
            deleted_count = 1

        db.commit()

        logger.info(f"Region deleted{' (forced)' if force else ''}: {region_code} by {current_admin.email}")
        return {
            "message": f"지역이 삭제되었습니다{' (하위 지역 포함)' if force and child_count > 0 else ''}",
            "deleted_count": deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete region: {str(e)}")
        raise HTTPException(status_code=500, detail="지역 삭제 실패")
