import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session
from ..database import get_db
from .service import KMAWeatherService
from .database_service import WeatherDatabaseService
from .models import WeatherInfo

logger = logging.getLogger(__name__)


class WeatherDataCollector:
    """날씨 데이터 수집 및 저장 클래스"""

    def __init__(self):
        self.weather_service = KMAWeatherService()

    async def collect_all_cities_weather(self, include_forecast: bool = False) -> Dict[str, Any]:
        """모든 주요 도시의 날씨 데이터를 수집하고 저장"""
        logger.info("Starting weather data collection for all cities")

        # 데이터베이스 세션 가져오기
        db_gen = get_db()
        db = next(db_gen)

        try:
            db_service = WeatherDatabaseService(db)
            cities = self.weather_service.get_major_cities()

            results = {
                "collected_at": datetime.now().isoformat(),
                "total_cities": len(cities),
                "success_count": 0,
                "failed_count": 0,
                "cities_data": [],
                "errors": []
            }

            # 병렬로 날씨 데이터 수집
            weather_data_list = await self._collect_weather_parallel(cities, include_forecast)

            # 성공한 데이터들을 데이터베이스에 저장
            successful_data = [data for data in weather_data_list if data is not None]

            if successful_data:
                saved_count = db_service.save_multiple_weather_data(successful_data)
                results["success_count"] = saved_count

                for weather_info in successful_data:
                    results["cities_data"].append({
                        "city": weather_info.location,
                        "temperature": weather_info.temperature,
                        "humidity": weather_info.humidity,
                        "weather_description": weather_info.weather_description,
                        "forecast_time": weather_info.forecast_time.isoformat()
                    })

            results["failed_count"] = len(cities) - len(successful_data)

            logger.info(f"Weather collection completed. Success: {results['success_count']}, Failed: {results['failed_count']}")
            return results

        except Exception as e:
            logger.error(f"Error in collect_all_cities_weather: {str(e)}")
            results["errors"].append(str(e))
            return results
        finally:
            db.close()

    async def collect_current_weather_only(self) -> Dict[str, Any]:
        """현재 날씨만 수집 (예보 제외)"""
        return await self.collect_all_cities_weather(include_forecast=False)

    async def _collect_weather_parallel(self, cities: List[Dict], include_forecast: bool) -> List[WeatherInfo]:
        """병렬로 날씨 데이터 수집"""
        weather_data_list = []

        # ThreadPoolExecutor를 사용하여 병렬 처리
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 각 도시에 대해 작업 제출
            future_to_city = {}

            for city in cities:
                if include_forecast:
                    # 예보 데이터 포함
                    future = executor.submit(self._get_city_forecast, city)
                else:
                    # 현재 날씨만
                    future = executor.submit(self._get_city_current_weather, city)
                future_to_city[future] = city

            # 완료된 작업들 처리
            for future in as_completed(future_to_city):
                city = future_to_city[future]
                try:
                    weather_info = future.result()
                    if weather_info:
                        weather_data_list.append(weather_info)
                        logger.info(f"Successfully collected weather data for {city['name']}")
                    else:
                        logger.warning(f"No weather data received for {city['name']}")
                except Exception as e:
                    logger.error(f"Error collecting weather data for {city['name']}: {str(e)}")

        return weather_data_list

    def _get_city_current_weather(self, city: Dict) -> WeatherInfo:
        """특정 도시의 현재 날씨 조회"""
        try:
            return self.weather_service.get_current_weather_by_city(city["name"])
        except Exception as e:
            logger.error(f"Error getting current weather for {city['name']}: {str(e)}")
            return None

    def _get_city_forecast(self, city: Dict) -> WeatherInfo:
        """특정 도시의 예보 날씨 조회 (필요시 구현)"""
        try:
            # 현재는 현재 날씨만 반환 (나중에 예보 기능 추가 가능)
            return self.weather_service.get_current_weather_by_city(city["name"])
        except Exception as e:
            logger.error(f"Error getting forecast for {city['name']}: {str(e)}")
            return None

    async def get_collection_stats(self) -> Dict[str, Any]:
        """수집 통계 조회"""
        db_gen = get_db()
        db = next(db_gen)

        try:
            db_service = WeatherDatabaseService(db)
            stats = db_service.get_weather_statistics()

            return {
                "database_stats": stats,
                "last_collection": datetime.now().isoformat(),
                "available_cities": [city["name"] for city in self.weather_service.get_major_cities()]
            }
        finally:
            db.close()


# 전역 인스턴스
weather_collector = WeatherDataCollector()
