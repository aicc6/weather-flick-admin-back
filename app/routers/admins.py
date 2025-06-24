from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_active_admin, get_current_superuser
from app.crud import (
    get_admins, get_admin, create_admin, update_admin,
    delete_admin, get_admin_by_email, get_admin_by_username
)
from app.schemas import AdminCreate, AdminUpdate, AdminResponse

router = APIRouter(prefix="/admins", tags=["admins"])


@router.get("/", response_model=List[AdminResponse])
async def read_admins(
    skip: int = 0,
    limit: int = 100,
    current_admin: AdminResponse = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Get all admins (superuser only)"""
    admins = get_admins(db, skip=skip, limit=limit)
    return admins


@router.post("/", response_model=AdminResponse)
async def create_new_admin(
    admin: AdminCreate,
    db: Session = Depends(get_db)
):
    """Create a new admin (registration endpoint - no authentication required)"""
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


@router.get("/{admin_id}", response_model=AdminResponse)
async def read_admin(
    admin_id: int,
    current_admin: AdminResponse = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Get a specific admin by ID (superuser only)"""
    db_admin = get_admin(db, admin_id=admin_id)
    if db_admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    return db_admin


@router.put("/{admin_id}", response_model=AdminResponse)
async def update_admin_info(
    admin_id: int,
    admin_update: AdminUpdate,
    current_admin: AdminResponse = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Update admin information (superuser only)"""
    db_admin = update_admin(db, admin_id=admin_id, admin_update=admin_update)
    if db_admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    return db_admin


@router.delete("/{admin_id}")
async def delete_admin_user(
    admin_id: int,
    current_admin: AdminResponse = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Delete an admin (superuser only)"""
    success = delete_admin(db, admin_id=admin_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    return {"message": "Admin deleted successfully"}


@router.put("/{admin_id}/activate")
async def activate_admin(
    admin_id: int,
    current_admin: AdminResponse = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Activate an admin account (superuser only)"""
    admin_update = AdminUpdate(is_active=True)
    db_admin = update_admin(db, admin_id=admin_id, admin_update=admin_update)
    if db_admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    return {"message": "Admin activated successfully"}


@router.put("/{admin_id}/deactivate")
async def deactivate_admin(
    admin_id: int,
    current_admin: AdminResponse = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Deactivate an admin account (superuser only)"""
    admin_update = AdminUpdate(is_active=False)
    db_admin = update_admin(db, admin_id=admin_id, admin_update=admin_update)
    if db_admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    return {"message": "Admin deactivated successfully"}
