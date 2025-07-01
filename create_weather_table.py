#!/usr/bin/env python3
"""
PostgreSQL에 날씨 데이터 테이블 생성 스크립트
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models import Base, CityWeatherData
from app.config import settings

def create_weather_table():
    """날씨 데이터 테이블 생성"""

    # 데이터베이스 URL 설정
    DATABASE_URL = "postgresql://aicc6:aicc6_pass@seongjunlee.dev:55432/weather_flick"

    try:
        # 엔진 생성
        engine = create_engine(DATABASE_URL)

        print("🔗 데이터베이스 연결 중...")

        # 연결 테스트
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ PostgreSQL 연결 성공: {version}")

        print("\n📊 테이블 생성 중...")

        # 모든 테이블 생성 (없는 테이블만 생성됨)
        Base.metadata.create_all(engine)

        print("✅ 테이블 생성 완료!")

        # 생성된 테이블 확인
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE '%weather%'
                ORDER BY table_name
            """))

            weather_tables = result.fetchall()

            if weather_tables:
                print("\n📋 생성된 날씨 관련 테이블:")
                for table in weather_tables:
                    print(f"  - {table[0]}")

            # city_weather_data 테이블 구조 확인
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'city_weather_data'
                ORDER BY ordinal_position
            """))

            columns = result.fetchall()

            if columns:
                print(f"\n🏗️  city_weather_data 테이블 구조:")
                for column in columns:
                    nullable = "NULL" if column[2] == "YES" else "NOT NULL"
                    print(f"  - {column[0]}: {column[1]} ({nullable})")

        print("\n🎉 설정 완료!")
        print("\n📡 사용 가능한 API 엔드포인트:")
        print("  - POST /api/v1/weather/collect/current")
        print("  - POST /api/v1/weather/collect/all")
        print("  - GET  /api/v1/weather/database/stats")
        print("  - GET  /api/v1/weather/database/data")
        print("  - GET  /api/v1/weather/database/latest/{city_name}")
        print("  - POST /api/v1/weather/database/cleanup")

        return True

    except SQLAlchemyError as e:
        print(f"❌ 데이터베이스 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

def check_database_connection():
    """데이터베이스 연결 확인"""
    DATABASE_URL = "postgresql://aicc6:aicc6_pass@seongjunlee.dev:55432/weather_flick"

    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

if __name__ == "__main__":
    print("🌤️  Weather Flick - 날씨 데이터 테이블 생성 도구")
    print("=" * 50)

    # 데이터베이스 연결 확인
    if not check_database_connection():
        print("❌ 데이터베이스 연결 실패!")
        print("   연결 정보를 확인해주세요:")
        print("   Host: seongjunlee.dev:55432")
        print("   Database: weather_flick")
        print("   User: aicc6")
        sys.exit(1)

    # 테이블 생성
    success = create_weather_table()

    if success:
        print("\n🚀 이제 FastAPI 서버를 실행하고 날씨 데이터를 수집해보세요!")
        print("   python run_dev.py")
        sys.exit(0)
    else:
        print("\n💥 테이블 생성 실패!")
        sys.exit(1)
