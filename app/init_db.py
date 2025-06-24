from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base
from app.crud import create_superuser, get_admin_by_email
from app.config import settings


def init_db():
    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if superuser already exists
        superuser = get_admin_by_email(db, settings.ADMIN_EMAIL)
        if not superuser:
            # Create superuser
            create_superuser(
                db=db,
                email=settings.ADMIN_EMAIL,
                username="admin",
                password=settings.ADMIN_PASSWORD,
                full_name="System Administrator"
            )
            print(f"Superuser created: {settings.ADMIN_EMAIL}")
        else:
            print(f"Superuser already exists: {settings.ADMIN_EMAIL}")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
