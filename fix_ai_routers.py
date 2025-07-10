#!/usr/bin/env python3
"""
AI 라우터 파일들의 권한 체크 및 사용자 참조를 관리자 백엔드에 맞게 수정하는 스크립트
"""

import os
import re

def fix_ai_router_file(file_path):
    """AI 라우터 파일을 수정"""
    print(f"Fixing {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. 관리자 권한 체크 코드 제거
        admin_check_patterns = [
            r'if not current_user\.get\("is_admin", False\):\s*raise HTTPException\(status_code=403, detail="Admin access required"\)',
            r'if not \(hasattr\(current_user, "role"\) and current_user\.role\.name == "ADMIN"\):\s*raise HTTPException\(status_code=403, detail="Admin access required"\)',
        ]
        
        for pattern in admin_check_patterns:
            content = re.sub(pattern, '# 관리자 백엔드에서는 이미 관리자 인증 완료', content, flags=re.MULTILINE | re.DOTALL)
        
        # 2. current_user 참조를 적절히 수정
        # current_user.id -> 함수에 따라 적절한 처리
        content = re.sub(r'user_id = current_user\.id', 'admin_id = current_admin.admin_id', content)
        content = re.sub(r'current_user\.id', 'current_admin.admin_id', content)
        content = re.sub(r'current_user\.get\("user_id"\)', 'current_admin.admin_id', content)
        
        # 3. 변수명 정리
        content = re.sub(r'current_user_id', 'admin_id', content)
        
        # 4. 로그 메시지 수정
        content = re.sub(r'"user_id": admin_id', '"admin_id": admin_id', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ Successfully fixed {file_path}")
        
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")

def main():
    """메인 함수"""
    router_dir = "/Users/sl/Repository/aicc6/weather-flick-admin-back/app/routers"
    
    # AI 라우터 파일들 찾기
    ai_router_files = []
    for file in os.listdir(router_dir):
        if file.startswith('ai_') and file.endswith('.py'):
            ai_router_files.append(os.path.join(router_dir, file))
    
    print(f"Found {len(ai_router_files)} AI router files to fix:")
    for file in ai_router_files:
        print(f"  - {file}")
    
    print("\nStarting fixes...")
    
    for file_path in ai_router_files:
        fix_ai_router_file(file_path)
    
    print(f"\n🎉 Completed fixing {len(ai_router_files)} AI router files!")

if __name__ == "__main__":
    main()