import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import unquote
from app.config import settings
from .models import (
    WeatherResponse, WeatherInfo, LocationCoordinate,
    UltraSrtNcstRequest, UltraSrtFcstRequest, VilageFcstRequest
)

logger = logging.getLogger(__name__)


class KMAWeatherService:
    """기상청 단기예보 API 서비스"""

    def __init__(self):
        # API 키 URL 디코딩
        self.api_key = unquote(settings.kma_api_key) if settings.kma_api_key else ""
        self.base_url = settings.kma_forecast_url

        logger.info(f"KMA API 키 길이: {len(self.api_key)}")
        logger.info(f"KMA API URL: {self.base_url}")

        # 기상청 자료구분코드 매핑
        self.category_mapping = {
            # 초단기실황
            "T1H": "기온",          # 온도 (°C)
            "RN1": "1시간 강수량",   # 강수량 (mm)
            "UUU": "동서바람성분",   # 풍속 동서성분 (m/s)
            "VVV": "남북바람성분",   # 풍속 남북성분 (m/s)
            "REH": "습도",          # 습도 (%)
            "PTY": "강수형태",      # 강수형태 (코드값)
            "VEC": "풍향",          # 풍향 (deg)
            "WSD": "풍속",          # 풍속 (m/s)

            # 초단기예보
            "LGT": "낙뢰",          # 낙뢰 (kA)

            # 단기예보
            "POP": "강수확률",      # 강수확률 (%)
            "PCP": "1시간 강수량",   # 1시간 강수량 (mm)
            "REH": "습도",          # 습도 (%)
            "SNO": "1시간 신적설",   # 1시간 신적설 (cm)
            "SKY": "하늘상태",      # 하늘상태 (코드값)
            "TMP": "1시간 기온",     # 1시간 기온 (°C)
            "TMN": "일 최저기온",    # 일 최저기온 (°C)
            "TMX": "일 최고기온",    # 일 최고기온 (°C)
            "UUU": "풍속(동서성분)", # 풍속 동서성분 (m/s)
            "VVV": "풍속(남북성분)", # 풍속 남북성분 (m/s)
            "WAV": "파고",          # 파고 (M)
            "VEC": "풍향",          # 풍향 (deg)
            "WSD": "풍속",          # 풍속 (m/s)
        }

        # 강수형태 코드 매핑
        self.precipitation_type_mapping = {
            "0": "없음",
            "1": "비",
            "2": "비/눈",
            "3": "눈",
            "5": "빗방울",
            "6": "빗방울눈날림",
            "7": "눈날림"
        }

        # 하늘상태 코드 매핑
        self.sky_condition_mapping = {
            "1": "맑음",
            "3": "구름많음",
            "4": "흐림"
        }

    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """API 요청 실행"""
        try:
            params["serviceKey"] = self.api_key
            url = f"{self.base_url}/{endpoint}"

            logger.info(f"KMA API 요청: {url}")
            logger.info(f"파라미터: {params}")

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"KMA API 요청 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"KMA API 응답 파싱 실패: {e}")
            return None

    def get_ultra_srt_ncst(self, request: UltraSrtNcstRequest) -> Optional[WeatherResponse]:
        """초단기실황 조회"""
        params = {
            "pageNo": request.page_no,
            "numOfRows": request.num_of_rows,
            "dataType": request.data_type,
            "base_date": request.base_date,
            "base_time": request.base_time,
            "nx": request.nx,
            "ny": request.ny
        }

        response_data = self._make_request("getUltraSrtNcst", params)
        if response_data:
            try:
                return WeatherResponse(**response_data)
            except Exception as e:
                logger.error(f"초단기실황 응답 파싱 실패: {e}")
                return None
        return None

    def get_ultra_srt_fcst(self, request: UltraSrtFcstRequest) -> Optional[WeatherResponse]:
        """초단기예보 조회"""
        params = {
            "pageNo": request.page_no,
            "numOfRows": request.num_of_rows,
            "dataType": request.data_type,
            "base_date": request.base_date,
            "base_time": request.base_time,
            "nx": request.nx,
            "ny": request.ny
        }

        response_data = self._make_request("getUltraSrtFcst", params)
        if response_data:
            try:
                return WeatherResponse(**response_data)
            except Exception as e:
                logger.error(f"초단기예보 응답 파싱 실패: {e}")
                return None
        return None

    def get_vilage_fcst(self, request: VilageFcstRequest) -> Optional[WeatherResponse]:
        """단기예보 조회"""
        params = {
            "pageNo": request.page_no,
            "numOfRows": request.num_of_rows,
            "dataType": request.data_type,
            "base_date": request.base_date,
            "base_time": request.base_time,
            "nx": request.nx,
            "ny": request.ny
        }

        response_data = self._make_request("getVilageFcst", params)
        if response_data:
            try:
                return WeatherResponse(**response_data)
            except Exception as e:
                logger.error(f"단기예보 응답 파싱 실패: {e}")
                return None
        return None

    def _get_current_base_time(self) -> tuple[str, str]:
        """현재 시각에 맞는 발표시각 계산"""
        now = datetime.now()

        # 기상청 발표시각 (매시 30분에 발표, 10분 딜레이 고려)
        # 현재 시간이 40분 이전이면 이전 시간 기준
        if now.minute < 40:
            base_time = now - timedelta(hours=1)
        else:
            base_time = now

        base_date = base_time.strftime("%Y%m%d")
        base_time_str = base_time.strftime("%H00")  # 정시로 설정

        return base_date, base_time_str

    def get_current_weather(self, nx: int, ny: int, location_name: str = "") -> Optional[WeatherInfo]:
        """현재 날씨 정보 조회 (초단기실황)"""
        base_date, base_time = self._get_current_base_time()

        request = UltraSrtNcstRequest(
            base_date=base_date,
            base_time=base_time,
            nx=nx,
            ny=ny
        )

        response = self.get_ultra_srt_ncst(request)
        if not response or response.response.header.resultCode != "00":
            logger.error(f"초단기실황 조회 실패: {response.response.header.resultMsg if response else '응답 없음'}")
            return None

        weather_list = self._parse_weather_info(response, location_name, "current")
        return weather_list[0] if weather_list else None

    def get_weather_forecast(self, nx: int, ny: int, location_name: str = "") -> List[WeatherInfo]:
        """날씨 예보 정보 조회 (초단기예보 + 단기예보)"""
        weather_list = []

        # 초단기예보 (6시간)
        base_date, base_time = self._get_current_base_time()
        ultra_request = UltraSrtFcstRequest(
            base_date=base_date,
            base_time=base_time,
            nx=nx,
            ny=ny
        )

        ultra_response = self.get_ultra_srt_fcst(ultra_request)
        if ultra_response and ultra_response.response.header.resultCode == "00":
            ultra_weather = self._parse_weather_info(ultra_response, location_name, "ultra_forecast")
            if ultra_weather:
                weather_list.extend(ultra_weather)

        # 단기예보 (3일)
        # 단기예보는 02, 05, 08, 11, 14, 17, 20, 23시에 발표
        forecast_times = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
        current_hour = int(base_time)

        # 가장 최근 발표시각 찾기
        latest_time = "2300"  # 기본값
        for time in forecast_times:
            if int(time[:2]) <= current_hour:
                latest_time = time
            else:
                break

        vilage_request = VilageFcstRequest(
            base_date=base_date,
            base_time=latest_time,
            nx=nx,
            ny=ny
        )

        vilage_response = self.get_vilage_fcst(vilage_request)
        if vilage_response and vilage_response.response.header.resultCode == "00":
            vilage_weather = self._parse_weather_info(vilage_response, location_name, "short_forecast")
            if vilage_weather:
                weather_list.extend(vilage_weather)

        return weather_list

    def _parse_weather_info(self, response: WeatherResponse, location_name: str, forecast_type: str) -> List[WeatherInfo]:
        """API 응답을 WeatherInfo 객체로 변환"""
        weather_list = []
        items = response.response.body.items.item

        if not items:
            return weather_list

        # 시간별로 그룹화
        time_groups = {}

        for item in items:
            if forecast_type == "current":
                # 초단기실황
                time_key = f"{item.baseDate}_{item.baseTime}"
                if time_key not in time_groups:
                    time_groups[time_key] = {
                        "base_date": item.baseDate,
                        "base_time": item.baseTime,
                        "nx": item.nx,
                        "ny": item.ny,
                        "data": {}
                    }
                time_groups[time_key]["data"][item.category] = item.obsrValue
            else:
                # 예보
                time_key = f"{item.fcstDate}_{item.fcstTime}"
                if time_key not in time_groups:
                    time_groups[time_key] = {
                        "fcst_date": item.fcstDate,
                        "fcst_time": item.fcstTime,
                        "nx": item.nx,
                        "ny": item.ny,
                        "data": {}
                    }
                time_groups[time_key]["data"][item.category] = item.fcstValue

        # WeatherInfo 객체 생성
        for time_key, group in time_groups.items():
            try:
                if forecast_type == "current":
                    forecast_time = datetime.strptime(
                        f"{group['base_date']} {group['base_time']}",
                        "%Y%m%d %H%M"
                    )
                else:
                    forecast_time = datetime.strptime(
                        f"{group['fcst_date']} {group['fcst_time']}",
                        "%Y%m%d %H%M"
                    )

                weather_info = WeatherInfo(
                    location=location_name,
                    nx=group["nx"],
                    ny=group["ny"],
                    forecast_time=forecast_time
                )

                # 데이터 매핑
                data = group["data"]

                # 기온
                if "T1H" in data:
                    weather_info.temperature = float(data["T1H"])
                elif "TMP" in data:
                    weather_info.temperature = float(data["TMP"])

                # 습도
                if "REH" in data:
                    weather_info.humidity = int(float(data["REH"]))

                # 강수량
                if "RN1" in data and data["RN1"] != "강수없음":
                    try:
                        weather_info.precipitation = float(data["RN1"])
                    except:
                        weather_info.precipitation = 0.0
                elif "PCP" in data and data["PCP"] != "강수없음":
                    try:
                        weather_info.precipitation = float(data["PCP"])
                    except:
                        weather_info.precipitation = 0.0

                # 풍속
                if "WSD" in data:
                    weather_info.wind_speed = float(data["WSD"])

                # 풍향
                if "VEC" in data:
                    weather_info.wind_direction = int(float(data["VEC"]))

                # 강수형태
                if "PTY" in data:
                    pty_code = data["PTY"]
                    weather_info.precipitation_type = self.precipitation_type_mapping.get(pty_code, "알 수 없음")

                # 하늘상태
                if "SKY" in data:
                    sky_code = data["SKY"]
                    weather_info.sky_condition = self.sky_condition_mapping.get(sky_code, "알 수 없음")

                # 날씨 설명 생성
                weather_info.weather_description = self._generate_weather_description(weather_info)

                weather_list.append(weather_info)

            except Exception as e:
                logger.error(f"날씨 정보 파싱 실패: {e}")
                continue

        return sorted(weather_list, key=lambda x: x.forecast_time)

    def _generate_weather_description(self, weather: WeatherInfo) -> str:
        """날씨 설명 생성"""
        description_parts = []

        if weather.temperature is not None:
            description_parts.append(f"기온 {weather.temperature}°C")

        if weather.sky_condition:
            description_parts.append(weather.sky_condition)

        if weather.precipitation_type and weather.precipitation_type != "없음":
            description_parts.append(weather.precipitation_type)

        if weather.precipitation is not None and weather.precipitation > 0:
            description_parts.append(f"강수량 {weather.precipitation}mm")

        if weather.humidity is not None:
            description_parts.append(f"습도 {weather.humidity}%")

        if weather.wind_speed is not None:
            description_parts.append(f"풍속 {weather.wind_speed}m/s")

        return ", ".join(description_parts) if description_parts else "날씨 정보 없음"


