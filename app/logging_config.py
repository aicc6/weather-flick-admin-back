"""
로깅 설정 - 프로덕션 환경에 최적화
"""

import logging
import logging.config
import os
from pathlib import Path

from app.config import settings
from app.utils.logging_filters import SensitiveDataFilter, HTTPRequestFilter, SecurityLogFormatter

# 로그 디렉토리 생성
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)


def get_logging_config():
    """환경에 따른 로깅 설정 반환"""
    # 환경 변수에서 로그 레벨 가져오기
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    environment = os.getenv("ENVIRONMENT", "development").lower()

    # JSON formatter 사용 가능 여부 확인
    try:
        import pythonjsonlogger.jsonlogger  # noqa: F401

        json_formatter_available = True
    except ImportError:
        json_formatter_available = False

    # 포맷터 설정
    formatters = {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "security": {
            "()": SecurityLogFormatter,
            "format": "%(asctime)s - SECURITY - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }

    # JSON 포맷터 사용 가능할 때 추가
    if json_formatter_available:
        formatters["json"] = {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(filename)s %(lineno)d %(funcName)s %(message)s %(request_id)s",
        }
        # 프로덕션 환경에서는 JSON을 기본으로 사용
        default_formatter = "json" if environment == "production" else "default"
    else:
        default_formatter = "default"

    # 필터 설정
    filters = {
        "sensitive_filter": {
            "()": SensitiveDataFilter,
        },
        "http_filter": {
            "()": HTTPRequestFilter,
        },
    }

    # 핸들러 설정
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": default_formatter,
            "stream": "ext://sys.stdout",
            "filters": ["sensitive_filter"],
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
            "filters": ["sensitive_filter"],
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": "logs/error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
            "filters": ["sensitive_filter"],
        },
    }

    # JSON formatter가 있으면 JSON 로그 파일 핸들러 추가
    if json_formatter_available:
        handlers["json_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": "logs/app.json",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
            "filters": ["sensitive_filter"],
        }

        # 보안 로그 핸들러 추가
        handlers["security_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "security",
            "filename": "logs/security.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "encoding": "utf8",
            "filters": ["sensitive_filter"],
        }

    app_handlers = ["console", "file", "error_file"]
    if json_formatter_available:
        app_handlers.append("json_file")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "filters": filters,
        "handlers": handlers,
        "loggers": {
            "app": {
                "level": "DEBUG",
                "handlers": app_handlers,
                "propagate": False,
            },
            "uvicorn": {
                "level": "DEBUG",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "DEBUG" if settings.debug else "WARNING",
                "handlers": ["file"],
                "propagate": False,
            },
            "security": {
                "level": "INFO",
                "handlers": ["security_file"] if json_formatter_available else ["file"],
                "propagate": False,
            },
        },
        "root": {"level": "INFO", "handlers": ["console", "file"]},
    }


def setup_logging():
    """로깅 설정 초기화"""
    config = get_logging_config()
    logging.config.dictConfig(config)

    # 앱 로거 반환
    logger = logging.getLogger("app")

    # JSON formatter 사용 가능 여부 로그
    try:
        import pythonjsonlogger.jsonlogger  # noqa: F401

        logger.info("로깅 시스템이 초기화되었습니다. (JSON 포맷 지원)")
    except ImportError:
        logger.info("로깅 시스템이 초기화되었습니다. (텍스트 포맷만 지원)")

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """로거 인스턴스 반환"""
    if name:
        return logging.getLogger(f"app.{name}")
    return logging.getLogger("app")
