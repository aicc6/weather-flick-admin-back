from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..models import CityWeatherData
from ..database import get_db
from ..weather.models import WeatherInfo, LocationCoordinate


logger = logging.getLogger(__name__)


class WeatherDatabaseService:
    """날씨 데이터 데이터베이스 서비스"""

    MAX_RECORDS = 1000  # 최대 저장할 레코드 수

    def __init__(self, db: Session):
        self.db = db

    def save_weather_data(self, weather_info: WeatherInfo) -> Optional[CityWeatherData]:
        """날씨 데이터를 데이터베이스에 저장"""
        try:
            # 기존 데이터 확인 (도시명 + 예보시각으로)
            existing = self.db.query(CityWeatherData).filter(
                and_(
                    CityWeatherData.city_name == weather_info.location,
                    CityWeatherData.forecast_time == weather_info.forecast_time
                )
            ).first()

            if existing:
                # 기존 데이터 업데이트
                existing.temperature = weather_info.temperature
                existing.humidity = weather_info.humidity
                existing.precipitation = weather_info.precipitation
                existing.wind_speed = weather_info.wind_speed
                existing.wind_direction = weather_info.wind_direction
                existing.sky_condition = weather_info.sky_condition
                existing.precipitation_type = weather_info.precipitation_type
                existing.weather_description = weather_info.weather_description
                existing.updated_at = datetime.now()

                self.db.commit()
                logger.info(f"Updated weather data for {weather_info.location}")
                return existing
            else:
                # 새 데이터 생성
                weather_data = CityWeatherData(
                    city_name=weather_info.location,
                    nx=weather_info.nx,
                    ny=weather_info.ny,
                    temperature=weather_info.temperature,
                    humidity=weather_info.humidity,
                    precipitation=weather_info.precipitation,
                    wind_speed=weather_info.wind_speed,
                    wind_direction=weather_info.wind_direction,
                    sky_condition=weather_info.sky_condition,
                    precipitation_type=weather_info.precipitation_type,
                    weather_description=weather_info.weather_description,
                    forecast_time=weather_info.forecast_time,
                    base_date=weather_info.forecast_time.strftime("%Y%m%d"),
                    base_time=weather_info.forecast_time.strftime("%H%M")
                )

                self.db.add(weather_data)
                self.db.commit()
                self.db.refresh(weather_data)

                logger.info(f"Saved new weather data for {weather_info.location}")
                return weather_data

        except Exception as e:
            logger.error(f"Error saving weather data for {weather_info.location}: {str(e)}")
            self.db.rollback()
            return None

    def save_multiple_weather_data(self, weather_data_list: List[WeatherInfo]) -> int:
        """여러 도시의 날씨 데이터를 일괄 저장"""
        saved_count = 0

        for weather_info in weather_data_list:
            if self.save_weather_data(weather_info):
                saved_count += 1

        # 데이터 개수 제한 확인 및 정리
        self._cleanup_old_data()

        return saved_count

    def get_latest_weather_data(self, city_name: Optional[str] = None, limit: int = 100) -> List[CityWeatherData]:
        """최신 날씨 데이터 조회"""
        try:
            query = self.db.query(CityWeatherData)

            if city_name:
                query = query.filter(CityWeatherData.city_name == city_name)

            return query.order_by(desc(CityWeatherData.forecast_time)).limit(limit).all()
        except Exception as e:
            logger.error(f"최신 날씨 데이터 조회 실패: {e}")
            self.db.rollback()
            return []

    def get_weather_by_city(self, city_name: str) -> Optional[CityWeatherData]:
        """특정 도시의 최신 날씨 데이터 조회"""
        try:
            return self.db.query(CityWeatherData).filter(
                CityWeatherData.city_name == city_name
            ).order_by(desc(CityWeatherData.forecast_time)).first()
        except Exception as e:
            logger.error(f"도시별 날씨 데이터 조회 실패 ({city_name}): {e}")
            self.db.rollback()
            return None

    def get_weather_statistics(self) -> Dict[str, Any]:
        """날씨 데이터 통계 조회"""
        total_count = self.db.query(CityWeatherData).count()

        # 도시별 데이터 개수
        city_counts = dict(
            self.db.query(
                CityWeatherData.city_name,
                func.count(CityWeatherData.id)
            ).group_by(CityWeatherData.city_name).all()
        )

        # 최신 데이터 시간
        latest_time = self.db.query(
            func.max(CityWeatherData.forecast_time)
        ).scalar()

        # 오래된 데이터 시간
        oldest_time = self.db.query(
            func.min(CityWeatherData.forecast_time)
        ).scalar()

        return {
            "total_records": total_count,
            "cities": list(city_counts.keys()),
            "city_counts": city_counts,
            "latest_forecast_time": latest_time,
            "oldest_forecast_time": oldest_time,
            "max_allowed_records": self.MAX_RECORDS
        }

    def _cleanup_old_data(self):
        """1000개 제한을 넘으면 오래된 데이터 삭제"""
        total_count = self.db.query(CityWeatherData).count()

        if total_count > self.MAX_RECORDS:
            # 삭제할 개수 계산
            delete_count = total_count - self.MAX_RECORDS

            # 가장 오래된 데이터들의 ID 조회
            old_data_ids = self.db.query(CityWeatherData.id).order_by(
                CityWeatherData.forecast_time.asc()
            ).limit(delete_count).all()

            # 해당 데이터들 삭제
            if old_data_ids:
                ids_to_delete = [row.id for row in old_data_ids]
                deleted_count = self.db.query(CityWeatherData).filter(
                    CityWeatherData.id.in_(ids_to_delete)
                ).delete(synchronize_session=False)

                self.db.commit()
                logger.info(f"Cleaned up {deleted_count} old weather records. Total records: {total_count - deleted_count}")

    def cleanup_old_data_manual(self) -> int:
        """수동으로 오래된 데이터 정리"""
        self._cleanup_old_data()
        return self.db.query(CityWeatherData).count()

    def delete_city_data(self, city_name: str) -> int:
        """특정 도시의 모든 데이터 삭제"""
        deleted_count = self.db.query(CityWeatherData).filter(
            CityWeatherData.city_name == city_name
        ).delete()

        self.db.commit()
        logger.info(f"Deleted {deleted_count} records for city: {city_name}")
        return deleted_count