# 주요 도시 좌표 (기상청 격자 좌표)
MAJOR_CITIES = {
    "서울": LocationCoordinate(name="서울", nx=60, ny=127, lat=37.5665, lon=126.9780),
    "부산": LocationCoordinate(name="부산", nx=98, ny=76, lat=35.1796, lon=129.0756),
    "대구": LocationCoordinate(name="대구", nx=89, ny=90, lat=35.8714, lon=128.6014),
    "인천": LocationCoordinate(name="인천", nx=55, ny=124, lat=37.4563, lon=126.7052),
    "광주": LocationCoordinate(name="광주", nx=58, ny=74, lat=35.1595, lon=126.8526),
    "대전": LocationCoordinate(name="대전", nx=67, ny=100, lat=36.3504, lon=127.3845),
    "울산": LocationCoordinate(name="울산", nx=102, ny=84, lat=35.5384, lon=129.3114),
    "세종": LocationCoordinate(name="세종", nx=66, ny=103, lat=36.4801, lon=127.2890),
    "경기": LocationCoordinate(name="수원", nx=60, ny=121, lat=37.2636, lon=127.0286),
    "강원": LocationCoordinate(name="춘천", nx=73, ny=134, lat=37.8813, lon=127.7298),
    "충북": LocationCoordinate(name="청주", nx=69, ny=106, lat=36.6424, lon=127.4890),
    "충남": LocationCoordinate(name="홍성", nx=65, ny=100, lat=36.6015, lon=126.6708),
    "전북": LocationCoordinate(name="전주", nx=63, ny=89, lat=35.8242, lon=127.1480),
    "전남": LocationCoordinate(name="목포", nx=50, ny=67, lat=34.8118, lon=126.3922),
    "경북": LocationCoordinate(name="안동", nx=91, ny=106, lat=36.5684, lon=128.7294),
    "경남": LocationCoordinate(name="창원", nx=90, ny=77, lat=35.2280, lon=128.6811),
    "제주": LocationCoordinate(name="제주", nx=52, ny=38, lat=33.4996, lon=126.5312),
}


def get_weather_service() -> KMAWeatherService:
    """WeatherService 인스턴스 반환"""
    return KMAWeatherService()
