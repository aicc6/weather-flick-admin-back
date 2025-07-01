from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime
import logging

from .service import get_weather_service, KMAWeatherService, MAJOR_CITIES
from .models import (
    WeatherInfo, LocationCoordinate,
    UltraSrtNcstRequest, UltraSrtFcstRequest, VilageFcstRequest,
    WeatherResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("/current", response_model=WeatherInfo)
async def get_current_weather(
    nx: int = Query(..., description="예보지점 X 좌표"),
    ny: int = Query(..., description="예보지점 Y 좌표"),
    location: str = Query("", description="지역명"),
    weather_service: KMAWeatherService = Depends(get_weather_service)
):
    """
    현재 날씨 정보 조회 (초단기실황)

    - **nx**: 기상청 격자 X 좌표
    - **ny**: 기상청 격자 Y 좌표
    - **location**: 지역명 (선택사항)
    """
    try:
        weather = weather_service.get_current_weather(nx, ny, location)
        if not weather:
            raise HTTPException(status_code=404, detail="날씨 정보를 찾을 수 없습니다.")

        return weather

    except Exception as e:
        logger.error(f"현재 날씨 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="날씨 정보 조회 중 오류가 발생했습니다.")


@router.get("/forecast", response_model=List[WeatherInfo])
async def get_weather_forecast(
    nx: int = Query(..., description="예보지점 X 좌표"),
    ny: int = Query(..., description="예보지점 Y 좌표"),
    location: str = Query("", description="지역명"),
    weather_service: KMAWeatherService = Depends(get_weather_service)
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
    weather_service: KMAWeatherService = Depends(get_weather_service)
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
    weather_service: KMAWeatherService = Depends(get_weather_service)
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
    weather_service: KMAWeatherService = Depends(get_weather_service)
):
    """
    초단기실황 조회 (Raw API)

    기상청 API를 직접 호출하여 원본 응답을 반환합니다.
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
    weather_service: KMAWeatherService = Depends(get_weather_service)
):
    """
    초단기예보 조회 (Raw API)

    기상청 API를 직접 호출하여 원본 응답을 반환합니다.
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
    weather_service: KMAWeatherService = Depends(get_weather_service)
):
    """
    단기예보 조회 (Raw API)

    기상청 API를 직접 호출하여 원본 응답을 반환합니다.
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
async def weather_health_check():
    """
    날씨 API 헬스체크
    """
    return {
        "status": "healthy",
        "service": "weather",
        "timestamp": datetime.now().isoformat(),
        "available_cities": len(MAJOR_CITIES)
    }
