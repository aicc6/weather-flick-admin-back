from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from sqlalchemy.orm import Session

from ..services.weather_service import get_weather_service, KTOWeatherService, MAJOR_CITIES
from ..weather.models import (
    WeatherInfo, LocationCoordinate,
    UltraSrtNcstRequest, UltraSrtFcstRequest, VilageFcstRequest,
    WeatherResponse
)
from ..services.weather_database_service import WeatherDatabaseService
from ..weather.scheduler import weather_collector
from ..database import get_db
from ..models import WeatherData

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

@router.get("/database/stats")
async def get_database_stats(db: Session = Depends(get_db)):
    """
    저장된 날씨 데이터 통계 조회
    """
    try:
        db_service = WeatherDatabaseService(db)
        stats = db_service.get_weather_statistics()
        return stats
    except Exception as e:
        logger.error(f"Database stats error: {e}")
        raise HTTPException(status_code=500, detail="통계 조회 중 오류가 발생했습니다.")


@router.get("/database/data")
async def get_stored_weather_data(
    city_name: Optional[str] = Query(None, description="특정 도시 데이터만 조회"),
    limit: int = Query(100, description="조회할 레코드 수"),
    db: Session = Depends(get_db)
):
    """
    저장된 날씨 데이터 조회
    """
    try:
        db_service = WeatherDatabaseService(db)
        data = db_service.get_latest_weather_data(city_name, limit)

        return {
            "total_records": len(data),
            "city_filter": city_name,
            "data": [
                {
                    "id": str(record.id),
                    "city_name": record.city_name,
                    "temperature": record.temperature,
                    "humidity": record.humidity,
                    "precipitation": record.precipitation,
                    "wind_speed": record.wind_speed,
                    "sky_condition": record.sky_condition,
                    "weather_description": record.weather_description,
                    "forecast_time": record.forecast_time.isoformat() if record.forecast_time else None,
                    "created_at": record.created_at.isoformat() if record.created_at else None
                }
                for record in data
            ]
        }
    except Exception as e:
        logger.error(f"Get stored data error: {e}")
        raise HTTPException(status_code=500, detail="데이터 조회 중 오류가 발생했습니다.")


