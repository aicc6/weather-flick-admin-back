#!/usr/bin/env python3
"""
users 테이블 데이터 확인 스크립트
"""

import sys
import os
from pathlib import Path
import hashlib
import secrets

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from app.database import SessionLocal
    from app.models import User, Admin
except ImportError as e:
    print(f"Import 오류: {e}")
    sys.exit(1)

def get_password_hash(password: str) -> str:
    """비밀번호 해시 함수 (간단한 구현)"""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256()
    hash_obj.update((password + salt).encode())
    return f"{salt}${hash_obj.hexdigest()}"

def check_users():
    """users 테이블 데이터 확인"""
    db = SessionLocal()

    try:
        # users 테이블 데이터 확인
        users = db.query(User).all()
        print(f"Users 테이블에 {len(users)}개의 레코드가 있습니다:")

        for user in users:
            print(f"  - ID: {user.id}, 이름: {user.full_name}, 이메일: {user.email}, 활성: {user.is_active}")

        # admins 테이블 데이터 확인
        admins = db.query(Admin).all()
        print(f"\nAdmins 테이블에 {len(admins)}개의 레코드가 있습니다:")

        for admin in admins:
            print(f"  - ID: {admin.id}, 이름: {admin.full_name}, 이메일: {admin.email}, 슈퍼유저: {admin.is_superuser}, 활성: {admin.is_active}")

        # 테스트용 사용자 추가
        if len(users) == 0:
            print("\n테스트용 사용자를 추가합니다...")
            test_user = User(
                full_name="테스트 사용자",
                email="test@example.com",
                username="testuser",
                hashed_password=get_password_hash("test123!"),
                is_active=True
            )
            db.add(test_user)
            db.commit()
            print("테스트 사용자가 추가되었습니다.")

    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Users 테이블 데이터 확인 중...")
    check_users()
    print("완료!")
