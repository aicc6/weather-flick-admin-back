# Weather Flick Admin Backend

Weather Flick 관리자 시스템의 백엔드 API 서버입니다.

## 기능

- 관리자 인증 (로그인/회원가입)
- JWT 토큰 기반 인증
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
```

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

## 보안 참고사항

- 프로덕션 환경에서는 `SECRET_KEY`를 반드시 변경하세요
- `DEBUG=false`로 설정하세요
- CORS 설정에서 허용할 도메인을 명시적으로 지정하세요
- 데이터베이스 접속 정보를 안전하게 관리하세요
