#!/usr/bin/env python3
"""
역할 및 권한 데이터 수정 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.config import settings
from app.models_rbac import Role, Permission, Resource, role_permissions
from app.models_admin import Admin
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_roles_and_permissions():
    """역할과 권한 데이터를 수정합니다"""
    
    # 데이터베이스 연결
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 1. 기존 역할들을 사용자 역할로 변경 (시스템 역할이 아니도록)
        logger.info("기존 역할들을 사용자 역할로 변경 중...")
        roles_to_update = ['user_manager', 'content_manager', 'data_analyst']
        for role_name in roles_to_update:
            role = db.query(Role).filter(Role.name == role_name).first()
            if role:
                role.is_system = False
                logger.info(f"역할 '{role.display_name}' 시스템 플래그 해제")
        
        # 2. 권한 데이터가 없다면 생성
        logger.info("권한 데이터 확인 및 생성 중...")
        
        # 기본 리소스들
        resources_data = [
            {'name': 'users', 'display_name': '사용자', 'description': '사용자 관리', 'module': 'user_management'},
            {'name': 'content', 'display_name': '콘텐츠', 'description': '콘텐츠 관리', 'module': 'content_management'},
            {'name': 'destinations', 'display_name': '목적지', 'description': '여행 목적지 관리', 'module': 'content_management'},
            {'name': 'reviews', 'display_name': '리뷰', 'description': '사용자 리뷰 관리', 'module': 'content_management'},
            {'name': 'support', 'display_name': '지원', 'description': '고객 지원', 'module': 'user_management'},
            {'name': 'reports', 'display_name': '보고서', 'description': '분석 보고서', 'module': 'analytics'},
            {'name': 'dashboard', 'display_name': '대시보드', 'description': '관리 대시보드', 'module': 'system'},
            {'name': 'logs', 'display_name': '로그', 'description': '시스템 로그', 'module': 'system'},
            {'name': 'system', 'display_name': '시스템', 'description': '시스템 설정', 'module': 'system'},
            {'name': 'promotions', 'display_name': '프로모션', 'description': '프로모션 관리', 'module': 'content_management'},
            {'name': 'recommendations', 'display_name': '추천', 'description': '추천 시스템', 'module': 'ai'},
            {'name': 'ai_models', 'display_name': 'AI 모델', 'description': 'AI 모델 관리', 'module': 'ai'},
            {'name': 'contact', 'display_name': '문의', 'description': '고객 문의', 'module': 'user_management'},
        ]
        
        # 리소스 생성
        for res_data in resources_data:
            existing = db.query(Resource).filter(Resource.name == res_data['name']).first()
            if not existing:
                resource = Resource(**res_data)
                db.add(resource)
                logger.info(f"리소스 '{res_data['display_name']}' 생성")
        
        db.commit()
        
        # 3. 권한 생성 (리소스별 기본 액션들)
        actions = ['read', 'write', 'delete', 'export', 'approve', 'respond', 'generate', 'update', 'answer']
        
        # 특정 리소스별 특별 액션
        special_actions = {
            'support': ['respond'],
            'reports': ['generate', 'export'],
            'content': ['approve'],
            'contact': ['update', 'answer']
        }
        
        resources = db.query(Resource).all()
        for resource in resources:
            # 기본 액션들
            basic_actions = ['read']
            if resource.name in ['users', 'content', 'destinations', 'reviews', 'promotions']:
                basic_actions.extend(['write', 'delete'])
            if resource.name in ['users', 'reports', 'logs']:
                basic_actions.append('export')
            if resource.name == 'content':
                basic_actions.append('approve')
            if resource.name == 'support':
                basic_actions.extend(['write', 'respond'])
            if resource.name == 'reports':
                basic_actions.append('generate')
            if resource.name in ['ai_models', 'recommendations']:
                basic_actions.append('write')
            if resource.name == 'contact':
                basic_actions.extend(['update', 'answer'])
            
            for action in basic_actions:
                permission_name = f"{resource.name}.{action}"
                existing = db.query(Permission).filter(Permission.name == permission_name).first()
                if not existing:
                    permission = Permission(
                        name=permission_name,
                        resource_id=resource.id,
                        action=action,
                        description=f"{resource.display_name} {action}"
                    )
                    db.add(permission)
                    logger.info(f"권한 '{permission_name}' 생성")
        
        db.commit()
        
        # 4. 역할에 권한 할당 확인 및 재할당
        logger.info("역할별 권한 할당 확인 중...")
        
        role_permissions_map = {
            'user_manager': [
                'users.read', 'users.write', 'users.delete', 'users.export',
                'content.read', 'destinations.read', 'reviews.read', 'reviews.write', 'reviews.delete',
                'support.read', 'support.write', 'support.respond',
                'reports.read', 'dashboard.read', 'logs.read'
            ],
            'content_manager': [
                'content.read', 'content.write', 'content.delete', 'content.approve',
                'destinations.read', 'destinations.write', 'destinations.delete',
                'reviews.read', 'users.read',
                'promotions.read', 'promotions.write', 'promotions.delete',
                'recommendations.read', 'recommendations.write',
                'ai_models.read', 'ai_models.write',
                'reports.read', 'dashboard.read'
            ],
            'data_analyst': [
                'users.read', 'content.read', 'destinations.read', 'reviews.read',
                'support.read', 'reports.read', 'reports.generate', 'reports.export',
                'dashboard.read', 'logs.read', 'logs.export', 'system.read',
                'promotions.read', 'recommendations.read', 'ai_models.read'
            ],
            'super_admin': [
                'contact.read', 'contact.update', 'contact.answer'
            ]
        }
        
        for role_name, permission_names in role_permissions_map.items():
            role = db.query(Role).filter(Role.name == role_name).first()
            if role:
                # 기존 권한 클리어
                role.permissions.clear()
                
                # 새 권한 할당
                for perm_name in permission_names:
                    permission = db.query(Permission).filter(Permission.name == perm_name).first()
                    if permission:
                        role.permissions.append(permission)
                        logger.info(f"역할 '{role.display_name}'에 권한 '{perm_name}' 할당")
                    else:
                        logger.warning(f"권한 '{perm_name}'을 찾을 수 없습니다")
        
        db.commit()
        logger.info("역할 및 권한 데이터 수정 완료!")
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_roles_and_permissions()