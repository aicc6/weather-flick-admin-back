"""
로깅 설정 모듈
"""
import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

def setup_logging(log_dir: str = "logs", log_level: str = "INFO"):
    """
    애플리케이션 로깅 설정
    
    Args:
        log_dir: 로그 파일이 저장될 디렉토리
        log_level: 로깅 레벨
    """
    # 로그 디렉토리 생성
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 로그 포맷 설정
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(log_format, date_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 - 일반 로그
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / f"app_{datetime.now().strftime('%Y%m%d')}.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(log_format, date_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 에러 전용 파일 핸들러
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s",
        date_format
    )
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)
    
    # 특정 로거들의 레벨 조정 (노이즈 감소)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    
    # 초기화 메시지
    logging.info("="*50)
    logging.info(f"로깅 시스템 초기화 완료")
    logging.info(f"로그 디렉토리: {log_path.absolute()}")
    logging.info(f"로그 레벨: {log_level}")
    logging.info("="*50)