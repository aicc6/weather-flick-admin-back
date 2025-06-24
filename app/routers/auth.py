from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import authenticate_admin, create_access_token, get_current_active_admin
from app.crud import create_admin, get_admin_by_email, get_admin_by_username
from app.schemas import Token, AdminResponse, AdminRegister
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=AdminResponse)
async def register_admin(
    admin: AdminRegister,
    db: Session = Depends(get_db)
):
    """Register a new admin account (no authentication required)"""
    # Check if email already exists
    db_admin = get_admin_by_email(db, email=admin.email)
    if db_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    db_admin = get_admin_by_username(db, username=admin.username)
    if db_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    return create_admin(db=db, admin=admin)


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    admin = authenticate_admin(db, form_data.username, form_data.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive admin"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": admin.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=AdminResponse)
async def read_admins_me(current_admin: AdminResponse = Depends(get_current_active_admin)):
    return current_admin
