from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Admin
from app.schemas import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def get_admin_by_email(db: Session, email: str) -> Optional[Admin]:
    return db.query(Admin).filter(Admin.email == email).first()


def authenticate_admin(db: Session, email: str, password: str) -> Optional[Admin]:
    admin = get_admin_by_email(db, email)
    if not admin:
        return None
    if not verify_password(password, admin.hashed_password):
        return None
    return admin


async def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Admin:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    admin = get_admin_by_email(db, email=token_data.email)
    if admin is None:
        raise credentials_exception
    return admin


async def get_current_active_admin(current_admin: Admin = Depends(get_current_admin)) -> Admin:
    if not current_admin.is_active:
        raise HTTPException(status_code=400, detail="Inactive admin")
    return current_admin


async def get_current_superuser(current_admin: Admin = Depends(get_current_active_admin)) -> Admin:
    if not current_admin.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The admin doesn't have enough privileges"
        )
    return current_admin
