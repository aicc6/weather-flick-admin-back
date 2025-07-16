"""
문의사항 관련 서비스
"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from fastapi import HTTPException

from app.models import Contact, ContactAnswer
from app.models_admin import Admin
from app.schemas.contact_schemas import (
    ContactAnswerCreate,
    ContactAnswerUpdate,
    ContactStatusUpdate,
    ContactStatsResponse
)


class ContactService:
    """문의사항 서비스 클래스"""
    
    @staticmethod
    def get_contacts(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> tuple[List[Contact], int]:
        """문의 목록 조회"""
        query = db.query(Contact).options(joinedload(Contact.answer))
        
        # 필터링
        if category:
            query = query.filter(Contact.category == category)
        if status:
            query = query.filter(Contact.approval_status == status)
        if search:
            query = query.filter(
                or_(
                    Contact.title.ilike(f"%{search}%"),
                    Contact.content.ilike(f"%{search}%"),
                    Contact.name.ilike(f"%{search}%"),
                    Contact.email.ilike(f"%{search}%")
                )
            )
        if start_date:
            query = query.filter(Contact.created_at >= start_date)
        if end_date:
            query = query.filter(Contact.created_at <= end_date)
        
        # 전체 개수
        total = query.count()
        
        # 페이지네이션
        contacts = query.order_by(Contact.created_at.desc()).offset(skip).limit(limit).all()
        
        # has_answer 속성 추가
        for contact in contacts:
            contact.has_answer = contact.answer is not None
        
        return contacts, total
    
    @staticmethod
    def get_contact(db: Session, contact_id: int) -> Contact:
        """문의 상세 조회"""
        contact = db.query(Contact).options(
            joinedload(Contact.answer).joinedload(ContactAnswer.admin)
        ).filter(Contact.id == contact_id).first()
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        # 답변에 관리자 이름 추가
        if contact.answer and contact.answer.admin:
            contact.answer.admin_name = contact.answer.admin.name
        
        return contact
    
    @staticmethod
    def update_contact_status(
        db: Session,
        contact_id: int,
        status_update: ContactStatusUpdate
    ) -> Contact:
        """문의 상태 변경"""
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        contact.approval_status = status_update.approval_status
        db.commit()
        db.refresh(contact)
        
        return contact
    
    @staticmethod
    def create_answer(
        db: Session,
        contact_id: int,
        answer_create: ContactAnswerCreate,
        admin_id: int
    ) -> ContactAnswer:
        """문의 답변 작성"""
        # 문의 확인
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        # 기존 답변 확인
        existing_answer = db.query(ContactAnswer).filter(
            ContactAnswer.contact_id == contact_id
        ).first()
        if existing_answer:
            raise HTTPException(status_code=400, detail="Answer already exists")
        
        # 답변 생성
        answer = ContactAnswer(
            contact_id=contact_id,
            admin_id=admin_id,
            content=answer_create.content
        )
        db.add(answer)
        
        # 상태를 COMPLETE로 변경
        contact.approval_status = 'COMPLETE'
        
        db.commit()
        db.refresh(answer)
        
        return answer
    
    @staticmethod
    def update_answer(
        db: Session,
        contact_id: int,
        answer_update: ContactAnswerUpdate,
        admin_id: int
    ) -> ContactAnswer:
        """문의 답변 수정"""
        answer = db.query(ContactAnswer).filter(
            ContactAnswer.contact_id == contact_id
        ).first()
        
        if not answer:
            raise HTTPException(status_code=404, detail="Answer not found")
        
        # 권한 확인 (본인이 작성한 답변만 수정 가능)
        if answer.admin_id != admin_id:
            # 슈퍼유저인 경우는 수정 가능
            admin = db.query(Admin).filter(Admin.id == admin_id).first()
            if not admin or not admin.is_superuser:
                raise HTTPException(
                    status_code=403,
                    detail="You can only edit your own answers"
                )
        
        answer.content = answer_update.content
        db.commit()
        db.refresh(answer)
        
        return answer
    
    @staticmethod
    def delete_answer(db: Session, contact_id: int, admin_id: int) -> None:
        """문의 답변 삭제"""
        answer = db.query(ContactAnswer).filter(
            ContactAnswer.contact_id == contact_id
        ).first()
        
        if not answer:
            raise HTTPException(status_code=404, detail="Answer not found")
        
        # 권한 확인
        admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if answer.admin_id != admin_id and not admin.is_superuser:
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own answers"
            )
        
        # 문의 상태를 PENDING으로 변경
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if contact:
            contact.approval_status = 'PENDING'
        
        db.delete(answer)
        db.commit()
    
    @staticmethod
    def get_contact_stats(db: Session) -> ContactStatsResponse:
        """문의 통계 조회"""
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        week_start = now - timedelta(days=now.weekday())
        month_start = datetime(now.year, now.month, 1)
        
        # 전체 개수
        total_count = db.query(Contact).count()
        
        # 상태별 개수
        pending_count = db.query(Contact).filter(
            Contact.approval_status == 'PENDING'
        ).count()
        processing_count = db.query(Contact).filter(
            Contact.approval_status == 'PROCESSING'
        ).count()
        complete_count = db.query(Contact).filter(
            Contact.approval_status == 'COMPLETE'
        ).count()
        
        # 기간별 개수
        today_count = db.query(Contact).filter(
            Contact.created_at >= today_start
        ).count()
        this_week_count = db.query(Contact).filter(
            Contact.created_at >= week_start
        ).count()
        this_month_count = db.query(Contact).filter(
            Contact.created_at >= month_start
        ).count()
        
        return ContactStatsResponse(
            total_count=total_count,
            pending_count=pending_count,
            processing_count=processing_count,
            complete_count=complete_count,
            today_count=today_count,
            this_week_count=this_week_count,
            this_month_count=this_month_count
        )
    
    @staticmethod
    def get_categories(db: Session) -> List[str]:
        """문의 카테고리 목록 조회"""
        categories = db.query(Contact.category).distinct().all()
        return [cat[0] for cat in categories]