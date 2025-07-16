"""
관리자 카테고리 관리 API 라우터
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.models import CategoryCode
from app.auth import require_super_admin

router = APIRouter(prefix="/admin/categories", tags=["Admin - Categories"])


@router.post("/kto/initialize")
async def initialize_kto_categories(
    db: Session = Depends(get_db),
    _: dict = Depends(require_super_admin)
):
    """
    한국관광공사 표준 카테고리 데이터 초기화
    """
    try:
        # 기존 데이터 삭제
        db.query(CategoryCode).delete()
        
        # 1. 대분류 카테고리 (cat1) 적재
        categories_level1 = [
            ('A01', '자연'),
            ('A02', '인문(문화/예술/역사)'),
            ('A03', '레포츠'),
            ('A04', '쇼핑'),
            ('A05', '음식'),
            ('B01', '건물'),
            ('B02', '이벤트'),
            ('C01', '추천코스'),
            ('C02', '가족코스'),
            ('C03', '나홀로코스'),
            ('C04', '커플코스'),
            ('C05', '친구코스'),
        ]
        
        for code, name in categories_level1:
            category = CategoryCode(
                category_code=code,
                category_name=name,
                parent_category_code=None,
                level=1
            )
            db.add(category)
        
        # 2. 관광지 중분류 카테고리
        categories_tourist = [
            ('A0101', '자연관광지', 'A01'),
            ('A0102', '관광자원', 'A01'),
            ('A0201', '역사관광지', 'A02'),
            ('A0202', '휴양관광지', 'A02'),
            ('A0203', '체험관광지', 'A02'),
            ('A0204', '산업관광지', 'A02'),
            ('A0205', '건축/조형물', 'A02'),
            ('A0206', '문화관광지', 'A02'),
            ('A0301', '레포츠소개', 'A03'),
            ('A0302', '육상레포츠', 'A03'),
            ('A0303', '수상레포츠', 'A03'),
            ('A0304', '항공레포츠', 'A03'),
            ('A0305', '복합레포츠', 'A03'),
            ('A0401', '쇼핑', 'A04'),
            ('A0502', '음식점', 'A05'),
        ]
        
        for code, name, parent in categories_tourist:
            category = CategoryCode(
                category_code=code,
                category_name=name,
                parent_category_code=parent,
                level=2
            )
            db.add(category)
        
        # 3. 문화시설 카테고리
        categories_cultural = [
            ('A0207', '박물관', 'A02'),
            ('A0208', '기념관', 'A02'),
            ('A0209', '전시관', 'A02'),
            ('A0210', '컨벤션센터', 'A02'),
            ('A0211', '미술관/화랑', 'A02'),
            ('A0212', '공연장', 'A02'),
            ('A0213', '문화원', 'A02'),
            ('A0214', '외국문화원', 'A02'),
            ('A0215', '도서관', 'A02'),
            ('A0216', '대형서점', 'A02'),
            ('A0217', '문화전수시설', 'A02'),
            ('A0218', '영화관', 'A02'),
        ]
        
        for code, name, parent in categories_cultural:
            category = CategoryCode(
                category_code=code,
                category_name=name,
                parent_category_code=parent,
                level=2
            )
            db.add(category)
        
        # 4. 축제공연행사(15) 카테고리
        categories_festival = [
            ('A0207', '문화관광축제', '15', 'A02'),
            ('A0208', '일반축제', '15', 'A02'),
            ('A0209', '전통공연', '15', 'A02'),
            ('A0210', '연극', '15', 'A02'),
            ('A0211', '뮤지컬', '15', 'A02'),
            ('A0212', '오페라', '15', 'A02'),
            ('A0213', '전시회', '15', 'A02'),
            ('A0214', '박람회', '15', 'A02'),
            ('A0215', '컨벤션', '15', 'A02'),
            ('A0216', '무용', '15', 'A02'),
            ('A0217', '클래식음악회', '15', 'A02'),
            ('A0218', '대중콘서트', '15', 'A02'),
            ('A0219', '영화', '15', 'A02'),
            ('A0220', '스포츠경기', '15', 'A02'),
            ('A0221', '기타행사', '15', 'A02'),
        ]
        
        for code, name, content_type, parent in categories_festival:
            category = CategoryCode(
                category_code=code,
                category_name=name,
                content_type_id=content_type,
                parent_category_code=parent,
                category_level=2
            )
            db.add(category)
        
        # 5. 여행코스(25) 카테고리
        categories_course = [
            ('C0112', '가족코스', '25', 'C01'),
            ('C0113', '나홀로코스', '25', 'C01'),
            ('C0114', '커플코스', '25', 'C01'),
            ('C0115', '친구코스', '25', 'C01'),
            ('C0116', '효도코스', '25', 'C01'),
            ('C0117', '도보코스', '25', 'C01'),
        ]
        
        for code, name, content_type, parent in categories_course:
            category = CategoryCode(
                category_code=code,
                category_name=name,
                content_type_id=content_type,
                parent_category_code=parent,
                category_level=2
            )
            db.add(category)
        
        # 6. 레포츠(28) 카테고리
        categories_sports = [
            ('A0301', '레포츠소개', '28', 'A03'),
            ('A0302', '육상레포츠', '28', 'A03'),
            ('A0303', '수상레포츠', '28', 'A03'),
            ('A0304', '항공레포츠', '28', 'A03'),
            ('A0305', '복합레포츠', '28', 'A03'),
        ]
        
        for code, name, content_type, parent in categories_sports:
            category = CategoryCode(
                category_code=code,
                category_name=name,
                content_type_id=content_type,
                parent_category_code=parent,
                category_level=2
            )
            db.add(category)
        
        # 7. 숙박(32) 카테고리
        categories_accommodation = [
            ('B0201', '관광호텔', '32', 'B01'),
            ('B0202', '수상관광호텔', '32', 'B01'),
            ('B0203', '전통호텔', '32', 'B01'),
            ('B0204', '가족호텔', '32', 'B01'),
            ('B0205', '호스텔', '32', 'B01'),
            ('B0206', '여관', '32', 'B01'),
            ('B0207', '모텔', '32', 'B01'),
            ('B0208', '민박', '32', 'B01'),
            ('B0209', '게스트하우스', '32', 'B01'),
            ('B0210', '홈스테이', '32', 'B01'),
            ('B0211', '서비스드레지던스', '32', 'B01'),
            ('B0212', '의료관광호텔', '32', 'B01'),
            ('B0213', '소형호텔', '32', 'B01'),
            ('B0214', '펜션', '32', 'B01'),
            ('B0215', '콘도미니엄', '32', 'B01'),
            ('B0216', '유스호스텔', '32', 'B01'),
            ('B0217', '야영장', '32', 'B01'),
            ('B0218', '한옥', '32', 'B01'),
        ]
        
        for code, name, content_type, parent in categories_accommodation:
            category = CategoryCode(
                category_code=code,
                category_name=name,
                content_type_id=content_type,
                parent_category_code=parent,
                category_level=2
            )
            db.add(category)
        
        # 8. 쇼핑(38) 카테고리
        categories_shopping = [
            ('A0401', '쇼핑', '38', 'A04'),
            ('A0402', '면세점', '38', 'A04'),
            ('A0403', '대형마트', '38', 'A04'),
            ('A0404', '전문상가', '38', 'A04'),
            ('A0405', '백화점', '38', 'A04'),
            ('A0406', '시장', '38', 'A04'),
            ('A0407', '상설시장', '38', 'A04'),
            ('A0408', '전통시장', '38', 'A04'),
            ('A0409', '5일장', '38', 'A04'),
            ('A0410', '상점가', '38', 'A04'),
            ('A0411', '아울렛', '38', 'A04'),
            ('A0412', '편의점', '38', 'A04'),
        ]
        
        for code, name, content_type, parent in categories_shopping:
            category = CategoryCode(
                category_code=code,
                category_name=name,
                content_type_id=content_type,
                parent_category_code=parent,
                category_level=2
            )
            db.add(category)
        
        # 9. 음식점(39) 카테고리
        categories_restaurant = [
            ('A0502', '음식점', '39', 'A05'),
            ('A0503', '카페/디저트', '39', 'A05'),
            ('A0504', '술집', '39', 'A05'),
            ('A0505', '한식', '39', 'A05'),
            ('A0506', '서양식', '39', 'A05'),
            ('A0507', '일식', '39', 'A05'),
            ('A0508', '중식', '39', 'A05'),
            ('A0509', '아시아식', '39', 'A05'),
            ('A0510', '패스트푸드', '39', 'A05'),
            ('A0511', '간식', '39', 'A05'),
            ('A0512', '분식', '39', 'A05'),
            ('A0513', '뷔페', '39', 'A05'),
            ('A0514', '민속주점', '39', 'A05'),
            ('A0515', '이색음식점', '39', 'A05'),
        ]
        
        for code, name, content_type, parent in categories_restaurant:
            category = CategoryCode(
                category_code=code,
                category_name=name,
                content_type_id=content_type,
                parent_category_code=parent,
                category_level=2
            )
            db.add(category)
        
        # 커밋
        db.commit()
        
        # 결과 확인
        total_count = db.query(CategoryCode).count()
        
        # 컨텐츠 타입별 개수 확인
        content_type_counts = db.execute(text("""
            SELECT 
                COALESCE(content_type_id, 'ROOT') as content_type,
                category_level,
                COUNT(*) as count
            FROM category_codes 
            GROUP BY content_type_id, category_level 
            ORDER BY content_type_id, category_level
        """)).fetchall()
        
        return {
            "message": "한국관광공사 표준 카테고리 데이터 초기화 완료",
            "total_count": total_count,
            "breakdown": [
                {
                    "content_type": row[0],
                    "category_level": row[1],
                    "count": row[2]
                } for row in content_type_counts
            ]
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"카테고리 초기화 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/")
async def get_all_categories(
    content_type_id: str = None,
    category_level: int = None,
    db: Session = Depends(get_db),
    _: dict = Depends(require_super_admin)
):
    """
    전체 카테고리 목록 조회
    """
    try:
        query = db.query(CategoryCode)
        
        if content_type_id:
            query = query.filter(CategoryCode.content_type_id == content_type_id)
        
        if category_level:
            query = query.filter(CategoryCode.category_level == category_level)
        
        categories = query.order_by(CategoryCode.category_code).all()
        
        result = []
        for category in categories:
            result.append({
                "category_code": category.category_code,
                "category_name": category.category_name,
                "content_type_id": category.content_type_id,
                "parent_category_code": category.parent_category_code,
                "category_level": category.category_level,
                "created_at": category.created_at.isoformat() if category.created_at else None,
                "updated_at": category.updated_at.isoformat() if category.updated_at else None,
            })
        
        return {
            "categories": result,
            "total_count": len(result)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"카테고리 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/content-types")
async def get_content_types(
    db: Session = Depends(get_db),
    _: dict = Depends(require_super_admin)
):
    """
    컨텐츠 타입별 카테고리 통계 조회
    """
    try:
        # 컨텐츠 타입별 카테고리 개수 조회
        stats = db.execute(text("""
            SELECT 
                content_type_id,
                COUNT(*) as category_count
            FROM category_codes 
            WHERE content_type_id IS NOT NULL
            GROUP BY content_type_id 
            ORDER BY content_type_id
        """)).fetchall()
        
        # 컨텐츠 타입 매핑
        content_type_mapping = {
            '12': '관광지',
            '14': '문화시설',
            '15': '축제공연행사',
            '25': '여행코스',
            '28': '레포츠',
            '32': '숙박',
            '38': '쇼핑',
            '39': '음식점'
        }
        
        result = []
        for content_type_id, count in stats:
            result.append({
                "content_type_id": content_type_id,
                "content_type_name": content_type_mapping.get(content_type_id, f"Unknown ({content_type_id})"),
                "category_count": count
            })
        
        return {
            "content_types": result,
            "total_content_types": len(result)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"컨텐츠 타입 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/hierarchy")
async def get_category_hierarchy(
    content_type_id: str = None,
    db: Session = Depends(get_db),
    _: dict = Depends(require_super_admin)
):
    """
    카테고리 계층 구조 조회
    """
    try:
        # 1차 카테고리 조회
        level1_query = db.query(CategoryCode).filter(CategoryCode.category_level == 1)
        level1_categories = level1_query.all()
        
        # 2차 카테고리 조회
        level2_query = db.query(CategoryCode).filter(CategoryCode.category_level == 2)
        if content_type_id:
            level2_query = level2_query.filter(CategoryCode.content_type_id == content_type_id)
        level2_categories = level2_query.all()
        
        # 계층 구조 구성
        hierarchy = []
        for level1 in level1_categories:
            children = [
                {
                    "category_code": child.category_code,
                    "category_name": child.category_name,
                    "content_type_id": child.content_type_id,
                } for child in level2_categories 
                if child.parent_category_code == level1.category_code
            ]
            
            # 해당 컨텐츠 타입 필터링 시 자식이 있는 경우만 포함
            if content_type_id is None or children:
                hierarchy.append({
                    "category_code": level1.category_code,
                    "category_name": level1.category_name,
                    "children": children
                })
        
        return {
            "hierarchy": hierarchy,
            "content_type_id": content_type_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"카테고리 계층 구조 조회 중 오류가 발생했습니다: {str(e)}"
        )