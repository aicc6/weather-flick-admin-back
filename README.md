# Weather Flick Admin Back End

관리자 페이지를 위한 FastAPI 기반 백엔드 애플리케이션입니다.

## 기능

- 🔐 JWT 기반 인증 시스템
- 👥 관리자 계정 관리 (생성, 수정, 삭제, 활성화/비활성화)
  > 로그인시 메일 인증 = Google SMTP를 사용하여 구현
- 🛡️ 권한 기반 접근 제어 (일반 관리자 / 슈퍼유저)
- 📊 관리자 목록 조회 및 페이징
- 🔒 비밀번호 해싱 (bcrypt)
- 🌐 CORS 지원

## 설치 및 실행

### 1. 의존성 설치

**Python/pip 사용:**

```bash
pip install -r requirements.txt
```

**Windows 사용자를 위한 배치 파일:**

```bash
install_requirements.bat
```

### 2. 환경 변수 설정

`env.example` 파일을 참고하여 `.env` 파일을 생성하세요:

```bash
cp env.example .env
```

### 3. 데이터베이스 초기화

```bash
python -m app.init_db
```

### 4. 서버 실행

**방법 1: 개선된 run.py 사용 (권장)**

```bash
python run.py
# uvicorn app.main:app --reload
```

**방법 2: Windows 배치 파일 사용**

```bash
start_server.bat
```

**방법 3: uvicorn 직접 사용**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

서버가 실행되면 다음과 같은 메시지가 표시됩니다:

```
🚀 Starting Weather Flick Admin Backend Server...
📍 Server will be available at: http://localhost:8000
📊 Admin API Documentation: http://localhost:8000/docs
🔄 Auto-reload enabled for development
```

서버가 실행되면 다음 URL에서 접근할 수 있습니다:

- **API 문서**: http://localhost:8000/docs
- **대안 문서**: http://localhost:8000/redoc
- **헬스 체크**: http://localhost:8000/health
- **기본 엔드포인트**: http://localhost:8000/

## 문제 해결

### 서버가 시작되지 않는 경우

1. **포트 충돌 확인**

   ```bash
   netstat -an | findstr :8000
   ```

   8000번 포트가 이미 사용 중이면 다른 포트를 사용하세요.

2. **의존성 확인**

   ```bash
   pip list | findstr fastapi
   pip list | findstr uvicorn
   ```

3. **데이터베이스 연결 확인**
   `app/config.py`에서 데이터베이스 URL이 올바른지 확인하세요.

4. **Python 버전 확인**
   Python 3.8 이상이 필요합니다.

### 일반적인 오류

- **"You must pass the application as an import string to enable 'reload'"**:
  이 경고는 이제 수정되었습니다. `python run.py`를 사용하세요.

- **데이터베이스 연결 오류**:
  PostgreSQL 서버가 실행 중인지 확인하고 `app/config.py`의 설정을 확인하세요.

## API 엔드포인트

### 인증 (Authentication)

- `POST /auth/login` - 관리자 로그인
- `GET /auth/me` - 현재 로그인한 관리자 정보 조회

### 관리자 관리 (Admin Management)

- `GET /admins/` - 관리자 목록 조회 (슈퍼유저만)
- `POST /admins/` - 새 관리자 생성 (슈퍼유저만)
- `GET /admins/{admin_id}` - 특정 관리자 조회 (슈퍼유저만)
- `PUT /admins/{admin_id}` - 관리자 정보 수정 (슈퍼유저만)
- `DELETE /admins/{admin_id}` - 관리자 삭제 (슈퍼유저만)
- `PUT /admins/{admin_id}/activate` - 관리자 계정 활성화 (슈퍼유저만)
- `PUT /admins/{admin_id}/deactivate` - 관리자 계정 비활성화 (슈퍼유저만)

### 날씨 데이터 (Weather Data)

- `GET /weather/` - 날씨 데이터 조회

### 사용자 관리 (User Management)

- `GET /users/` - 사용자 목록 조회

## 기본 계정

초기 슈퍼유저 계정:

- 이메일: admin@weatherflick.com
- 비밀번호: admin123

## 보안

- 모든 비밀번호는 bcrypt로 해싱됩니다
- JWT 토큰은 30분 후 만료됩니다
- 슈퍼유저만 관리자 계정을 관리할 수 있습니다
- CORS 설정으로 허용된 도메인에서만 접근 가능합니다

## 개발

### 프로젝트 구조

```
app/
├── __init__.py
├── main.py              # FastAPI 애플리케이션
├── config.py            # 설정 관리
├── database.py          # 데이터베이스 연결
├── models.py            # SQLAlchemy 모델
├── schemas.py           # Pydantic 스키마
├── auth.py              # 인증 관련 함수
├── crud.py              # 데이터베이스 CRUD 작업
├── init_db.py           # 초기 데이터베이스 설정
├── routers/
│   ├── __init__.py
│   ├── auth.py          # 인증 라우터
│   ├── admins.py        # 관리자 관리 라우터
│   ├── weather.py       # 날씨 데이터 라우터
│   └── users.py         # 사용자 관리 라우터
└── services/            # 비즈니스 로직 서비스
```

### 개발 도구

- **run.py**: 개선된 서버 시작 스크립트
- **start_server.bat**: Windows용 서버 시작 배치 파일
- **install_requirements.bat**: Windows용 의존성 설치 배치 파일
