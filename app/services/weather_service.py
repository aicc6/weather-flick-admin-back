import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.base_url = "https://apihub.kma.go.kr/api/typ01/url/fct_afs_do.php"
        self.auth_key = "FouhOAZzSeeLoTgGcynndA"  # 실제 운영에서는 환경변수로 관리

    def get_weather_forecast(self, region_code: str = "108") -> List[Dict]:
        """
        기상청 단기예보 API에서 날씨 데이터를 가져옵니다.

        Args:
            region_code: 지역코드 (108: 서울, 159: 부산, 143: 대구, 184: 제주)

        Returns:
            List[Dict]: 날씨 예보 데이터 리스트
        """
        try:
            # 현재 시간 기준으로 예보 시간 설정
            now = datetime.now()
            tmfc1 = now.strftime("%Y%m%d%H")
            tmfc2 = (now + timedelta(hours=12)).strftime("%Y%m%d%H")

            params = {
                'reg': region_code,
                'tmfc1': tmfc1,
                'tmfc2': tmfc2,
                'disp': '0',
                'help': '1',
                'authKey': self.auth_key
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            # 응답 데이터 파싱
            weather_data = self._parse_weather_data(response.text, region_code)
            return weather_data

        except requests.RequestException as e:
            logger.error(f"Weather API request failed: {e}")
            return self._get_mock_weather_data(region_code)
        except Exception as e:
            logger.error(f"Weather data parsing failed: {e}")
            return self._get_mock_weather_data(region_code)

    def _parse_weather_data(self, raw_data: str, region_code: str) -> List[Dict]:
        """
        기상청 API 응답 데이터를 파싱합니다.
        """
        weather_data = []

        # 데이터 라인들을 파싱
        lines = raw_data.strip().split('\n')

        for line in lines:
            if line.startswith('#') or not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 17:
                try:
                    weather_info = {
                        'region_id': parts[0],
                        'forecast_time': parts[1],
                        'effective_time': parts[2],
                        'model': parts[3],
                        'sequence': parts[4],
                        'station': parts[5],
                        'category': parts[6],
                        'manager_id': parts[7],
                        'manager_forecast': parts[8],
                        'wind_direction1': parts[9],
                        'wind_type': parts[10],
                        'wind_direction2': parts[11],
                        'wind_speed1': parts[12],
                        'wind_speed2': parts[13],
                        'humidity1': parts[14],
                        'humidity2': parts[15],
                        'sky_condition': parts[16],
                        'precipitation': parts[17] if len(parts) > 17 else '0',
                        'weather_description': parts[18] if len(parts) > 18 else ''
                    }

                    # 온도 정보 추출 (TA 필드가 있는 경우)
                    if len(parts) > 19:
                        weather_info['temperature'] = parts[19]
                    else:
                        weather_info['temperature'] = 'N/A'

                    weather_data.append(weather_info)

                except (IndexError, ValueError) as e:
                    logger.warning(f"Failed to parse weather line: {line}, Error: {e}")
                    continue

        return weather_data

    def _get_mock_weather_data(self, region_code: str) -> List[Dict]:
        """
        API 실패 시 사용할 목업 데이터를 반환합니다.
        """
        region_names = {
            '108': '서울',
            '159': '부산',
            '143': '대구',
            '184': '제주'
        }

        region_name = region_names.get(region_code, '서울')

        return [
            {
                'region_id': region_code,
                'region_name': region_name,
                'forecast_time': datetime.now().strftime("%Y%m%d%H%M"),
                'temperature': '23',
                'sky_condition': 'DB01',
                'sky_description': '맑음',
                'precipitation': '0',
                'weather_description': '맑음',
                'wind_direction': 'NW',
                'wind_speed': '12',
                'humidity': '65'
            }
        ]

    def get_current_weather_summary(self) -> Dict:
        """
        주요 도시들의 현재 날씨 요약을 반환합니다.
        """
        regions = ['108', '159', '143', '184']  # 서울, 부산, 대구, 제주
        weather_summary = {}

        for region_code in regions:
            weather_data = self.get_weather_forecast(region_code)
            if weather_data:
                latest_weather = weather_data[0]  # 가장 최근 예보

                region_names = {
                    '108': '서울',
                    '159': '부산',
                    '143': '대구',
                    '184': '제주'
                }

                weather_summary[region_code] = {
                    'region_name': region_names.get(region_code, '알 수 없음'),
                    'temperature': latest_weather.get('temperature', 'N/A'),
                    'sky_condition': latest_weather.get('sky_condition', 'N/A'),
                    'weather_description': latest_weather.get('weather_description', '알 수 없음'),
                    'wind_speed': latest_weather.get('wind_speed1', 'N/A'),
                    'humidity': latest_weather.get('humidity1', 'N/A'),
                    'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

        return weather_summary
