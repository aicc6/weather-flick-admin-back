#!/usr/bin/env python3
"""
데이터베이스 시드 스크립트
초기 사용자 및 관리자 데이터를 생성합니다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from app.database import SessionLocal, engine
    from app.models import Base, Admin, User
    from app.auth import get_password_hash
except ImportError as e:
    print(f"Import 오류: {e}")
    print("현재 디렉토리:", os.getcwd())
    print("Python 경로:", sys.path)
    sys.exit(1)

def create_tables():
    """테이블 생성"""
    try:
        Base.metadata.create_all(bind=engine)
        print("테이블 생성 완료")
    except Exception as e:
        print(f"테이블 생성 오류: {e}")

def seed_data():
    """초기 데이터 생성"""
    db = SessionLocal()

    try:
        # 기존 데이터 확인
        existing_admins = db.query(Admin).count()
        existing_users = db.query(User).count()

        print(f"기존 관리자 수: {existing_admins}")
        print(f"기존 사용자 수: {existing_users}")

        # 슈퍼유저가 없으면 생성
        if existing_admins == 0:
            superuser = Admin(
                full_name="슈퍼 관리자",
                email="admin@weatherflick.com",
                username="superadmin",
                hashed_password=get_password_hash("admin123!"),
                is_active=True,
                is_superuser=True
            )
            db.add(superuser)
            print("슈퍼유저 생성: admin@weatherflick.com")

        # 일반 관리자 생성
        admin = Admin(
            full_name="일반 관리자",
            email="manager@weatherflick.com",
            username="manager",
            hashed_password=get_password_hash("manager123!"),
            is_active=True,
            is_superuser=False
        )
        db.add(admin)
        print("일반 관리자 생성: manager@weatherflick.com")

        # 테스트 사용자들 생성
        test_users = [
            {
                "full_name": "김철수",
                "email": "kim@example.com",
                "username": "kimchulsoo",
                "password": "user123!"
            },
            {
                "full_name": "이영희",
                "email": "lee@example.com",
                "username": "leeyounghee",
                "password": "user123!"
            },
            {
                "full_name": "박민수",
                "email": "park@example.com",
                "username": "parkminsu",
                "password": "user123!"
            },
            {
                "full_name": "정수진",
                "email": "jung@example.com",
                "username": "jungsujin",
                "password": "user123!"
            }
        ]

        for user_data in test_users:
            # 중복 확인
            existing_user = db.query(User).filter(
                (User.email == user_data["email"]) |
                (User.username == user_data["username"])
            ).first()

            if not existing_user:
                user = User(
                    full_name=user_data["full_name"],
                    email=user_data["email"],
                    username=user_data["username"],
                    hashed_password=get_password_hash(user_data["password"]),
                    is_active=True
                )
                db.add(user)
                print(f"사용자 생성: {user_data['email']}")

        db.commit()
        print("데이터베이스 시드 완료!")

    except Exception as e:
        print(f"시드 중 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("데이터베이스 시드 시작...")
    create_tables()
    seed_data()
    print("시드 완료!")
