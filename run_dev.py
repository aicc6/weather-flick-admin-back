#!/usr/bin/env python3
"""
개발 서버 실행 스크립트

사용법:
    python run_dev.py

이 스크립트는 개발 환경에서 FastAPI 서버를 실행합니다.
"""

import uvicorn

from app.config import settings

if __name__ == "__main__":
    print(f"🚀 {settings.app_name} 개발 서버를 시작합니다...")
    print(f"📍 서버 주소: http://{settings.host}:{settings.port}")
    print(f"📖 API 문서: http://{settings.host}:{settings.port}/docs")
    print(f"🔧 디버그 모드: {settings.debug}")

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,  # 개발 시 자동 리로드
        log_level="info")
