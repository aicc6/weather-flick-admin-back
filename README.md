# Weather Flick Admin Backend

Weather Flick 관리자 시스템의 백엔드 API 서버입니다.

## 기능

- 관리자 인증 (로그인/회원가입)
- JWT 토큰 기반 인증
- 기상청 단기예보 API 연동
- PostgreSQL 데이터베이스 연동
- FastAPI 기반 RESTful API
- Swagger UI 자동 문서화

## 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```env
# 애플리케이션 설정
DEBUG=true
SECRET_KEY=weatherflick-admin-secret-key

# 데이터베이스 설정
DATABASE_URL=postgresql://aicc6:aicc6_pass@seongjunlee.dev:55432/weather_flick

# 기상청 API 설정
KMA_API_KEY=YOUR_KMA_API_KEY
KMA_FORECAST_URL=http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0
```

> **참고**: 기상청 API 키는 [공공데이터포털](https://www.data.go.kr/data/15084084/openapi.do)에서 발급받을 수 있습니다.

### 3. 데이터베이스 초기화

```bash
python init_db.py
```

이 명령어는 다음을 수행합니다:

- 데이터베이스 테이블 생성
- 슈퍼 관리자 계정 생성

**슈퍼 관리자 계정 정보:**

- 이메일: `admin@weatherflick.com`
- 비밀번호: `admin123`

### 4. 서버 실행

#### 개발 환경

```bash
python run_dev.py
```

#### 프로덕션 환경

```bash
python main.py
```

### 5. API 문서 확인

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 엔드포인트

### 인증 관련

- `POST /api/v1/auth/login` - 관리자 로그인
- `POST /api/v1/auth/register` - 새 관리자 등록 (인증 필요)
- `GET /api/v1/auth/me` - 현재 관리자 프로필 조회
- `POST /api/v1/auth/logout` - 로그아웃
- `POST /api/v1/auth/token` - OAuth2 호환 로그인 (Swagger UI용)

### 날씨 관련

- `GET /api/v1/weather/current/{city_name}` - 도시별 현재 날씨 조회
- `GET /api/v1/weather/forecast/{city_name}` - 도시별 날씨 예보 조회
- `GET /api/v1/weather/current` - 좌표로 현재 날씨 조회
- `GET /api/v1/weather/forecast` - 좌표로 날씨 예보 조회
- `GET /api/v1/weather/cities` - 사용 가능한 도시 목록 조회
- `POST /api/v1/weather/ultra-srt-ncst` - 초단기실황 조회 (Raw API)
- `POST /api/v1/weather/ultra-srt-fcst` - 초단기예보 조회 (Raw API)
- `POST /api/v1/weather/vilage-fcst` - 단기예보 조회 (Raw API)
- `GET /api/v1/weather/health` - 날씨 서비스 헬스체크

### 기본 엔드포인트

- `GET /` - API 상태 확인
- `GET /health` - 헬스 체크

## 사용 예시

### 1. 로그인

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@weatherflick.com",
    "password": "admin123"
  }'
```

### 2. 서울 현재 날씨 조회

```bash
curl "http://localhost:8000/api/v1/weather/current/서울"
```

**응답 예시:**

```json
{
  "location": "서울",
  "nx": 60,
  "ny": 127,
  "forecast_time": "2025-07-01T10:00:00",
  "temperature": 28.3,
  "humidity": 83,
  "precipitation": 0.0,
  "wind_speed": 2.9,
  "wind_direction": 186,
  "sky_condition": null,
  "precipitation_type": "없음",
  "weather_description": "기온 28.3°C, 습도 83%, 풍속 2.9m/s"
}
```

### 3. 사용 가능한 도시 목록 조회

```bash
curl "http://localhost:8000/api/v1/weather/cities"
```

### 4. 좌표로 날씨 조회

```bash
curl "http://localhost:8000/api/v1/weather/current?nx=60&ny=127&location=서울"
```

### 5. 날씨 예보 조회

```bash
curl "http://localhost:8000/api/v1/weather/forecast/부산"
```

### 2. 새 관리자 등록

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "email": "newadmin@weatherflick.com",
    "password": "newpassword",
    "name": "New Admin"
  }'
```

### 3. 프로필 조회

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 프로젝트 구조

```
weather-flick-admin-back/
├── app/
│   ├── auth/           # 인증 관련 모듈
│   │   ├── __init__.py
│   │   ├── dependencies.py  # 의존성 주입
│   │   ├── router.py        # 인증 라우터
│   │   ├── schemas.py       # Pydantic 스키마
│   │   └── utils.py         # 인증 유틸리티
│   ├── weather/        # 날씨 관련 모듈
│   │   ├── __init__.py
│   │   ├── models.py        # 날씨 데이터 모델
│   │   ├── router.py        # 날씨 라우터
│   │   └── service.py       # 기상청 API 서비스
│   ├── config.py       # 설정
│   ├── database.py     # 데이터베이스 연결
│   ├── init_data.py    # 초기 데이터 생성
│   └── models.py       # SQLAlchemy 모델
├── main.py             # FastAPI 애플리케이션
├── init_db.py          # 데이터베이스 초기화 스크립트
├── run_dev.py          # 개발 서버 실행 스크립트
├── requirements.txt    # 의존성 목록
└── README.md
```

## 지원 도시

현재 다음 도시들의 날씨 정보를 제공합니다:

- **서울** (60, 127)
- **부산** (98, 76)
- **대구** (89, 90)
- **인천** (55, 124)
- **광주** (58, 74)
- **대전** (67, 100)
- **울산** (102, 84)
- **세종** (66, 103)
- **경기 (수원)** (60, 121)
- **강원 (춘천)** (73, 134)
- **충북 (청주)** (69, 106)
- **충남 (홍성)** (65, 100)
- **전북 (전주)** (63, 89)
- **전남 (목포)** (50, 67)
- **경북 (안동)** (91, 106)
- **경남 (창원)** (90, 77)
- **제주** (52, 38)

## 기상청 API 정보

이 서비스는 [기상청 단기예보 조회서비스](https://www.data.go.kr/data/15084084/openapi.do)를 사용합니다.

### 제공 데이터

- **초단기실황**: 현재 날씨 정보 (1시간 이내)
- **초단기예보**: 6시간 예보
- **단기예보**: 3일 예보

### 데이터 갱신 주기

- 초단기실황: 매시 30분 발표
- 초단기예보: 매시 30분 발표
- 단기예보: 02, 05, 08, 11, 14, 17, 20, 23시 발표

## 보안 참고사항

- 프로덕션 환경에서는 `SECRET_KEY`를 반드시 변경하세요
- `DEBUG=false`로 설정하세요
- CORS 설정에서 허용할 도메인을 명시적으로 지정하세요
- 데이터베이스 접속 정보를 안전하게 관리하세요
