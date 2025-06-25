# 데이터베이스 초기화 및 기본 데이터 생성

from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from . import models, crud, schemas
from .auth import get_password_hash


def init_db():
    # Create tables
    models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Check if superuser already exists
        superuser = crud.get_admin_by_email(db, email="admin@weatherflick.com")
        if not superuser:
            # Create superuser
            superuser_data = schemas.AdminCreate(
                full_name="Super Admin",
                email="admin@weatherflick.com",
                username="superadmin",
                password="admin123"
            )
            superuser = crud.create_admin(db, superuser_data)

            # Set as superuser
            superuser.is_superuser = True
            superuser.is_active = True
            db.commit()
            db.refresh(superuser)
            print("✅ Superuser created successfully!")
            print(f"   Email: {superuser.email}")
            print(f"   Username: {superuser.username}")
            print(f"   Password: admin123")
        else:
            print("✅ Superuser already exists!")

        # Check if regular admin exists
        admin = crud.get_admin_by_email(db, email="manager@weatherflick.com")
        if not admin:
            # Create regular admin
            admin_data = schemas.AdminCreate(
                full_name="Manager",
                email="manager@weatherflick.com",
                username="manager",
                password="manager123"
            )
            admin = crud.create_admin(db, admin_data)
            print("✅ Regular admin created successfully!")
            print(f"   Email: {admin.email}")
            print(f"   Username: {admin.username}")
            print(f"   Password: manager123")
        else:
            print("✅ Regular admin already exists!")

    except Exception as e:
        print(f"❌ Error creating initial data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialization completed!")
