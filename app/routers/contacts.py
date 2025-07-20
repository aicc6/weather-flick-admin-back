"""
간단한 문의사항 API 라우터
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
import asyncio

from ..database import get_db
from ..models import Contact, ContactAnswer, User, UserNotificationSettings
from ..models_admin import Admin
from ..dependencies import get_current_admin, check_permission
from ..services.notification_service import NotificationService

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/")
async def get_contacts(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(check_permission("contact.read")),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="문의 카테고리"),
    status: Optional[str] = Query(None, description="문의 상태"),
    search: Optional[str] = Query(None, description="검색어")
):
    """문의 목록 조회"""
    query = db.query(Contact)
    
    if category:
        query = query.filter(Contact.category == category)
    
    if status:
        query = query.filter(Contact.approval_status == status)
    
    if search:
        query = query.filter(
            (Contact.title.ilike(f"%{search}%")) |
            (Contact.name.ilike(f"%{search}%")) |
            (Contact.email.ilike(f"%{search}%"))
        )
    
    total = query.count()
    contacts = query.order_by(Contact.created_at.desc()).offset(skip).limit(limit).all()
    
    items = []
    for contact in contacts:
        # 답변 확인
        answer = db.query(ContactAnswer).filter(ContactAnswer.contact_id == contact.id).first()
        
        items.append({
            "id": contact.id,  # 프론트엔드에서 id로 사용
            "category": contact.category,
            "title": contact.title,
            "name": contact.name,
            "email": contact.email,
            "phone": "",  # phone 컬럼이 없음
            "approval_status": contact.approval_status if contact.approval_status else "PENDING",
            "status": contact.approval_status,  # status 대신 approval_status 사용
            "has_answer": answer is not None,
            "is_private": contact.is_private if hasattr(contact, 'is_private') else False,
            "created_at": contact.created_at.isoformat() if contact.created_at else None,
            "updated_at": contact.created_at.isoformat() if contact.created_at else None  # updated_at이 없으므로 created_at 사용
        })
    
    # 프론트엔드가 배열을 기대하므로 배열로 반환
    return items


@router.get("/stats")
async def get_contact_stats(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(check_permission("contact.read"))
):
    """문의 통계 조회"""
    total = db.query(func.count(Contact.id)).scalar() or 0
    pending = db.query(func.count(Contact.id)).filter(Contact.approval_status == "PENDING").scalar() or 0
    answered = db.query(func.count(Contact.id)).filter(Contact.approval_status == "PROCESSING").scalar() or 0
    completed = db.query(func.count(Contact.id)).filter(Contact.approval_status == "COMPLETE").scalar() or 0
    
    # 카테고리별 통계
    category_stats = []
    categories = db.query(Contact.category, func.count(Contact.id))\
        .group_by(Contact.category)\
        .all()
    
    for category, count in categories:
        if category:
            category_stats.append({
                "category": category,
                "count": count
            })
    
    return {
        "total_count": total,
        "pending_count": pending,
        "processing_count": answered,  # 프론트엔드에서 processing으로 표시
        "complete_count": completed,
        "today_count": db.query(func.count(Contact.id)).filter(
            Contact.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).scalar() or 0,
        "by_category": category_stats
    }


@router.get("/categories")
async def get_contact_categories(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(check_permission("contact.read"))
):
    """문의 카테고리 목록 조회"""
    categories = db.query(Contact.category).distinct().filter(Contact.category != None).all()
    return [cat[0] for cat in categories]


@router.get("/{contact_id}")
async def get_contact_detail(
    contact_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(check_permission("contact.read"))
):
    """문의 상세 조회"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다.")
    
    # 답변 조회
    answer = db.query(ContactAnswer).filter(ContactAnswer.contact_id == contact_id).first()
    answer_data = None
    
    if answer:
        admin = db.query(Admin).filter(Admin.admin_id == answer.admin_id).first()
        answer_data = {
            "id": answer.id,
            "content": answer.content,
            "admin_id": answer.admin_id,
            "admin_name": admin.name if admin else "알 수 없음",
            "created_at": answer.created_at.isoformat() if answer.created_at else None,
            "updated_at": answer.updated_at.isoformat() if hasattr(answer, 'updated_at') and answer.updated_at else None
        }
    
    return {
        "id": contact.id,
        "contact_id": contact.id,
        "category": contact.category,
        "title": contact.title,
        "content": contact.content,
        "name": contact.name,
        "email": contact.email,
        "phone": "",  # phone 컬럼 없음
        "approval_status": contact.approval_status if contact.approval_status else "PENDING",
        "status": contact.approval_status,
        "is_private": contact.is_private if hasattr(contact, 'is_private') else False,
        "views": contact.views if hasattr(contact, 'views') else 0,
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
        "updated_at": contact.created_at.isoformat() if contact.created_at else None,  # updated_at 없음
        "answer": answer_data
    }


