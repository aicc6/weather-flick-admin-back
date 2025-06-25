# 관리자 관리 API

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import crud, schemas, auth
from ..database import get_db

router = APIRouter()


@router.get("/", response_model=List[schemas.Admin])
def read_admins(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_active_admin)
):
    admins = crud.get_admins(db, skip=skip, limit=limit)
    return admins


@router.post("/", response_model=schemas.Admin)
def create_admin(
    admin: schemas.AdminCreate,
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_superuser)
):
    # Check if email already exists
    db_admin = crud.get_admin_by_email(db, email=admin.email)
    if db_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    db_admin = crud.get_admin_by_username(db, username=admin.username)
    if db_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    return crud.create_admin(db=db, admin=admin)


@router.get("/{admin_id}", response_model=schemas.Admin)
def read_admin(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_active_admin)
):
    db_admin = crud.get_admin(db, admin_id=admin_id)
    if db_admin is None:
        raise HTTPException(status_code=404, detail="Admin not found")
    return db_admin


@router.put("/{admin_id}", response_model=schemas.Admin)
def update_admin(
    admin_id: int,
    admin_update: schemas.AdminUpdate,
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_superuser)
):
    db_admin = crud.update_admin(db, admin_id=admin_id, admin_update=admin_update)
    if db_admin is None:
        raise HTTPException(status_code=404, detail="Admin not found")
    return db_admin


@router.delete("/{admin_id}")
def delete_admin(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_superuser)
):
    success = crud.delete_admin(db, admin_id=admin_id)
    if not success:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {"message": "Admin deleted successfully"}


@router.put("/{admin_id}/activate", response_model=schemas.Admin)
def activate_admin(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_superuser)
):
    db_admin = crud.activate_admin(db, admin_id=admin_id)
    if db_admin is None:
        raise HTTPException(status_code=404, detail="Admin not found")
    return db_admin


@router.put("/{admin_id}/deactivate", response_model=schemas.Admin)
def deactivate_admin(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_superuser)
):
    db_admin = crud.deactivate_admin(db, admin_id=admin_id)
    if db_admin is None:
        raise HTTPException(status_code=404, detail="Admin not found")
    return db_admin
