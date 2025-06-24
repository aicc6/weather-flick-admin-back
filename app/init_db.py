from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base
from app.crud import create_admin, get_admin_by_email
from app.schemas import AdminCreate
from app.config import settings


def init_db():
    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if default admin already exists
        default_admin = get_admin_by_email(db, settings.ADMIN_EMAIL)
        if not default_admin:
            # Create default admin
            admin_data = AdminCreate(
                email=settings.ADMIN_EMAIL,
                username="admin",
                password=settings.ADMIN_PASSWORD,
                full_name="System Administrator"
            )
            create_admin(db=db, admin=admin_data)
            print(f"Default admin created: {settings.ADMIN_EMAIL}")
        else:
            print(f"Default admin already exists: {settings.ADMIN_EMAIL}")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
