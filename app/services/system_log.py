import inspect

from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SystemLog


def log_system_event(level, message, source=None, context=None, db: Session = None):
    if db is None:
        # FastAPI Depends로 사용 시 get_db()로 세션 획득
        db = next(get_db())
    if not source:
        # 호출한 모듈/함수명을 자동으로 기록
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        source = module.__name__ if module else "unknown"
    log = SystemLog(
        level=level,
        source=source,
        message=message,
        context=context or {},
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
