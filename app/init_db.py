# 최초 실행 시 슈퍼유저(admin@weatherflick.com/admin123) 자동 생성

from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from . import models, crud, schemas

# Create database tables
models.Base.metadata.create_all(bind=engine)


def init_db():
    db = SessionLocal()
    try:
        # Check if superuser already exists
        superuser = crud.get_admin_by_email(db, email="admin@weatherflick.com")
        if not superuser:
            # Create superuser
            superuser_data = schemas.AdminCreate(
                email="admin@weatherflick.com",
                username="admin",
                password="admin123"
            )
            superuser = crud.create_admin(db, admin=superuser_data)

            # Make superuser
            superuser.is_superuser = True
            db.commit()
            db.refresh(superuser)
            print("Superuser created successfully!")
        else:
            print("Superuser already exists!")
    finally:
        db.close()


if __name__ == "__main__":
    print("Creating initial data...")
    init_db()
    print("Initial data created!")
