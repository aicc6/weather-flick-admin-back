#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트

사용법:
    python init_db.py

이 스크립트는 다음 작업을 수행합니다:
1. 데이터베이스 테이블 생성
2. 슈퍼 관리자 계정 생성 (admin@weatherflick.com / admin123)
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.init_data import init_database

if __name__ == "__main__":
    print("=" * 50)
    print("Weather Flick Admin - 데이터베이스 초기화")
    print("=" * 50)

    try:
        init_database()
        print("\n" + "=" * 50)
        print("초기화 완료!")
        print("\n슈퍼 관리자 계정 정보:")
        print("이메일: admin@weatherflick.com")
        print("비밀번호: admin123")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 초기화 실패: {e}")
        sys.exit(1)
