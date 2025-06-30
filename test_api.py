#!/usr/bin/env python3
"""
API 기능 테스트 스크립트
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_login():
    """로그인 테스트"""
    print("=== 로그인 테스트 ===")

    login_data = {
        "email": "admin@weatherflick.com",
        "password": "admin123"
    }

    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)

    if response.status_code == 200:
        data = response.json()
        print("✅ 로그인 성공!")
        print(f"   관리자 ID: {data['admin']['id']}")
        print(f"   이메일: {data['admin']['email']}")
        print(f"   이름: {data['admin']['name']}")
        print(f"   로그인 횟수: {data['admin']['login_count']}")
        print(f"   토큰: {data['token']['access_token'][:50]}...")
        return data['token']['access_token']
    else:
        print(f"❌ 로그인 실패: {response.status_code}")
        print(f"   응답: {response.text}")
        return None

def test_profile(token):
    """프로필 조회 테스트"""
    print("\n=== 프로필 조회 테스트 ===")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)

    if response.status_code == 200:
        data = response.json()
        print("✅ 프로필 조회 성공!")
        print(f"   관리자 ID: {data['id']}")
        print(f"   이메일: {data['email']}")
        print(f"   이름: {data['name']}")
        print(f"   상태: {data['status']}")
    else:
        print(f"❌ 프로필 조회 실패: {response.status_code}")
        print(f"   응답: {response.text}")

def test_register(token):
    """새 관리자 등록 테스트"""
    print("\n=== 새 관리자 등록 테스트 ===")

    headers = {"Authorization": f"Bearer {token}"}
    register_data = {
        "email": "test@weatherflick.com",
        "password": "test123",
        "name": "Test Admin",
        "phone": "010-1234-5678"
    }

    response = requests.post(f"{BASE_URL}/auth/register", json=register_data, headers=headers)

    if response.status_code == 200:
        data = response.json()
        print("✅ 새 관리자 등록 성공!")
        print(f"   관리자 ID: {data['id']}")
        print(f"   이메일: {data['email']}")
        print(f"   이름: {data['name']}")
    else:
        print(f"❌ 새 관리자 등록 실패: {response.status_code}")
        print(f"   응답: {response.text}")

def test_health():
    """헬스 체크 테스트"""
    print("\n=== 헬스 체크 테스트 ===")

    response = requests.get("http://localhost:8000/health")

    if response.status_code == 200:
        data = response.json()
        print("✅ 헬스 체크 성공!")
        print(f"   상태: {data['status']}")
        print(f"   버전: {data['version']}")
    else:
        print(f"❌ 헬스 체크 실패: {response.status_code}")

if __name__ == "__main__":
    print("🧪 Weather Flick Admin API 테스트 시작\n")

    try:
        # 1. 헬스 체크
        test_health()

        # 2. 로그인 테스트
        token = test_login()

        if token:
            # 3. 프로필 조회 테스트
            test_profile(token)

            # 4. 새 관리자 등록 테스트
            test_register(token)

        print("\n🎉 모든 테스트 완료!")

    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행되고 있는지 확인하세요.")
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
