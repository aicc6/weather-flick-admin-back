from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..services.weather_service import get_weather_service, KTOWeatherService, MAJOR_CITIES
from ..weather.models import (
    WeatherInfo, LocationCoordinate,
    UltraSrtNcstRequest, UltraSrtFcstRequest, VilageFcstRequest,
    WeatherResponse
)
from ..weather.scheduler import weather_collector
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("/current", response_model=WeatherInfo)
async def get_current_weather(
    nx: int = Query(60, description="예보지점 X 좌표 (기본값: 서울)"),
    ny: int = Query(127, description="예보지점 Y 좌표 (기본값: 서울)"),
    location: str = Query("서울", description="지역명"),
    weather_service: KTOWeatherService = Depends(get_weather_service)
):
    """
    현재 날씨 정보 조회 (초단기실황)

    - **nx**: 기상청 격자 X 좌표
    - **ny**: 기상청 격자 Y 좌표
    - **location**: 지역명 (선택사항)
    """
    try:
        # 디버그 정보 로깅
        logger.info(f"날씨 조회 요청: nx={nx}, ny={ny}, location={location}")

        weather = weather_service.get_current_weather(nx, ny, location)
        if not weather:
            # 더 구체적인 404 메시지
            error_detail = f"날씨 정보를 찾을 수 없습니다. 좌표: ({nx}, {ny}), 지역: {location}. "
            error_detail += "기상청 API에서 해당 시간대의 데이터를 제공하지 않거나, API 키 설정에 문제가 있을 수 있습니다. "
            error_detail += "/api/weather/debug/api-test 엔드포인트로 API 상태를 확인해보세요."
            raise HTTPException(status_code=404, detail=error_detail)

        return weather

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"현재 날씨 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"날씨 정보 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/forecast", response_model=List[WeatherInfo])
async def get_weather_forecast(
    nx: int = Query(60, description="예보지점 X 좌표 (기본값: 서울)"),
    ny: int = Query(127, description="예보지점 Y 좌표 (기본값: 서울)"),
    location: str = Query("서울", description="지역명"),
    weather_service: KTOWeatherService = Depends(get_weather_service)
):
    """
    날씨 예보 정보 조회 (초단기예보 + 단기예보)

    - **nx**: 기상청 격자 X 좌표
    - **ny**: 기상청 격자 Y 좌표
    - **location**: 지역명 (선택사항)
    """
    try:
        forecasts = weather_service.get_weather_forecast(nx, ny, location)
        return forecasts

    except Exception as e:
        logger.error(f"날씨 예보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="날씨 예보 조회 중 오류가 발생했습니다.")


@router.get("/current/{city_name}", response_model=WeatherInfo)
async def get_current_weather_by_city(
    city_name: str,
    weather_service: KTOWeatherService = Depends(get_weather_service)
):
    """
    도시명으로 현재 날씨 정보 조회

    - **city_name**: 도시명 (서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종, 경기, 강원, 충북, 충남, 전북, 전남, 경북, 경남, 제주)
    """
    if city_name not in MAJOR_CITIES:
        available_cities = ", ".join(MAJOR_CITIES.keys())
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 도시입니다. 사용 가능한 도시: {available_cities}"
        )

    try:
        coordinate = MAJOR_CITIES[city_name]
        weather = weather_service.get_current_weather(coordinate.nx, coordinate.ny, coordinate.name)

        if not weather:
            raise HTTPException(status_code=404, detail=f"{city_name}의 날씨 정보를 찾을 수 없습니다.")

        return weather

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{city_name} 현재 날씨 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="날씨 정보 조회 중 오류가 발생했습니다.")


@router.get("/forecast/{city_name}", response_model=List[WeatherInfo])
async def get_weather_forecast_by_city(
    city_name: str,
    weather_service: KTOWeatherService = Depends(get_weather_service)
):
    """
    도시명으로 날씨 예보 정보 조회

    - **city_name**: 도시명 (서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종, 경기, 강원, 충북, 충남, 전북, 전남, 경북, 경남, 제주)
    """
    if city_name not in MAJOR_CITIES:
        available_cities = ", ".join(MAJOR_CITIES.keys())
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 도시입니다. 사용 가능한 도시: {available_cities}"
        )

    try:
        coordinate = MAJOR_CITIES[city_name]
        forecasts = weather_service.get_weather_forecast(coordinate.nx, coordinate.ny, coordinate.name)

        return forecasts

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{city_name} 날씨 예보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="날씨 예보 조회 중 오류가 발생했습니다.")


@router.get("/cities", response_model=List[LocationCoordinate])
async def get_available_cities():
    """
    사용 가능한 도시 목록 조회
    """
    return list(MAJOR_CITIES.values())


