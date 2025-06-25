# DB CRUD(Create, Read, Update, Delete) 함수

from sqlalchemy.orm import Session
from . import models, schemas
from .auth import get_password_hash


def get_admin(db: Session, admin_id: int):
    return db.query(models.Admin).filter(models.Admin.id == admin_id).first()


def get_admin_by_email(db: Session, email: str):
    return db.query(models.Admin).filter(models.Admin.email == email).first()


def get_admin_by_username(db: Session, username: str):
    return db.query(models.Admin).filter(models.Admin.username == username).first()


def get_admins(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Admin).offset(skip).limit(limit).all()


def create_admin(db: Session, admin: schemas.AdminCreate):
    hashed_password = get_password_hash(admin.password)
    db_admin = models.Admin(
        full_name=admin.full_name,
        email=admin.email,
        username=admin.username,
        hashed_password=hashed_password
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin


def update_admin(db: Session, admin_id: int, admin_update: schemas.AdminUpdate):
    db_admin = get_admin(db, admin_id)
    if not db_admin:
        return None

    update_data = admin_update.dict(exclude_unset=True)

    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(db_admin, field, value)

    db.commit()
    db.refresh(db_admin)
    return db_admin


def delete_admin(db: Session, admin_id: int):
    db_admin = get_admin(db, admin_id)
    if db_admin:
        db.delete(db_admin)
        db.commit()
        return True
    return False


def activate_admin(db: Session, admin_id: int):
    db_admin = get_admin(db, admin_id)
    if db_admin:
        db_admin.is_active = True
        db.commit()
        db.refresh(db_admin)
        return db_admin
    return None


def deactivate_admin(db: Session, admin_id: int):
    db_admin = get_admin(db, admin_id)
    if db_admin:
        db_admin.is_active = False
        db.commit()
        db.refresh(db_admin)
        return db_admin
    return None


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        full_name=user.full_name,
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False
