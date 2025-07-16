"""
문의사항 관련 라우터
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_admin
from app.models_admin import Admin
from app.services.contact_service import ContactService
from app.schemas.contact_schemas import (
    ContactListResponse,
    ContactDetailResponse,
    ContactAnswerCreate,
    ContactAnswerUpdate,
    ContactAnswerResponse,
    ContactStatusUpdate,
    ContactStatsResponse
)
from app.dependencies import require_permission

router = APIRouter(prefix="/contact", tags=["contact"])


@router.get("", response_model=List[ContactListResponse])
@require_permission("contact.read")
async def get_contacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """문의 목록 조회"""
    contacts, total = ContactService.get_contacts(
        db, skip, limit, category, status, search, start_date, end_date
    )
    return contacts


@router.get("/stats", response_model=ContactStatsResponse)
@require_permission("contact.read")
async def get_contact_stats(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """문의 통계 조회"""
    return ContactService.get_contact_stats(db)


@router.get("/categories", response_model=List[str])
@require_permission("contact.read")
async def get_categories(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """문의 카테고리 목록 조회"""
    return ContactService.get_categories(db)


@router.get("/{contact_id}", response_model=ContactDetailResponse)
@require_permission("contact.read")
async def get_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """문의 상세 조회"""
    return ContactService.get_contact(db, contact_id)


@router.patch("/{contact_id}/status", response_model=ContactDetailResponse)
@require_permission("contact.update")
async def update_contact_status(
    contact_id: int,
    status_update: ContactStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """문의 상태 변경"""
    contact = ContactService.update_contact_status(db, contact_id, status_update)
    return ContactService.get_contact(db, contact_id)


@router.post("/{contact_id}/answer", response_model=ContactAnswerResponse)
@require_permission("contact.answer")
async def create_answer(
    contact_id: int,
    answer_create: ContactAnswerCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """문의 답변 작성"""
    answer = ContactService.create_answer(
        db, contact_id, answer_create, current_admin.admin_id
    )
    # 관리자 정보 추가
    answer.admin_name = current_admin.name
    return answer


@router.put("/{contact_id}/answer", response_model=ContactAnswerResponse)
@require_permission("contact.answer")
async def update_answer(
    contact_id: int,
    answer_update: ContactAnswerUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """문의 답변 수정"""
    answer = ContactService.update_answer(
        db, contact_id, answer_update, current_admin.admin_id
    )
    # 관리자 정보 추가
    admin = db.query(Admin).filter(Admin.admin_id == answer.admin_id).first()
    if admin:
        answer.admin_name = admin.name
    return answer


@router.delete("/{contact_id}/answer", status_code=204)
@require_permission("contact.answer")
async def delete_answer(
    contact_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """문의 답변 삭제"""
    ContactService.delete_answer(db, contact_id, current_admin.admin_id)
    return None