@router.post("/ultra-srt-ncst", response_model=WeatherResponse)
async def get_ultra_srt_ncst(
    request: UltraSrtNcstRequest,
    weather_service: KTOWeatherService = Depends(get_weather_service)
):
    """
    초단기실황 조회 (Raw API)

    관광공사 API를 직접 호출하여 원본 응답을 반환합니다.
    """
    try:
        response = weather_service.get_ultra_srt_ncst(request)
        if not response:
            raise HTTPException(status_code=404, detail="초단기실황 정보를 찾을 수 없습니다.")

        return response

    except Exception as e:
        logger.error(f"초단기실황 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="초단기실황 조회 중 오류가 발생했습니다.")


@router.post("/ultra-srt-fcst", response_model=WeatherResponse)
async def get_ultra_srt_fcst(
    request: UltraSrtFcstRequest,
    weather_service: KTOWeatherService = Depends(get_weather_service)
):
    """
    초단기예보 조회 (Raw API)

    관광공사 API를 직접 호출하여 원본 응답을 반환합니다.
    """
    try:
        response = weather_service.get_ultra_srt_fcst(request)
        if not response:
            raise HTTPException(status_code=404, detail="초단기예보 정보를 찾을 수 없습니다.")

        return response

    except Exception as e:
        logger.error(f"초단기예보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="초단기예보 조회 중 오류가 발생했습니다.")


@router.post("/vilage-fcst", response_model=WeatherResponse)
async def get_vilage_fcst(
    request: VilageFcstRequest,
    weather_service: KTOWeatherService = Depends(get_weather_service)
):
    """
    단기예보 조회 (Raw API)

    관광공사 API를 직접 호출하여 원본 응답을 반환합니다.
    """
    try:
        response = weather_service.get_vilage_fcst(request)
        if not response:
            raise HTTPException(status_code=404, detail="단기예보 정보를 찾을 수 없습니다.")

        return response

    except Exception as e:
        logger.error(f"단기예보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="단기예보 조회 중 오류가 발생했습니다.")


@router.get("/health")
async def weather_health_check(weather_service: KTOWeatherService = Depends(get_weather_service)):
    """
    날씨 서비스 상태 확인
    """
    return {
        "status": "healthy",
        "service": "weather",
        "timestamp": datetime.now().isoformat(),
        "available_cities": len(MAJOR_CITIES),
        "api_key_configured": bool(weather_service.api_key),
        "api_key_length": len(weather_service.api_key) if weather_service.api_key else 0,
        "base_url": weather_service.base_url
    }


# ==================== 데이터베이스 관련 엔드포인트 ====================
# CityWeatherData 테이블이 제거되어 관련 엔드포인트들이 제거되었습니다.
# 날씨 데이터는 이제 weather_forecasts 테이블에서 관리됩니다.


# ==================== 데이터 수집 엔드포인트 ====================

@router.post("/collect/all")
async def collect_all_cities_data():
    """
    모든 주요 도시의 날씨 데이터를 수집하고 데이터베이스에 저장
    """
    try:
        result = await weather_collector.collect_all_cities_weather(include_forecast=True)
        return result
    except Exception as e:
        logger.error(f"Collect all cities error: {e}")
        raise HTTPException(status_code=500, detail="날씨 데이터 수집 중 오류가 발생했습니다.")


@router.post("/collect/current")
async def collect_current_weather_data():
    """
    모든 주요 도시의 현재 날씨만 수집하고 데이터베이스에 저장
    """
    try:
        result = await weather_collector.collect_current_weather_only()
        return result
    except Exception as e:
        logger.error(f"Collect current weather error: {e}")
        raise HTTPException(status_code=500, detail="현재 날씨 데이터 수집 중 오류가 발생했습니다.")


@router.get("/collect/stats")
async def get_collection_stats():
    """
    데이터 수집 통계 조회
    """
    try:
        stats = await weather_collector.get_collection_stats()
        return stats
    except Exception as e:
        logger.error(f"Get collection stats error: {e}")
        raise HTTPException(status_code=500, detail="수집 통계 조회 중 오류가 발생했습니다.")




@router.get("/summary")
def get_weather_summary(weather_service: KTOWeatherService = Depends(get_weather_service)):
    """
    주요 도시들의 현재 날씨 요약 및 통계 반환
    """
    cities = list(MAJOR_CITIES.keys())
    regions = []
    temps = []
    now = None
    for city_name in cities:
        weather = weather_service.get_current_weather_by_city(city_name)
        if weather and weather.temperature is not None:
            temps.append(weather.temperature)
            regions.append({
                "city_name": city_name,
                "region_code": MAJOR_CITIES[city_name].nx,
                "temperature": weather.temperature,
                "humidity": weather.humidity,
                "wind_speed": weather.wind_speed,
                "sky_condition": weather.sky_condition,
                "last_updated": weather.forecast_time.isoformat() if weather.forecast_time else None
            })
            if not now or (weather.forecast_time and weather.forecast_time > now):
                now = weather.forecast_time
    avg_temp = round(sum(temps) / len(temps), 1) if temps else None
    max_temp = max(temps) if temps else None
    min_temp = min(temps) if temps else None
    max_region = next((r["city_name"] for r in regions if r["temperature"] == max_temp), None)
    min_region = next((r["city_name"] for r in regions if r["temperature"] == min_temp), None)
    last_updated = now.isoformat() if now else None
    return {
        "regions": regions,
        "summary": {
            "region_count": len(regions),
            "avg_temp": avg_temp,
            "max_temp": max_temp,
            "min_temp": min_temp,
            "max_region": max_region,
            "min_region": min_region,
            "last_updated": last_updated
        }
    }




@router.get("/summary-forecast")
def get_weather_summary_from_forecasts(db: Session = Depends(get_db)):
    """
    weather_forecasts 테이블에서 날씨 통계 데이터를 제공합니다.
    최신 예보 데이터를 기반으로 주요 지역별 온도 통계를 계산합니다.
    """
    try:
        # 최신 예보 데이터 조회 (지역별 가장 최근 데이터)
        subquery = text("""
            SELECT DISTINCT region_code,
                   FIRST_VALUE(min_temp::numeric) OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as min_temp,
                   FIRST_VALUE(max_temp::numeric) OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as max_temp,
                   FIRST_VALUE(weather_condition) OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as weather_condition,
                   FIRST_VALUE(precipitation_prob) OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as precipitation_prob,
                   FIRST_VALUE(forecast_date) OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as latest_forecast_date
            FROM weather_forecasts 
            WHERE min_temp IS NOT NULL 
            AND max_temp IS NOT NULL 
            AND forecast_date >= CURRENT_DATE - INTERVAL '3 days'
        """)
        
        result = db.execute(subquery).fetchall()
        
        if not result:
            return {
                "regions": [],
                "summary": {
                    "region_count": 0,
                    "avg_temp": None,
                    "max_temp": None,
                    "min_temp": None,
                    "max_region": None,
                    "min_region": None,
                    "last_updated": None,
                    "message": "weather_forecasts 테이블에 최근 데이터가 없습니다."
                }
            }
        
        # 지역 정보 매핑을 위한 쿼리
        region_query = text("""
            SELECT region_code, region_name, region_name_full
            FROM regions 
            WHERE is_active = true
        """)
        regions_data = db.execute(region_query).fetchall()
        region_map = {r.region_code: r.region_name_full or r.region_name for r in regions_data}
        
        regions = []
        temps = []
        
        for row in result:
            # 평균 온도 계산 (최저온도와 최고온도의 평균)
            avg_temp = (float(row.min_temp) + float(row.max_temp)) / 2
            temps.append(avg_temp)
            
            region_name = region_map.get(row.region_code, f"지역코드_{row.region_code}")
            
            regions.append({
                "city_name": region_name,
                "region_code": row.region_code,
                "region_name": region_name,
                "temperature": round(avg_temp, 1),
                "min_temp": float(row.min_temp),
                "max_temp": float(row.max_temp),
                "weather_condition": row.weather_condition,
                "precipitation_prob": row.precipitation_prob,
                "last_updated": row.latest_forecast_date.isoformat() if row.latest_forecast_date else None
            })
        
        # 통계 계산
        avg_temp = round(sum(temps) / len(temps), 1) if temps else None
        max_temp = max(temps) if temps else None
        min_temp = min(temps) if temps else None
        
        max_region_data = next((r for r in regions if r["temperature"] == max_temp), None)
        min_region_data = next((r for r in regions if r["temperature"] == min_temp), None)
        
        max_region = max_region_data["region_name"] if max_region_data else None
        min_region = min_region_data["region_name"] if min_region_data else None
        
        # 가장 최근 업데이트 시간
        latest_update = max((r["last_updated"] for r in regions if r["last_updated"]), default=None)
        
        return {
            "regions": regions,
            "summary": {
                "region_count": len(regions),
                "avg_temp": avg_temp,
                "max_temp": max_temp,
                "min_temp": min_temp,
                "max_region": max_region,
                "min_region": min_region,
                "last_updated": latest_update,
                "data_source": "weather_forecasts"
            }
        }
        
    except Exception as e:
        logger.error(f"Weather forecast summary 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"예보 데이터 기반 날씨 요약 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/database/forecast-data")
def get_forecast_weather_data(
    limit: int = Query(20, description="반환할 데이터 수"),
    db: Session = Depends(get_db)
):
    """
    weather_forecasts 테이블에서 지역별 최신 날씨 예보 데이터를 반환합니다.
    날씨 정보 관리 페이지에서 사용됩니다.
    """
    try:
        # 지역별 최신 예보 데이터 조회
        query = text("""
            WITH latest_forecasts AS (
                SELECT DISTINCT region_code,
                       FIRST_VALUE(min_temp::numeric) OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as min_temp,
                       FIRST_VALUE(max_temp::numeric) OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as max_temp,
                       FIRST_VALUE(weather_condition) OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as weather_condition,
                       FIRST_VALUE(precipitation_prob) OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as precipitation_prob,
                       FIRST_VALUE(forecast_date) OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as forecast_date,
                       FIRST_VALUE(created_at) OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as created_at,
                       ROW_NUMBER() OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as rn
                FROM weather_forecasts 
                WHERE min_temp IS NOT NULL 
                AND max_temp IS NOT NULL 
                AND forecast_date >= CURRENT_DATE - INTERVAL '3 days'
            )
            SELECT lf.*, r.region_name, r.region_name_full
            FROM latest_forecasts lf
            LEFT JOIN regions r ON lf.region_code = r.region_code
            WHERE lf.rn = 1
            ORDER BY lf.created_at DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, {"limit": limit}).fetchall()
        
        if not result:
            return {
                "success": True,
                "data": [],
                "message": "weather_forecasts 테이블에 최근 데이터가 없습니다."
            }
        
        # 응답 데이터 구성
        weather_data = []
        for row in result:
            # 평균 온도 계산
            avg_temp = (float(row.min_temp) + float(row.max_temp)) / 2
            city_name = row.region_name_full or row.region_name or f"지역코드_{row.region_code}"
            
            weather_data.append({
                "id": f"forecast_{row.region_code}",
                "city_name": city_name,
                "region_code": row.region_code,
                "temperature": round(avg_temp, 1),
                "min_temp": float(row.min_temp),
                "max_temp": float(row.max_temp),
                "weather_description": row.weather_condition,
                "weather_condition": row.weather_condition,
                "precipitation_prob": row.precipitation_prob,
                "humidity": None,  # forecasts 테이블에는 없음
                "wind_speed": None,  # forecasts 테이블에는 없음
                "sky_condition": row.weather_condition,
                "forecast_date": row.forecast_date.isoformat() if row.forecast_date else None,
                "last_updated": row.created_at.isoformat() if row.created_at else None,
                "data_source": "weather_forecasts"
            })
        
        return {
            "success": True,
            "data": weather_data,
            "count": len(weather_data),
            "message": f"weather_forecasts 테이블에서 {len(weather_data)}개 지역의 날씨 데이터를 조회했습니다."
        }
        
    except Exception as e:
        logger.error(f"Forecast weather data 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"예보 데이터 조회 중 오류가 발생했습니다: {str(e)}")




@router.get("/debug/api-test")
async def debug_kma_api_test(weather_service: KTOWeatherService = Depends(get_weather_service)):
    """
    기상청 API 테스트 및 디버깅
    """
    try:
        from ..weather.models import UltraSrtNcstRequest
        from datetime import datetime, timedelta

        # 현재 시간 기준으로 발표시각 계산
        now = datetime.now()
        if now.minute < 40:
            base_time = now - timedelta(hours=1)
        else:
            base_time = now

        base_date = base_time.strftime("%Y%m%d")
        base_time_str = base_time.strftime("%H00")

        # 서울 좌표로 테스트
        request = UltraSrtNcstRequest(
            base_date=base_date,
            base_time=base_time_str,
            nx=60,
            ny=127
        )

        # 실제 API 호출
        response = weather_service.get_ultra_srt_ncst(request)

        debug_info = {
            "api_key_length": len(weather_service.api_key),
            "api_url": weather_service.base_url,
            "request_params": {
                "base_date": base_date,
                "base_time": base_time_str,
                "nx": 60,
                "ny": 127
            },
            "current_time": now.isoformat(),
            "calculated_base_time": base_time.isoformat(),
            "response_received": response is not None
        }

        if response:
            debug_info.update({
                "response_code": response.response.header.resultCode,
                "response_message": response.response.header.resultMsg,
                "total_count": response.response.header.totalCount,
                "items_count": len(response.response.body.items.item) if response.response.body.items.item else 0
            })

            # 첫 몇 개 아이템 샘플
            if response.response.body.items.item:
                debug_info["sample_items"] = [
                    {
                        "category": item.category,
                        "obsrValue": item.obsrValue,
                        "baseDate": item.baseDate,
                        "baseTime": item.baseTime
                    }
                    for item in response.response.body.items.item[:3]
                ]
        else:
            debug_info["error"] = "API 응답이 없습니다"

        return debug_info

    except Exception as e:
        logger.error(f"API 테스트 실패: {e}", exc_info=True)
        return {
            "error": str(e),
            "api_key_configured": bool(weather_service.api_key),
            "api_url": weather_service.base_url
        }
