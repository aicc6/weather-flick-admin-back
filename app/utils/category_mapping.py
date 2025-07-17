"""
카테고리 매핑 유틸리티
"""

# 관광지 카테고리 코드 매핑
CATEGORY_CODE_MAPPING = {
    # 한국관광공사 API 기본 카테고리
    'AC': '숙박',
    'C01': '추천코스',
    'EV': '축제/공연/행사',
    'EX': '체험관광',
    'FD': '음식',
    'HS': '역사관광',
    'LS': '레저스포츠',
    'NA': '자연관광',
    'SH': '쇼핑',
    'VE': '문화관광',
    
    # 추가 호환성을 위한 매핑
    'A01': '자연관광',
    'A02': '문화관광',
    'A03': '레저스포츠',
    'A04': '쇼핑',
    'A05': '음식',
    'B01': '숙박',
    'B02': '축제/공연/행사',
    'C02': '가족코스',
    'C03': '나홀로코스',
    'C04': '커플코스',
    'C05': '친구코스',
}

# 카테고리 설명 매핑
CATEGORY_DESCRIPTION_MAPPING = {
    'AC': '호텔, 펜션, 민박 등 숙박시설',
    'C01': '추천 여행 코스 및 루트',
    'EV': '축제, 공연, 각종 이벤트',
    'EX': '체험활동 및 프로그램',
    'FD': '음식점, 카페, 맛집',
    'HS': '역사적 장소 및 문화재',
    'LS': '스포츠 및 레크리에이션',
    'NA': '자연 경관 및 관광지',
    'SH': '쇼핑몰, 시장, 상점',
    'VE': '박물관, 미술관, 문화시설',
    
    # 추가 매핑
    'A01': '자연 경관 및 관광지',
    'A02': '박물관, 미술관, 문화시설',
    'A03': '스포츠 및 레크리에이션',
    'A04': '쇼핑몰, 시장, 상점',
    'A05': '음식점, 카페, 맛집',
    'B01': '호텔, 펜션, 민박 등 숙박시설',
    'B02': '축제, 공연, 각종 이벤트',
    'C02': '가족 단위 여행 코스',
    'C03': '혼자 여행하기 좋은 코스',
    'C04': '커플 여행 코스',
    'C05': '친구들과 함께하는 여행 코스',
}

def get_category_name(category_code: str) -> str:
    """카테고리 코드로 카테고리 이름 조회"""
    return CATEGORY_CODE_MAPPING.get(category_code, category_code or '미분류')

def get_category_description(category_code: str) -> str:
    """카테고리 코드로 카테고리 설명 조회"""
    return CATEGORY_DESCRIPTION_MAPPING.get(category_code, '카테고리 설명 없음')

def normalize_category_data(category_code: str, category_name: str = None) -> dict:
    """카테고리 데이터 정규화"""
    normalized_name = category_name or get_category_name(category_code)
    description = get_category_description(category_code)
    
    return {
        'category_code': category_code,
        'category_name': normalized_name,
        'category_description': description,
        'is_mapped': category_code in CATEGORY_CODE_MAPPING
    }

def get_main_categories() -> list:
    """주요 카테고리 목록 반환 (빈도 기준)"""
    return [
        {'code': 'SH', 'name': '쇼핑', 'description': '쇼핑몰, 시장, 상점'},
        {'code': 'VE', 'name': '문화관광', 'description': '박물관, 미술관, 문화시설'},
        {'code': 'HS', 'name': '역사관광', 'description': '역사적 장소 및 문화재'},
        {'code': 'NA', 'name': '자연관광', 'description': '자연 경관 및 관광지'},
        {'code': 'EX', 'name': '체험관광', 'description': '체험활동 및 프로그램'},
        {'code': 'C01', 'name': '추천코스', 'description': '추천 여행 코스 및 루트'},
        {'code': 'AC', 'name': '숙박', 'description': '호텔, 펜션, 민박 등 숙박시설'},
        {'code': 'LS', 'name': '레저스포츠', 'description': '스포츠 및 레크리에이션'},
    ]

def get_category_stats() -> dict:
    """카테고리별 통계 정보 반환"""
    return {
        'total_categories': len(CATEGORY_CODE_MAPPING),
        'main_categories': len(get_main_categories()),
        'categories': CATEGORY_CODE_MAPPING,
        'main_category_codes': [cat['code'] for cat in get_main_categories()]
    }