from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas, auth
from ..database import get_db

router = APIRouter()

@router.get("/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_admin: schemas.Admin = Depends(auth.get_current_active_admin)):
    # 슈퍼유저 또는 활성 관리자만 접근 가능
    if not current_admin.is_superuser and not current_admin.is_active:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.get_users(db, skip=skip, limit=limit)

@router.post("/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), current_admin: schemas.Admin = Depends(auth.get_current_superuser)):
    return crud.create_user(db, user)

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_admin: schemas.Admin = Depends(auth.get_current_superuser)):
    success = crud.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}
