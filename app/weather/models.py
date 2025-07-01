from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime


class WeatherResponseHeader(BaseModel):
    """기상청 API 응답 헤더"""
    resultCode: str
    resultMsg: str


class WeatherItem(BaseModel):
    """기상청 API 응답 아이템"""
    baseDate: str  # 발표일자 (YYYYMMDD)
    baseTime: str  # 발표시각 (HHMM)
    category: str  # 자료구분코드
    nx: int        # 예보지점 X 좌표
    ny: int        # 예보지점 Y 좌표
    obsrValue: Optional[str] = None  # 실황값 (초단기실황)
    fcstDate: Optional[str] = None   # 예보일자 (YYYYMMDD) (예보)
    fcstTime: Optional[str] = None   # 예보시각 (HHMM) (예보)
    fcstValue: Optional[str] = None  # 예보값 (예보)


class WeatherResponseItems(BaseModel):
    """기상청 API 응답 아이템 래퍼"""
    item: List[WeatherItem]


class WeatherResponseBody(BaseModel):
    """기상청 API 응답 바디"""
    dataType: str
    items: WeatherResponseItems
    pageNo: int
    numOfRows: int
    totalCount: int


class WeatherApiResponse(BaseModel):
    """기상청 API 전체 응답"""
    header: WeatherResponseHeader
    body: WeatherResponseBody


class WeatherResponse(BaseModel):
    """API 응답 래퍼"""
    response: WeatherApiResponse


class UltraSrtNcstRequest(BaseModel):
    """초단기실황 조회 요청"""
    base_date: str  # 발표일자 (YYYYMMDD)
    base_time: str  # 발표시각 (HHMM)
    nx: int         # 예보지점 X 좌표
    ny: int         # 예보지점 Y 좌표
    page_no: int = 1
    num_of_rows: int = 1000
    data_type: str = "JSON"


class UltraSrtFcstRequest(BaseModel):
    """초단기예보 조회 요청"""
    base_date: str  # 발표일자 (YYYYMMDD)
    base_time: str  # 발표시각 (HHMM)
    nx: int         # 예보지점 X 좌표
    ny: int         # 예보지점 Y 좌표
    page_no: int = 1
    num_of_rows: int = 1000
    data_type: str = "JSON"


class VilageFcstRequest(BaseModel):
    """단기예보 조회 요청"""
    base_date: str  # 발표일자 (YYYYMMDD)
    base_time: str  # 발표시각 (HHMM)
    nx: int         # 예보지점 X 좌표
    ny: int         # 예보지점 Y 좌표
    page_no: int = 1
    num_of_rows: int = 1000
    data_type: str = "JSON"


class WeatherInfo(BaseModel):
    """처리된 날씨 정보"""
    location: str  # 지역명
    nx: int        # X 좌표
    ny: int        # Y 좌표
    forecast_time: datetime  # 예보 시각
    temperature: Optional[float] = None      # 기온 (°C)
    humidity: Optional[int] = None           # 습도 (%)
    precipitation: Optional[float] = None    # 강수량 (mm)
    wind_speed: Optional[float] = None       # 풍속 (m/s)
    wind_direction: Optional[int] = None     # 풍향 (deg)
    sky_condition: Optional[str] = None      # 하늘상태
    precipitation_type: Optional[str] = None # 강수형태
    weather_description: str = ""            # 날씨 설명


class LocationCoordinate(BaseModel):
    """위치 좌표 정보"""
    name: str    # 지역명
    nx: int      # X 좌표 (기상청 격자)
    ny: int      # Y 좌표 (기상청 격자)
    lat: float   # 위도
    lon: float   # 경도
