from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, schemas, auth
from ..database import get_db

router = APIRouter()

@router.get("/", response_model=List[schemas.User])
def read_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, description="Search by email or username"),
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_active_admin)
):
    """
    사용자 목록 조회 (검색 지원)
    - 슈퍼유저 또는 활성 관리자만 접근 가능
    - PostgreSQL public.users 테이블에서 데이터 조회
    """
    if not current_admin.is_superuser and not current_admin.is_active:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    if search:
        return crud.search_users(db, search_term=search, skip=skip, limit=limit)
    else:
        return crud.get_users(db, skip=skip, limit=limit)

@router.get("/count", response_model=dict)
def get_users_count(
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_active_admin)
):
    """
    총 사용자 수 조회
    """
    if not current_admin.is_superuser and not current_admin.is_active:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    count = crud.get_users_count(db)
    return {"total_users": count}

@router.get("/{user_id}", response_model=schemas.User)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_active_admin)
):
    """
    특정 사용자 정보 조회
    """
    if not current_admin.is_superuser and not current_admin.is_active:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/", response_model=schemas.User)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_superuser)
):
    """
    새 사용자 생성 (슈퍼유저만)
    """
    # Check if user already exists
    db_user_email = crud.get_user_by_email(db, email=user.email)
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user_username = crud.get_user_by_username(db, username=user.username)
    if db_user_username:
        raise HTTPException(status_code=400, detail="Username already taken")

    return crud.create_user(db, user)

@router.put("/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_superuser)
):
    """
    사용자 정보 수정 (슈퍼유저만)
    """
    # Check if user exists
    db_user = crud.get_user(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check email uniqueness if being updated
    if user_update.email and user_update.email != db_user.email:
        existing_user = crud.get_user_by_email(db, email=user_update.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

    # Check username uniqueness if being updated
    if user_update.username and user_update.username != db_user.username:
        existing_user = crud.get_user_by_username(db, username=user_update.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")

    updated_user = crud.update_user(db, user_id=user_id, user_update=user_update)
    return updated_user

@router.put("/{user_id}/activate", response_model=schemas.User)
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_superuser)
):
    """
    사용자 계정 활성화 (슈퍼유저만)
    """
    user = crud.activate_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}/deactivate", response_model=schemas.User)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_superuser)
):
    """
    사용자 계정 비활성화 (슈퍼유저만)
    """
    user = crud.deactivate_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: schemas.Admin = Depends(auth.get_current_superuser)
):
    """
    사용자 삭제 (슈퍼유저만)
    """
    success = crud.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}
