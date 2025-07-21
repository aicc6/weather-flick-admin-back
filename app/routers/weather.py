import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.weather_service import (
    MAJOR_CITIES,
    KTOWeatherService,
    get_weather_service,
)
from ..weather.models import (
    LocationCoordinate,
    UltraSrtFcstRequest,
    UltraSrtNcstRequest,
    VilageFcstRequest,
    WeatherInfo,
    WeatherResponse,
)
from ..weather.scheduler import weather_collector

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


@router.get("/forecast", response_model=list[WeatherInfo])
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


@router.get("/forecast/{city_name}", response_model=list[WeatherInfo])
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


@router.get("/cities", response_model=list[LocationCoordinate])
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
# 날씨 데이터는 이제 weather_forecast 테이블에서 관리됩니다.


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
async def get_collection_stats(db: Session = Depends(get_db)):
    """
    데이터 수집 통계 조회
    """
    try:
        # 전체 지역 수와 수집된 지역 수 조회
        total_regions_query = text("""
            SELECT COUNT(DISTINCT region_code) as total
            FROM regions
            WHERE is_active = true
        """)
        total_regions = db.execute(total_regions_query).scalar()

        collected_regions_query = text("""
            SELECT COUNT(DISTINCT region_code) as collected
            FROM weather_forecast
            WHERE DATE(created_at) = CURRENT_DATE
        """)
        collected_regions = db.execute(collected_regions_query).scalar()

        # 오늘 수집 횟수
        today_collection_query = text("""
            SELECT COUNT(*) as count
            FROM weather_forecast
            WHERE DATE(created_at) = CURRENT_DATE
        """)
        today_collection_count = db.execute(today_collection_query).scalar()

        # 마지막 수집 시간
        last_collection_query = text("""
            SELECT MAX(created_at) as last_time
            FROM weather_forecast
        """)
        last_collection_time = db.execute(last_collection_query).scalar()

        # 최근 수집 이력 (예시)
        collection_history_query = text("""
            SELECT 
                wf.region_code,
                r.region_name,
                wf.created_at as collected_at,
                CASE 
                    WHEN wf.min_temp IS NOT NULL AND wf.max_temp IS NOT NULL 
                    THEN 'success' 
                    ELSE 'failed' 
                END as status
            FROM weather_forecast wf
            LEFT JOIN regions r ON wf.region_code = r.region_code
            WHERE wf.created_at >= NOW() - INTERVAL '24 hours'
            ORDER BY wf.created_at DESC
            LIMIT 10
        """)
        collection_history = db.execute(collection_history_query).fetchall()

        history_list = [
            {
                "region_code": row.region_code,
                "region_name": row.region_name or f"지역코드_{row.region_code}",
                "collected_at": row.collected_at.isoformat() if row.collected_at else None,
                "status": row.status
            }
            for row in collection_history
        ]

        # 실패 횟수 계산
        failed_collections = sum(1 for h in history_list if h["status"] == "failed")
        successful_collections = len(history_list) - failed_collections
        error_rate = round((failed_collections / len(history_list) * 100), 1) if history_list else 0

        return {
            "total_regions": total_regions or 0,
            "collected_regions": collected_regions or 0,
            "today_collection_count": today_collection_count or 0,
            "last_collection_time": last_collection_time.isoformat() if last_collection_time else None,
            "collection_history": history_list,
            "failed_collections": failed_collections,
            "successful_collections": successful_collections,
            "error_rate": error_rate,
            "next_collection_time": None  # 배치 스케줄러와 연동 필요
        }
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
    weather_forecast 테이블에서 날씨 통계 데이터를 제공합니다.
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
                   FIRST_VALUE(forecast_date) OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as latest_forecast_date,
                   FIRST_VALUE(created_at) OVER (PARTITION BY region_code ORDER BY forecast_date DESC, created_at DESC) as latest_created_at
            FROM weather_forecast 
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
                    "message": "weather_forecast 테이블에 최근 데이터가 없습니다."
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
                "last_updated": row.latest_created_at.isoformat() if row.latest_created_at else None
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
                "data_source": "weather_forecast"
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
    weather_forecast 테이블에서 지역별 최신 날씨 예보 데이터를 반환합니다.
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
                FROM weather_forecast 
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
                "data_source": "weather_forecast"
            })

        return {
            "success": True,
            "data": weather_data,
            "count": len(weather_data),
            "message": f"weather_forecast 테이블에서 {len(weather_data)}개 지역의 날씨 데이터를 조회했습니다."
        }

    except Exception as e:
        logger.error(f"Forecast weather data 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"예보 데이터 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/database/current-data")
def get_current_weather_data(
    limit: int = Query(20, description="반환할 데이터 수"),
    db: Session = Depends(get_db)
):
    """
    weather_current 테이블에서 지역별 최신 실시간 날씨 데이터를 반환합니다.
    습도, 풍속, 가시거리, UV지수 등 상세한 날씨 정보를 제공합니다.
    """
    try:
        # 지역별 최신 실시간 날씨 데이터 조회
        query = text("""
            WITH latest_current AS (
                SELECT DISTINCT region_code,
                       FIRST_VALUE(avg_temp::numeric) OVER (PARTITION BY region_code ORDER BY weather_date DESC, created_at DESC) as avg_temp,
                       FIRST_VALUE(max_temp::numeric) OVER (PARTITION BY region_code ORDER BY weather_date DESC, created_at DESC) as max_temp,
                       FIRST_VALUE(min_temp::numeric) OVER (PARTITION BY region_code ORDER BY weather_date DESC, created_at DESC) as min_temp,
                       FIRST_VALUE(humidity) OVER (PARTITION BY region_code ORDER BY weather_date DESC, created_at DESC) as humidity,
                       FIRST_VALUE(wind_speed) OVER (PARTITION BY region_code ORDER BY weather_date DESC, created_at DESC) as wind_speed,
                       FIRST_VALUE(visibility) OVER (PARTITION BY region_code ORDER BY weather_date DESC, created_at DESC) as visibility,
                       FIRST_VALUE(uv_index) OVER (PARTITION BY region_code ORDER BY weather_date DESC, created_at DESC) as uv_index,
                       FIRST_VALUE(precipitation) OVER (PARTITION BY region_code ORDER BY weather_date DESC, created_at DESC) as precipitation,
                       FIRST_VALUE(weather_condition) OVER (PARTITION BY region_code ORDER BY weather_date DESC, created_at DESC) as weather_condition,
                       FIRST_VALUE(weather_date) OVER (PARTITION BY region_code ORDER BY weather_date DESC, created_at DESC) as weather_date,
                       FIRST_VALUE(created_at) OVER (PARTITION BY region_code ORDER BY weather_date DESC, created_at DESC) as created_at,
                       ROW_NUMBER() OVER (PARTITION BY region_code ORDER BY weather_date DESC, created_at DESC) as rn
                FROM weather_current 
                WHERE avg_temp IS NOT NULL 
                AND weather_date >= CURRENT_DATE - INTERVAL '7 days'
            )
            SELECT lc.*, r.region_name, r.region_name_full
            FROM latest_current lc
            LEFT JOIN regions r ON lc.region_code = r.region_code
            WHERE lc.rn = 1
            ORDER BY lc.created_at DESC
            LIMIT :limit
        """)

        result = db.execute(query, {"limit": limit}).fetchall()

        if not result:
            return {
                "success": True,
                "data": [],
                "message": "weather_current 테이블에 최근 데이터가 없습니다."
            }

        # 응답 데이터 구성
        weather_data = []
        for row in result:
            city_name = row.region_name_full or row.region_name or f"지역코드_{row.region_code}"
            
            weather_data.append({
                "id": f"current_{row.region_code}",
                "city_name": city_name,
                "region_code": row.region_code,
                "temperature": round(float(row.avg_temp), 1) if row.avg_temp else None,
                "min_temp": float(row.min_temp) if row.min_temp else None,
                "max_temp": float(row.max_temp) if row.max_temp else None,
                "humidity": row.humidity,
                "wind_speed": row.wind_speed,
                "visibility": row.visibility,
                "uv_index": row.uv_index,
                "precipitation": row.precipitation,
                "weather_description": row.weather_condition,
                "weather_condition": row.weather_condition,
                "sky_condition": row.weather_condition,
                "weather_date": row.weather_date.isoformat() if row.weather_date else None,
                "last_updated": row.created_at.isoformat() if row.created_at else None,
                "data_source": "weather_current"
            })

        return {
            "success": True,
            "data": weather_data,
            "count": len(weather_data),
            "message": f"weather_current 테이블에서 {len(weather_data)}개 지역의 실시간 날씨 데이터를 조회했습니다."
        }

    except Exception as e:
        logger.error(f"Current weather data 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"실시간 날씨 데이터 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/update-empty-data")
async def update_empty_weather_data(
    db: Session = Depends(get_db)
):
    """
    빈 날씨 데이터를 api_raw_data에서 업데이트
    
    weather_current 테이블의 빈 필드(precipitation, visibility, uv_index 등)를
    api_raw_data 테이블에 저장된 이전 수집 데이터를 사용하여 업데이트합니다.
    """
    import json
    from datetime import datetime
    
    try:
        # 빈 필드가 있는 레코드 조회
        empty_records_query = text("""
            SELECT id, region_code, region_name, weather_date, 
                   avg_temp, max_temp, min_temp, humidity, 
                   precipitation, wind_speed, weather_condition,
                   visibility, uv_index
            FROM weather_current
            WHERE precipitation IS NULL
               OR visibility IS NULL
               OR uv_index IS NULL
            ORDER BY weather_date DESC, region_code
            LIMIT 100
        """)
        
        empty_records = db.execute(empty_records_query).fetchall()
        
        if not empty_records:
            return {
                "success": True,
                "message": "빈 필드가 있는 레코드가 없습니다.",
                "updated_count": 0
            }
        
        updated_count = 0
        failed_count = 0
        
        for record in empty_records:
            # api_raw_data에서 해당 날짜와 지역의 데이터 검색
            raw_data_query = text("""
                SELECT id, raw_response
                FROM api_raw_data
                WHERE api_provider = 'WEATHER'
                  AND response_status = 200
                  AND raw_response IS NOT NULL
                  AND created_at::date = :weather_date
                  AND (
                    request_params->>'region' = :region_name
                    OR request_params->>'city' = :region_name
                    OR raw_response::text LIKE :region_pattern
                  )
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            raw_data_results = db.execute(
                raw_data_query,
                {
                    'weather_date': record.weather_date,
                    'region_name': record.region_name,
                    'region_pattern': f'%{record.region_name}%'
                }
            ).fetchall()
            
            if not raw_data_results:
                continue
                
            # raw_response에서 날씨 데이터 추출
            weather_info = None
            api_raw_data_id = None
            
            for raw_data in raw_data_results:
                try:
                    response_data = raw_data.raw_response
                    
                    # API 응답 구조에 따라 파싱
                    if 'response' in response_data and 'body' in response_data['response']:
                        items = response_data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
                        if items:
                            item = items[0] if isinstance(items, list) else items
                            
                            weather_info = {}
                            # 강수량
                            if record.precipitation is None and 'rn1' in item:
                                weather_info['precipitation'] = float(item.get('rn1', 0))
                            
                            # 가시거리
                            if record.visibility is None and 'visibility' in item:
                                weather_info['visibility'] = float(item.get('visibility', 10000)) / 1000
                            
                            # UV 지수
                            if record.uv_index is None and 'uv' in item:
                                weather_info['uv_index'] = float(item.get('uv', 0))
                                
                            if weather_info:
                                api_raw_data_id = str(raw_data.id)
                                break
                                
                except Exception as e:
                    logger.warning(f"Failed to parse raw_response: {e}")
                    continue
            
            # 업데이트 수행
            if weather_info:
                update_fields = []
                params = {'id': record.id}
                
                if 'precipitation' in weather_info:
                    update_fields.append("precipitation = :precipitation")
                    params['precipitation'] = weather_info['precipitation']
                    
                if 'visibility' in weather_info:
                    update_fields.append("visibility = :visibility")
                    params['visibility'] = weather_info['visibility']
                    
                if 'uv_index' in weather_info:
                    update_fields.append("uv_index = :uv_index")
                    params['uv_index'] = weather_info['uv_index']
                    
                if api_raw_data_id:
                    update_fields.append("raw_data_id = :raw_data_id")
                    params['raw_data_id'] = api_raw_data_id
                    
                if update_fields:
                    update_fields.append("updated_at = :updated_at")
                    params['updated_at'] = datetime.now()
                    
                    update_query = text(f"""
                        UPDATE weather_current
                        SET {', '.join(update_fields)}
                        WHERE id = :id
                    """)
                    
                    db.execute(update_query, params)
                    updated_count += 1
                    
        db.commit()
        
        # 업데이트 후 상태 확인
        check_query = text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN precipitation IS NULL THEN 1 ELSE 0 END) as null_precipitation,
                SUM(CASE WHEN visibility IS NULL THEN 1 ELSE 0 END) as null_visibility,
                SUM(CASE WHEN uv_index IS NULL THEN 1 ELSE 0 END) as null_uv_index
            FROM weather_current
        """)
        
        result = db.execute(check_query).fetchone()
        
        return {
            "success": True,
            "message": "빈 날씨 데이터 업데이트가 완료되었습니다.",
            "processed_count": len(empty_records),
            "updated_count": updated_count,
            "current_status": {
                "total_records": result.total,
                "null_precipitation": result.null_precipitation,
                "null_visibility": result.null_visibility,
                "null_uv_index": result.null_uv_index
            }
        }
        
    except Exception as e:
        logger.error(f"Update empty weather data error: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"빈 데이터 업데이트 중 오류가 발생했습니다: {str(e)}")