@router.post("/{contact_id}/answer")
async def create_answer(
    contact_id: int,
    answer_data: dict,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(check_permission("contact.answer"))
):
    """문의 답변 작성"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다.")
    
    # 이미 답변이 있는지 확인
    existing_answer = db.query(ContactAnswer).filter(ContactAnswer.contact_id == contact_id).first()
    if existing_answer:
        raise HTTPException(status_code=400, detail="이미 답변이 있습니다.")
    
    # content 필드 확인
    content = answer_data.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="답변 내용을 입력해주세요.")
    
    # 답변 생성
    answer = ContactAnswer(
        contact_id=contact_id,
        admin_id=current_admin.admin_id,
        content=content
    )
    db.add(answer)
    
    # 문의 상태 업데이트
    contact.approval_status = "COMPLETE"
    
    # 문의 작성자에게 알림 생성
    # 이메일로 사용자 찾기
    user = db.query(User).filter(User.email == contact.email).first()
    if user:
        # 알림 서비스 초기화
        notification_service = NotificationService(db)
        
        # 사용자의 알림 설정 확인
        user_settings = db.query(UserNotificationSettings).filter(
            UserNotificationSettings.user_id == user.user_id
        ).first()
        
        # 문의 답변 알림 전송 (모든 활성 채널로)
        asyncio.create_task(
            notification_service.send_contact_answer_notification(
                user=user,
                contact_title=contact.title,
                answer_content=content,
                contact_id=contact.id,
                user_settings=user_settings
            )
        )
    
    db.commit()
    db.refresh(answer)
    
    return {
        "answer_id": answer.id,
        "content": answer.content,
        "created_at": answer.created_at
    }


@router.patch("/{contact_id}/status")
async def update_contact_status(
    contact_id: int,
    status_data: dict,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(check_permission("contact.update"))
):
    """문의 상태 변경"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다.")
    
    status = status_data.get("approval_status") or status_data.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="상태값을 입력해주세요.")
    
    if status not in ["PENDING", "PROCESSING", "COMPLETE"]:
        raise HTTPException(status_code=400, detail="잘못된 상태값입니다.")
    
    contact.approval_status = status
    
    db.commit()
    
    return {"status": status}


@router.put("/{contact_id}/answer")
async def update_answer(
    contact_id: int,
    answer_data: dict,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(check_permission("contact.answer"))
):
    """문의 답변 수정"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다.")
    
    # 답변 확인
    answer = db.query(ContactAnswer).filter(ContactAnswer.contact_id == contact_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="답변을 찾을 수 없습니다.")
    
    # content 필드 확인
    content = answer_data.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="답변 내용을 입력해주세요.")
    
    # 답변 수정
    answer.content = content
    if hasattr(answer, 'updated_at'):
        answer.updated_at = datetime.now()
    
    db.commit()
    db.refresh(answer)
    
    # 관리자 정보 추가
    admin = db.query(Admin).filter(Admin.admin_id == answer.admin_id).first()
    
    return {
        "id": answer.id,
        "content": answer.content,
        "admin_id": answer.admin_id,
        "admin_name": admin.name if admin else "알 수 없음",
        "created_at": answer.created_at.isoformat() if answer.created_at else None,
        "updated_at": answer.updated_at.isoformat() if hasattr(answer, 'updated_at') and answer.updated_at else None
    }


@router.delete("/{contact_id}/answer")
async def delete_answer(
    contact_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(check_permission("contact.answer"))
):
    """문의 답변 삭제"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다.")
    
    # 답변 확인
    answer = db.query(ContactAnswer).filter(ContactAnswer.contact_id == contact_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="답변을 찾을 수 없습니다.")
    
    # 답변 삭제
    db.delete(answer)
    
    # 문의 상태를 PENDING으로 변경
    contact.approval_status = "PENDING"
    
    db.commit()
    
    return {"message": "답변이 삭제되었습니다."}