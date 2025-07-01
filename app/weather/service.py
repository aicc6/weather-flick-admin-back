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

    def get_major_cities(self) -> List[Dict]:
        """주요 도시 목록 반환"""
        return [
            {
                "name": city.name,
                "nx": city.nx,
                "ny": city.ny,
                "lat": city.lat,
                "lon": city.lon
            }
            for city in MAJOR_CITIES.values()
        ]

    def get_current_weather_by_city(self, city_name: str) -> Optional[WeatherInfo]:
        """도시명으로 현재 날씨 조회"""
        if city_name not in MAJOR_CITIES:
            logger.error(f"지원하지 않는 도시: {city_name}")
            return None

        city = MAJOR_CITIES[city_name]
        return self.get_current_weather(city.nx, city.ny, city.name)


# 주요 도시 좌표 (기상청 격자 좌표)
MAJOR_CITIES = {
    # 특별시/광역시
    "서울": LocationCoordinate(name="서울", nx=60, ny=127, lat=37.5665, lon=126.9780),
    "부산": LocationCoordinate(name="부산", nx=98, ny=76, lat=35.1796, lon=129.0756),
    "대구": LocationCoordinate(name="대구", nx=89, ny=90, lat=35.8714, lon=128.6014),
    "인천": LocationCoordinate(name="인천", nx=55, ny=124, lat=37.4563, lon=126.7052),
    "광주": LocationCoordinate(name="광주", nx=58, ny=74, lat=35.1595, lon=126.8526),
    "대전": LocationCoordinate(name="대전", nx=67, ny=100, lat=36.3504, lon=127.3845),
    "울산": LocationCoordinate(name="울산", nx=102, ny=84, lat=35.5384, lon=129.3114),
    "세종": LocationCoordinate(name="세종", nx=66, ny=103, lat=36.4801, lon=127.2890),

    # 경기도 주요 도시
    "수원": LocationCoordinate(name="수원", nx=60, ny=121, lat=37.2636, lon=127.0286),
    "고양": LocationCoordinate(name="고양", nx=57, ny=128, lat=37.6564, lon=126.8340),
    "용인": LocationCoordinate(name="용인", nx=64, ny=119, lat=37.2342, lon=127.2017),
    "성남": LocationCoordinate(name="성남", nx=63, ny=124, lat=37.4201, lon=127.1262),
    "부천": LocationCoordinate(name="부천", nx=56, ny=125, lat=37.5035, lon=126.7660),
    "안산": LocationCoordinate(name="안산", nx=58, ny=121, lat=37.3219, lon=126.8309),
    "안양": LocationCoordinate(name="안양", nx=59, ny=123, lat=37.3943, lon=126.9568),
    "평택": LocationCoordinate(name="평택", nx=62, ny=114, lat=36.9922, lon=127.1127),
    "의정부": LocationCoordinate(name="의정부", nx=61, ny=130, lat=37.7381, lon=127.0338),
    "시흥": LocationCoordinate(name="시흥", nx=57, ny=123, lat=37.3804, lon=126.8031),
    "파주": LocationCoordinate(name="파주", nx=56, ny=131, lat=37.7602, lon=126.7800),
    "김포": LocationCoordinate(name="김포", nx=55, ny=128, lat=37.6149, lon=126.7158),
    "광명": LocationCoordinate(name="광명", nx=58, ny=125, lat=37.4783, lon=126.8644),
    "경기광주": LocationCoordinate(name="경기광주", nx=61, ny=120, lat=37.4296, lon=127.2556),
    "이천": LocationCoordinate(name="이천", nx=68, ny=121, lat=37.2722, lon=127.4350),
    "양주": LocationCoordinate(name="양주", nx=61, ny=131, lat=37.7851, lon=127.0456),

    # 강원도 주요 도시
    "춘천": LocationCoordinate(name="춘천", nx=73, ny=134, lat=37.8813, lon=127.7298),
    "원주": LocationCoordinate(name="원주", nx=76, ny=122, lat=37.3422, lon=127.9202),
    "강릉": LocationCoordinate(name="강릉", nx=92, ny=131, lat=37.7519, lon=128.8761),
    "동해": LocationCoordinate(name="동해", nx=97, ny=127, lat=37.5247, lon=129.1144),
    "태백": LocationCoordinate(name="태백", nx=95, ny=119, lat=37.1640, lon=128.9856),
    "속초": LocationCoordinate(name="속초", nx=87, ny=141, lat=38.2070, lon=128.5918),
    "삼척": LocationCoordinate(name="삼척", nx=98, ny=125, lat=37.4496, lon=129.1658),
    "홍천": LocationCoordinate(name="홍천", nx=75, ny=133, lat=37.6971, lon=127.8897),
    "횡성": LocationCoordinate(name="횡성", nx=77, ny=125, lat=37.4914, lon=127.9816),
    "평창": LocationCoordinate(name="평창", nx=84, ny=123, lat=37.3706, lon=128.3904),

    # 충청북도 주요 도시
    "청주": LocationCoordinate(name="청주", nx=69, ny=106, lat=36.6424, lon=127.4890),
    "충주": LocationCoordinate(name="충주", nx=76, ny=114, lat=36.9910, lon=127.9259),
    "제천": LocationCoordinate(name="제천", nx=81, ny=118, lat=37.1326, lon=128.1909),
    "보은": LocationCoordinate(name="보은", nx=73, ny=103, lat=36.4890, lon=127.7294),
    "옥천": LocationCoordinate(name="옥천", nx=71, ny=99, lat=36.3068, lon=127.5717),
    "영동": LocationCoordinate(name="영동", nx=74, ny=97, lat=36.1750, lon=127.7766),
    "증평": LocationCoordinate(name="증평", nx=71, ny=110, lat=36.7879, lon=127.5815),
    "진천": LocationCoordinate(name="진천", nx=68, ny=111, lat=36.8554, lon=127.4330),
    "괴산": LocationCoordinate(name="괴산", nx=74, ny=111, lat=36.8158, lon=127.7878),
    "음성": LocationCoordinate(name="음성", nx=72, ny=113, lat=36.9434, lon=127.6867),
    "단양": LocationCoordinate(name="단양", nx=84, ny=115, lat=36.9848, lon=128.3656),

    # 충청남도 주요 도시
    "천안": LocationCoordinate(name="천안", nx=63, ny=110, lat=36.8151, lon=127.1139),
    "공주": LocationCoordinate(name="공주", nx=60, ny=103, lat=36.4465, lon=127.1188),
    "보령": LocationCoordinate(name="보령", nx=54, ny=100, lat=36.3333, lon=126.6128),
    "아산": LocationCoordinate(name="아산", nx=60, ny=109, lat=36.7898, lon=127.0022),
    "서산": LocationCoordinate(name="서산", nx=51, ny=110, lat=36.7847, lon=126.4504),
    "논산": LocationCoordinate(name="논산", nx=62, ny=97, lat=36.1871, lon=127.0987),
    "계룡": LocationCoordinate(name="계룡", nx=65, ny=99, lat=36.2746, lon=127.2489),
    "당진": LocationCoordinate(name="당진", nx=54, ny=112, lat=36.8943, lon=126.6279),
    "금산": LocationCoordinate(name="금산", nx=69, ny=95, lat=36.1089, lon=127.4881),
    "홍성": LocationCoordinate(name="홍성", nx=65, ny=100, lat=36.6015, lon=126.6708),
    "예산": LocationCoordinate(name="예산", nx=58, ny=107, lat=36.6829, lon=126.8497),
    "태안": LocationCoordinate(name="태안", nx=48, ny=109, lat=36.7453, lon=126.2982),
    "부여": LocationCoordinate(name="부여", nx=59, ny=99, lat=36.2756, lon=126.9099),
    "서천": LocationCoordinate(name="서천", nx=55, ny=94, lat=36.0819, lon=126.6919),
    "청양": LocationCoordinate(name="청양", nx=62, ny=103, lat=36.4594, lon=126.8024),

    # 전라북도 주요 도시
    "전주": LocationCoordinate(name="전주", nx=63, ny=89, lat=35.8242, lon=127.1480),
    "군산": LocationCoordinate(name="군산", nx=56, ny=92, lat=35.9677, lon=126.7369),
    "익산": LocationCoordinate(name="익산", nx=60, ny=91, lat=35.9483, lon=126.9576),
    "정읍": LocationCoordinate(name="정읍", nx=58, ny=83, lat=35.5699, lon=126.8558),
    "남원": LocationCoordinate(name="남원", nx=68, ny=80, lat=35.4163, lon=127.3906),
    "김제": LocationCoordinate(name="김제", nx=59, ny=88, lat=35.8038, lon=126.8810),
    "완주": LocationCoordinate(name="완주", nx=63, ny=89, lat=35.9050, lon=127.1605),
    "진안": LocationCoordinate(name="진안", nx=68, ny=88, lat=35.7917, lon=127.4244),
    "무주": LocationCoordinate(name="무주", nx=72, ny=93, lat=36.0074, lon=127.6605),
    "장수": LocationCoordinate(name="장수", nx=70, ny=85, lat=35.6474, lon=127.5203),
    "임실": LocationCoordinate(name="임실", nx=66, ny=84, lat=35.6175, lon=127.2898),
    "순창": LocationCoordinate(name="순창", nx=63, ny=79, lat=35.3741, lon=127.1374),
    "고창": LocationCoordinate(name="고창", nx=56, ny=80, lat=35.4347, lon=126.7022),
    "부안": LocationCoordinate(name="부안", nx=56, ny=87, lat=35.7319, lon=126.7330),

    # 전라남도 주요 도시
    "목포": LocationCoordinate(name="목포", nx=50, ny=67, lat=34.8118, lon=126.3922),
    "여수": LocationCoordinate(name="여수", nx=73, ny=66, lat=34.7604, lon=127.6622),
    "순천": LocationCoordinate(name="순천", nx=70, ny=70, lat=34.9507, lon=127.4872),
    "나주": LocationCoordinate(name="나주", nx=56, ny=71, lat=35.0160, lon=126.7108),
    "광양": LocationCoordinate(name="광양", nx=73, ny=70, lat=34.9407, lon=127.5956),
    "담양": LocationCoordinate(name="담양", nx=61, ny=78, lat=35.3211, lon=126.9880),
    "곡성": LocationCoordinate(name="곡성", nx=66, ny=77, lat=35.2819, lon=127.2930),
    "구례": LocationCoordinate(name="구례", nx=69, ny=75, lat=35.2027, lon=127.4632),
    "고흥": LocationCoordinate(name="고흥", nx=66, ny=62, lat=34.6114, lon=127.2753),
    "보성": LocationCoordinate(name="보성", nx=62, ny=66, lat=34.7715, lon=127.0801),
    "화순": LocationCoordinate(name="화순", nx=61, ny=72, lat=35.0645, lon=126.9864),
    "장흥": LocationCoordinate(name="장흥", nx=59, ny=63, lat=34.6811, lon=126.9073),
    "강진": LocationCoordinate(name="강진", nx=57, ny=63, lat=34.6420, lon=126.7674),
    "해남": LocationCoordinate(name="해남", nx=54, ny=61, lat=34.5736, lon=126.5987),
    "영암": LocationCoordinate(name="영암", nx=56, ny=69, lat=34.8000, lon=126.6967),
    "무안": LocationCoordinate(name="무안", nx=52, ny=71, lat=34.9903, lon=126.4819),
    "함평": LocationCoordinate(name="함평", nx=52, ny=75, lat=35.0669, lon=126.5168),
    "영광": LocationCoordinate(name="영광", nx=52, ny=77, lat=35.2773, lon=126.5122),
    "장성": LocationCoordinate(name="장성", nx=57, ny=77, lat=35.3019, lon=126.7886),
    "완도": LocationCoordinate(name="완도", nx=57, ny=56, lat=34.3114, lon=126.7552),
    "진도": LocationCoordinate(name="진도", nx=48, ny=59, lat=34.4867, lon=126.2633),
    "신안": LocationCoordinate(name="신안", nx=50, ny=66, lat=34.8267, lon=126.1077),

    # 경상북도 주요 도시
    "포항": LocationCoordinate(name="포항", nx=102, ny=94, lat=36.0190, lon=129.3435),
    "경주": LocationCoordinate(name="경주", nx=100, ny=91, lat=35.8562, lon=129.2247),
    "김천": LocationCoordinate(name="김천", nx=80, ny=96, lat=36.1396, lon=128.1133),
    "안동": LocationCoordinate(name="안동", nx=91, ny=106, lat=36.5684, lon=128.7294),
    "구미": LocationCoordinate(name="구미", nx=84, ny=96, lat=36.1196, lon=128.3441),
    "영주": LocationCoordinate(name="영주", nx=89, ny=111, lat=36.8056, lon=128.6236),
    "영천": LocationCoordinate(name="영천", nx=95, ny=93, lat=35.9731, lon=128.9386),
    "상주": LocationCoordinate(name="상주", nx=81, ny=103, lat=36.4107, lon=128.1590),
    "문경": LocationCoordinate(name="문경", nx=81, ny=106, lat=36.5866, lon=128.1863),
    "경산": LocationCoordinate(name="경산", nx=91, ny=90, lat=35.8251, lon=128.7411),
    "군위": LocationCoordinate(name="군위", nx=88, ny=99, lat=36.2395, lon=128.5719),
    "의성": LocationCoordinate(name="의성", nx=90, ny=101, lat=36.3526, lon=128.6973),
    "청송": LocationCoordinate(name="청송", nx=96, ny=103, lat=36.4359, lon=129.0570),
    "영양": LocationCoordinate(name="영양", nx=97, ny=108, lat=36.6669, lon=129.1123),
    "영덕": LocationCoordinate(name="영덕", nx=102, ny=103, lat=36.4155, lon=129.3653),
    "청도": LocationCoordinate(name="청도", nx=91, ny=86, lat=35.6474, lon=128.7345),
    "고령": LocationCoordinate(name="고령", nx=83, ny=87, lat=35.7275, lon=128.2636),
    "성주": LocationCoordinate(name="성주", nx=83, ny=91, lat=35.9196, lon=128.2829),
    "칠곡": LocationCoordinate(name="칠곡", nx=85, ny=93, lat=35.9942, lon=128.4015),
    "예천": LocationCoordinate(name="예천", nx=86, ny=107, lat=36.6546, lon=128.4517),
    "봉화": LocationCoordinate(name="봉화", nx=90, ny=113, lat=36.8932, lon=128.7323),
    "울진": LocationCoordinate(name="울진", nx=102, ny=115, lat=36.9931, lon=129.4006),
    "울릉": LocationCoordinate(name="울릉", nx=127, ny=127, lat=37.4845, lon=130.9058),

    # 경상남도 주요 도시
    "창원": LocationCoordinate(name="창원", nx=90, ny=77, lat=35.2280, lon=128.6811),
    "진주": LocationCoordinate(name="진주", nx=90, ny=75, lat=35.1799, lon=128.1076),
    "통영": LocationCoordinate(name="통영", nx=87, ny=68, lat=34.8543, lon=128.4334),
    "사천": LocationCoordinate(name="사천", nx=80, ny=71, lat=35.0036, lon=128.0646),
    "김해": LocationCoordinate(name="김해", nx=95, ny=77, lat=35.2342, lon=128.8897),
    "밀양": LocationCoordinate(name="밀양", nx=92, ny=83, lat=35.5040, lon=128.7463),
    "거제": LocationCoordinate(name="거제", nx=90, ny=69, lat=34.8807, lon=128.6212),
    "양산": LocationCoordinate(name="양산", nx=97, ny=79, lat=35.3350, lon=129.0378),
    "의령": LocationCoordinate(name="의령", nx=89, ny=78, lat=35.3224, lon=128.2616),
    "함안": LocationCoordinate(name="함안", nx=86, ny=77, lat=35.2733, lon=128.4065),
    "창녕": LocationCoordinate(name="창녕", nx=87, ny=83, lat=35.5448, lon=128.4925),
    "고성": LocationCoordinate(name="고성", nx=85, ny=71, lat=34.9736, lon=128.3227),
    "남해": LocationCoordinate(name="남해", nx=77, ny=68, lat=34.8372, lon=127.892),
    "하동": LocationCoordinate(name="하동", nx=74, ny=73, lat=35.0677, lon=127.7513),
    "산청": LocationCoordinate(name="산청", nx=76, ny=80, lat=35.4154, lon=127.8735),
    "함양": LocationCoordinate(name="함양", nx=74, ny=82, lat=35.5202, lon=127.7256),
    "거창": LocationCoordinate(name="거창", nx=77, ny=86, lat=35.6869, lon=127.9094),
    "합천": LocationCoordinate(name="합천", nx=81, ny=84, lat=35.5666, lon=128.1655),

    # 제주도
    "제주": LocationCoordinate(name="제주", nx=52, ny=38, lat=33.4996, lon=126.5312),
    "서귀포": LocationCoordinate(name="서귀포", nx=52, ny=33, lat=33.2541, lon=126.5600),
}


def get_weather_service() -> KMAWeatherService:
    """WeatherService 인스턴스 반환"""
    return KMAWeatherService()
