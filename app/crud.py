from sqlalchemy.orm import Session
from app.models import Admin
from app.schemas import AdminCreate, AdminUpdate, AdminRegister
from app.auth import get_password_hash
from typing import Union


def get_admin(db: Session, admin_id: int) -> Admin:
    return db.query(Admin).filter(Admin.id == admin_id).first()


def get_admin_by_email(db: Session, email: str) -> Admin:
    return db.query(Admin).filter(Admin.email == email).first()


def get_admin_by_username(db: Session, username: str) -> Admin:
    return db.query(Admin).filter(Admin.username == username).first()


def get_admins(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Admin).offset(skip).limit(limit).all()


def create_admin(db: Session, admin: Union[AdminCreate, AdminRegister]) -> Admin:
    hashed_password = get_password_hash(admin.password)
    db_admin = Admin(
        email=admin.email,
        username=admin.username,
        hashed_password=hashed_password,
        full_name=admin.full_name
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin


def update_admin(db: Session, admin_id: int, admin_update: AdminUpdate) -> Admin:
    db_admin = get_admin(db, admin_id)
    if not db_admin:
        return None

    update_data = admin_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_admin, field, value)

    db.commit()
    db.refresh(db_admin)
    return db_admin


def delete_admin(db: Session, admin_id: int) -> bool:
    db_admin = get_admin(db, admin_id)
    if not db_admin:
        return False

    db.delete(db_admin)
    db.commit()
    return True
