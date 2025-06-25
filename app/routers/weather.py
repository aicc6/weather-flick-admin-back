from fastapi import APIRouter, Depends
from typing import Dict, List
from ..services.weather_service import WeatherService
from .. import auth

router = APIRouter()
weather_service = WeatherService()


@router.get("/current")
def get_current_weather(
    current_admin = Depends(auth.get_current_active_admin)
) -> Dict:
    """
    주요 도시들의 현재 날씨 정보를 반환합니다.
    """
    return weather_service.get_current_weather_summary()


@router.get("/forecast/{region_code}")
def get_weather_forecast(
    region_code: str,
    current_admin = Depends(auth.get_current_active_admin)
) -> List[Dict]:
    """
    특정 지역의 날씨 예보를 반환합니다.

    Args:
        region_code: 지역코드 (108: 서울, 159: 부산, 143: 대구, 184: 제주)
    """
    return weather_service.get_weather_forecast(region_code)


@router.get("/regions")
def get_available_regions(
    current_admin = Depends(auth.get_current_active_admin)
) -> Dict:
    """
    사용 가능한 지역 정보를 반환합니다.
    """
    return {
        "regions": [
            {"code": "108", "name": "서울"},
            {"code": "159", "name": "부산"},
            {"code": "143", "name": "대구"},
            {"code": "184", "name": "제주"}
        ]
    }