@router.get("/database/latest/{city_name}")
async def get_latest_city_weather(
    city_name: str,
    db: Session = Depends(get_db)
):
    """
    특정 도시의 최신 날씨 데이터 조회
    """
    try:
        db_service = WeatherDatabaseService(db)
        data = db_service.get_weather_by_city(city_name)

        if not data:
            raise HTTPException(status_code=404, detail=f"{city_name}의 저장된 데이터를 찾을 수 없습니다.")

        return {
            "id": str(data.id),
            "city_name": data.city_name,
            "temperature": data.temperature,
            "humidity": data.humidity,
            "precipitation": data.precipitation,
            "wind_speed": data.wind_speed,
            "wind_direction": data.wind_direction,
            "sky_condition": data.sky_condition,
            "precipitation_type": data.precipitation_type,
            "weather_description": data.weather_description,
            "forecast_time": data.forecast_time.isoformat() if data.forecast_time else None,
            "coordinates": {
                "nx": data.nx,
                "ny": data.ny,
                "latitude": float(data.latitude) if data.latitude else None,
                "longitude": float(data.longitude) if data.longitude else None
            },
            "created_at": data.created_at.isoformat() if data.created_at else None,
            "updated_at": data.updated_at.isoformat() if data.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get latest city weather error: {e}")
        raise HTTPException(status_code=500, detail="데이터 조회 중 오류가 발생했습니다.")


@router.post("/database/cleanup")
async def cleanup_database(db: Session = Depends(get_db)):
    """
    데이터베이스 정리 (1000개 제한 적용)
    """
    try:
        db_service = WeatherDatabaseService(db)
        remaining_count = db_service.cleanup_old_data_manual()

        return {
            "message": "데이터베이스 정리 완료",
            "remaining_records": remaining_count,
            "max_records": WeatherDatabaseService.MAX_RECORDS
        }
    except Exception as e:
        logger.error(f"Database cleanup error: {e}")
        raise HTTPException(status_code=500, detail="데이터베이스 정리 중 오류가 발생했습니다.")


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


@router.delete("/database/city/{city_name}")
async def delete_city_data(
    city_name: str,
    db: Session = Depends(get_db)
):
    """
    특정 도시의 모든 데이터 삭제
    """
    try:
        db_service = WeatherDatabaseService(db)
        deleted_count = db_service.delete_city_data(city_name)

        return {
            "message": f"{city_name} 데이터 삭제 완료",
            "deleted_records": deleted_count
        }
    except Exception as e:
        logger.error(f"Delete city data error: {e}")
        raise HTTPException(status_code=500, detail="데이터 삭제 중 오류가 발생했습니다.")


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


@router.get("/summary-db")
def get_weather_summary_db(db: Session = Depends(get_db)):
    """
    데이터베이스에 저장된 주요 도시들의 최신 날씨 요약 및 통계 반환
    """
    try:
        from ..services.weather_service import MAJOR_CITIES
        from ..services.weather_database_service import WeatherDatabaseService

        db_service = WeatherDatabaseService(db)
        cities = list(MAJOR_CITIES.keys())

        # 단일 쿼리로 모든 도시의 최신 데이터 조회 (성능 개선)
        latest_weather_data = db_service.get_latest_weather_data(limit=len(cities) * 2)

        # 도시별 최신 데이터 매핑
        city_data_map = {}
        for data in latest_weather_data:
            if data.city_name in cities and data.city_name not in city_data_map:
                city_data_map[data.city_name] = data

        regions = []
        temps = []
        now = None

        # 데이터가 없는 경우 기본 응답 제공
        if not latest_weather_data:
            logger.warning("데이터베이스에 저장된 날씨 데이터가 없습니다.")
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
                    "message": "저장된 날씨 데이터가 없습니다. 데이터 수집을 먼저 실행해주세요."
                }
            }

        for city_name in cities:
            data = city_data_map.get(city_name)
            if data and data.temperature is not None:
                temp = float(data.temperature)
                temps.append(temp)
                regions.append({
                    "city_name": city_name,
                    "region_code": getattr(data, 'region_code', None),
                    "temperature": temp,
                    "humidity": data.humidity,
                    "wind_speed": data.wind_speed,
                    "sky_condition": data.sky_condition,
                    "last_updated": data.forecast_time.isoformat() if data.forecast_time else None
                })
                if not now or (data.forecast_time and data.forecast_time > now):
                    now = data.forecast_time

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
    except Exception as e:
        logger.error(f"Weather summary-db 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"날씨 요약 데이터 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/collect-sample-data")
async def collect_sample_weather_data(
    db: Session = Depends(get_db),
    weather_service: KTOWeatherService = Depends(get_weather_service)
):
    """
    샘플 날씨 데이터 수집 (테스트용)
    주요 도시 3개의 현재 날씨를 수집하여 DB에 저장
    """
    try:
        from ..services.weather_database_service import WeatherDatabaseService
        from ..services.weather_service import MAJOR_CITIES

        db_service = WeatherDatabaseService(db)

        # 테스트용으로 3개 도시만 수집
        test_cities = ['서울', '부산', '대구']
        collected_data = []

        for city_name in test_cities:
            try:
                if city_name in MAJOR_CITIES:
                    coordinate = MAJOR_CITIES[city_name]
                    weather = weather_service.get_current_weather(coordinate.nx, coordinate.ny, coordinate.name)

                    if weather:
                        saved_data = db_service.save_weather_data(weather)
                        if saved_data:
                            collected_data.append({
                                "city": city_name,
                                "temperature": weather.temperature,
                                "status": "success"
                            })
                        else:
                            collected_data.append({
                                "city": city_name,
                                "status": "failed_to_save"
                            })
                    else:
                        collected_data.append({
                            "city": city_name,
                            "status": "no_weather_data"
                        })
            except Exception as e:
                logger.error(f"{city_name} 데이터 수집 실패: {e}")
                collected_data.append({
                    "city": city_name,
                    "status": f"error: {str(e)}"
                })

        return {
            "message": "샘플 데이터 수집 완료",
            "collected_count": len([d for d in collected_data if d.get("status") == "success"]),
            "total_attempted": len(test_cities),
            "details": collected_data
        }

    except Exception as e:
        logger.error(f"샘플 데이터 수집 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"데이터 수집 중 오류가 발생했습니다: {str(e)}")


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
