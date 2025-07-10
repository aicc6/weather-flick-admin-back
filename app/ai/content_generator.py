"""
AI 기반 콘텐츠 생성 시스템
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import (
    Destination,
    Review,
    TravelPlan,
    Weather,
)
from app.utils.async_processing import AsyncBatch

logger = get_logger("content_generator")


class ContentType(Enum):
    """콘텐츠 유형"""

    TRAVEL_GUIDE = "travel_guide"
    DESTINATION_DESCRIPTION = "destination_description"
    ITINERARY_SUGGESTION = "itinerary_suggestion"
    TRAVEL_TIP = "travel_tip"
    WEATHER_ADVICE = "weather_advice"
    CULTURAL_INSIGHT = "cultural_insight"
    FOOD_RECOMMENDATION = "food_recommendation"
    SAFETY_INFORMATION = "safety_information"
    BUDGET_ADVICE = "budget_advice"
    SEASONAL_CONTENT = "seasonal_content"


class ContentStyle(Enum):
    """콘텐츠 스타일"""

    FORMAL = "formal"
    CASUAL = "casual"
    ENTHUSIASTIC = "enthusiastic"
    INFORMATIVE = "informative"
    PERSONAL = "personal"
    PROFESSIONAL = "professional"


@dataclass
class ContentRequest:
    """콘텐츠 생성 요청"""

    content_type: ContentType
    style: ContentStyle
    target_audience: str
    destination_id: str | None = None
    user_id: str | None = None
    context: dict[str, Any] | None = None
    length: str = "medium"  # short, medium, long
    language: str = "ko"


@dataclass
class GeneratedContent:
    """생성된 콘텐츠"""

    content_id: str
    title: str
    content: str
    content_type: ContentType
    style: ContentStyle
    metadata: dict[str, Any]
    quality_score: float
    created_at: datetime
    expires_at: datetime | None = None


class TravelGuideGenerator:
    """여행 가이드 생성기"""

    def __init__(self, db: Session):
        self.db = db

    async def generate_destination_guide(
        self, destination_id: str, user_context: dict[str, Any] | None = None
    ) -> GeneratedContent:
        """목적지 가이드 생성"""
        try:
            # 목적지 정보 수집
            destination = (
                self.db.query(Destination)
                .filter(Destination.destination_id == destination_id)
                .first()
            )

            if not destination:
                raise ValueError(f"Destination not found: {destination_id}")

            # 리뷰 데이터 수집
            reviews = (
                self.db.query(Review)
                .filter(Review.destination_id == destination_id)
                .order_by(desc(Review.rating))
                .limit(10)
                .all()
            )

            # 날씨 정보 수집
            weather_data = await self._get_weather_context(destination)

            # 사용자 맞춤 정보
            user_preferences = user_context or {}

            # 가이드 콘텐츠 생성
            guide_content = await self._create_destination_guide_content(
                destination, reviews, weather_data, user_preferences
            )

            return GeneratedContent(
                content_id=f"guide_{destination_id}_{int(datetime.now().timestamp())}",
                title=f"{destination.name} 여행 가이드",
                content=guide_content,
                content_type=ContentType.TRAVEL_GUIDE,
                style=ContentStyle.INFORMATIVE,
                metadata={
                    "destination_id": destination_id,
                    "review_count": len(reviews),
                    "avg_rating": (
                        sum(r.rating for r in reviews if r.rating) / len(reviews)
                        if reviews
                        else 0
                    ),
                    "weather_included": bool(weather_data),
                },
                quality_score=0.85,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=30),
            )

        except Exception as e:
            logger.error(f"Error generating destination guide: {e}")
            raise

    async def _get_weather_context(self, destination: Destination) -> dict[str, Any]:
        """날씨 컨텍스트 수집"""
        try:
            # 최근 날씨 데이터 조회
            recent_weather = (
                self.db.query(Weather)
                .filter(
                    and_(
                        Weather.region == destination.region,
                        Weather.date >= datetime.now() - timedelta(days=7),
                    )
                )
                .order_by(desc(Weather.date))
                .first()
            )

            if recent_weather:
                return {
                    "temperature": recent_weather.temperature,
                    "humidity": recent_weather.humidity,
                    "precipitation": recent_weather.precipitation,
                    "weather_condition": recent_weather.weather_condition,
                    "last_updated": recent_weather.date.isoformat(),
                }

            return {}

        except Exception as e:
            logger.error(f"Error getting weather context: {e}")
            return {}

    async def _create_destination_guide_content(
        self,
        destination: Destination,
        reviews: list[Review],
        weather_data: dict[str, Any],
        user_preferences: dict[str, Any],
    ) -> str:
        """목적지 가이드 콘텐츠 생성"""
        try:
            # 기본 정보 섹션
            basic_info = f"""
# {destination.name} 여행 가이드

## 기본 정보
- **위치**: {destination.region}
- **카테고리**: {destination.category}
- **주소**: {destination.address or '정보 없음'}
"""

            # 리뷰 기반 하이라이트
            review_highlights = ""
            if reviews:
                top_reviews = [r for r in reviews if r.rating and r.rating >= 4.0][:3]
                if top_reviews:
                    review_highlights = "\n## 방문객 추천 포인트\n"
                    for i, review in enumerate(top_reviews, 1):
                        content = (review.content or "좋은 경험이었습니다")[:100]
                        review_highlights += (
                            f"{i}. {content}... (평점: {review.rating}/5)\n"
                        )

            # 날씨 정보
            weather_section = ""
            if weather_data:
                weather_section = f"""
## 현재 날씨 정보
- **기온**: {weather_data.get('temperature', 'N/A')}°C
- **습도**: {weather_data.get('humidity', 'N/A')}%
- **강수량**: {weather_data.get('precipitation', 'N/A')}mm
- **날씨**: {weather_data.get('weather_condition', '정보 없음')}
"""

            # 맞춤 추천 사항
            personalized_tips = ""
            if user_preferences:
                personalized_tips = "\n## 맞춤 추천 사항\n"

                if user_preferences.get("travel_style") == "adventure":
                    personalized_tips += "- 모험을 좋아하시는 분께 특별히 추천드리는 액티비티들을 찾아보세요.\n"
                elif user_preferences.get("travel_style") == "relaxation":
                    personalized_tips += "- 휴식과 힐링이 필요하신 분께 이곳의 조용한 명소들을 추천합니다.\n"

                if user_preferences.get("budget_range"):
                    budget = user_preferences["budget_range"]
                    if budget == "low":
                        personalized_tips += "- 합리적인 가격으로 즐길 수 있는 옵션들을 우선적으로 소개합니다.\n"
                    elif budget == "high":
                        personalized_tips += (
                            "- 프리미엄 경험과 서비스를 중심으로 안내해드립니다.\n"
                        )

            # 방문 팁
            visit_tips = f"""
## 방문 팁
- **최적 방문 시간**: {self._get_best_visit_time(destination)}
- **소요 시간**: {self._estimate_visit_duration(destination)}
- **접근성**: {self._get_accessibility_info(destination)}
- **주의사항**: {self._get_safety_tips(destination)}
"""

            # 전체 콘텐츠 조합
            full_content = (
                basic_info
                + review_highlights
                + weather_section
                + personalized_tips
                + visit_tips
            )

            return full_content.strip()

        except Exception as e:
            logger.error(f"Error creating guide content: {e}")
            return f"# {destination.name}\n\n기본 정보만 제공됩니다. 자세한 정보는 곧 업데이트될 예정입니다."

    def _get_best_visit_time(self, destination: Destination) -> str:
        """최적 방문 시간 추천"""
        category_times = {
            "관광지": "오전 9시~오후 5시",
            "음식점": "오전 11시~오후 9시",
            "숙박": "체크인 시간 확인 필요",
            "쇼핑": "오전 10시~오후 8시",
            "문화시설": "오전 9시~오후 6시",
            "레저": "날씨에 따라 상이",
        }
        return category_times.get(destination.category, "운영시간 확인 필요")

    def _estimate_visit_duration(self, destination: Destination) -> str:
        """방문 소요 시간 추정"""
        category_durations = {
            "관광지": "2~3시간",
            "음식점": "1~2시간",
            "숙박": "숙박 기간에 따라",
            "쇼핑": "1~4시간",
            "문화시설": "1~2시간",
            "레저": "반나절~하루",
        }
        return category_durations.get(destination.category, "방문 목적에 따라")

    def _get_accessibility_info(self, destination: Destination) -> str:
        """접근성 정보"""
        # 실제로는 더 상세한 교통 정보 제공
        return "대중교통 이용 가능, 자세한 교통편은 지도 앱 확인 권장"

    def _get_safety_tips(self, destination: Destination) -> str:
        """안전 정보"""
        general_tips = [
            "귀중품 관리에 주의하세요",
            "날씨 변화에 대비하세요",
            "현지 상황을 미리 확인하세요",
        ]
        return ", ".join(random.sample(general_tips, 2))


class ItineraryGenerator:
    """여행 일정 생성기"""

    def __init__(self, db: Session):
        self.db = db

    async def generate_smart_itinerary(
        self, user_id: str, region: str, duration_days: int, preferences: dict[str, Any]
    ) -> GeneratedContent:
        """스마트 여행 일정 생성"""
        try:
            # 지역 내 추천 목적지 수집
            destinations = self._get_regional_destinations(region, preferences)

            # 사용자 선호도 분석
            user_profile = await self._analyze_user_preferences(user_id)

            # 일정 최적화
            optimized_itinerary = await self._optimize_itinerary(
                destinations, duration_days, user_profile, preferences
            )

            # 일정 콘텐츠 생성
            itinerary_content = await self._create_itinerary_content(
                optimized_itinerary, region, duration_days
            )

            return GeneratedContent(
                content_id=f"itinerary_{user_id}_{int(datetime.now().timestamp())}",
                title=f"{region} {duration_days}일 여행 일정",
                content=itinerary_content,
                content_type=ContentType.ITINERARY_SUGGESTION,
                style=ContentStyle.PERSONAL,
                metadata={
                    "user_id": user_id,
                    "region": region,
                    "duration_days": duration_days,
                    "destination_count": len(optimized_itinerary),
                    "preferences": preferences,
                },
                quality_score=0.80,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=7),
            )

        except Exception as e:
            logger.error(f"Error generating itinerary: {e}")
            raise

    def _get_regional_destinations(
        self, region: str, preferences: dict[str, Any]
    ) -> list[Destination]:
        """지역 내 목적지 수집"""
        try:
            query = self.db.query(Destination).filter(Destination.region == region)

            # 카테고리 선호도 필터링
            if preferences.get("preferred_categories"):
                categories = preferences["preferred_categories"]
                query = query.filter(Destination.category.in_(categories))

            destinations = query.limit(20).all()

            # 평점 기반 정렬
            destinations_with_ratings = []
            for dest in destinations:
                reviews = (
                    self.db.query(Review)
                    .filter(Review.destination_id == dest.destination_id)
                    .all()
                )

                if reviews:
                    avg_rating = sum(r.rating for r in reviews if r.rating) / len(
                        reviews
                    )
                    destinations_with_ratings.append((dest, avg_rating))
                else:
                    destinations_with_ratings.append((dest, 3.0))  # 기본 평점

            # 평점 기준 정렬
            destinations_with_ratings.sort(key=lambda x: x[1], reverse=True)

            return [dest for dest, rating in destinations_with_ratings]

        except Exception as e:
            logger.error(f"Error getting regional destinations: {e}")
            return []

    async def _analyze_user_preferences(self, user_id: str) -> dict[str, Any]:
        """사용자 선호도 분석"""
        try:
            # 과거 여행 패턴 분석
            past_plans = (
                self.db.query(TravelPlan)
                .filter(TravelPlan.user_id == user_id)
                .order_by(desc(TravelPlan.created_at))
                .limit(10)
                .all()
            )

            # 리뷰 패턴 분석
            past_reviews = (
                self.db.query(Review)
                .filter(Review.user_id == user_id)
                .order_by(desc(Review.created_at))
                .limit(20)
                .all()
            )

            profile = {
                "avg_trip_duration": 3,  # 기본값
                "preferred_categories": [],
                "activity_level": "medium",
                "budget_preference": "medium",
                "review_tendency": "positive",
            }

            if past_plans:
                # 평균 여행 기간 계산
                durations = []
                for plan in past_plans:
                    if plan.end_date and plan.start_date:
                        duration = (plan.end_date - plan.start_date).days
                        durations.append(duration)

                if durations:
                    profile["avg_trip_duration"] = sum(durations) / len(durations)

            if past_reviews:
                # 선호 카테고리 분석
                category_counts = {}
                total_rating = 0

                for review in past_reviews:
                    if review.rating:
                        total_rating += review.rating

                        # 목적지 카테고리 조회
                        destination = (
                            self.db.query(Destination)
                            .filter(Destination.destination_id == review.destination_id)
                            .first()
                        )

                        if destination:
                            category = destination.category
                            category_counts[category] = (
                                category_counts.get(category, 0) + 1
                            )

                # 상위 카테고리 추출
                sorted_categories = sorted(
                    category_counts.items(), key=lambda x: x[1], reverse=True
                )
                profile["preferred_categories"] = [
                    cat for cat, count in sorted_categories[:3]
                ]

                # 평점 성향
                avg_rating = total_rating / len(past_reviews)
                if avg_rating >= 4.0:
                    profile["review_tendency"] = "positive"
                elif avg_rating <= 3.0:
                    profile["review_tendency"] = "critical"
                else:
                    profile["review_tendency"] = "balanced"

            return profile

        except Exception as e:
            logger.error(f"Error analyzing user preferences: {e}")
            return {}

    async def _optimize_itinerary(
        self,
        destinations: list[Destination],
        duration_days: int,
        user_profile: dict[str, Any],
        preferences: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """일정 최적화"""
        try:
            # 하루당 방문할 목적지 수 계산
            destinations_per_day = min(3, max(1, len(destinations) // duration_days))

            # 일정 구성
            itinerary = []
            used_destinations = set()

            for day in range(1, duration_days + 1):
                day_plan = {
                    "day": day,
                    "destinations": [],
                    "theme": self._get_day_theme(day, duration_days, user_profile),
                }

                # 하루 일정용 목적지 선택
                for i in range(destinations_per_day):
                    available_destinations = [
                        dest
                        for dest in destinations
                        if dest.destination_id not in used_destinations
                    ]

                    if not available_destinations:
                        break

                    # 테마에 맞는 목적지 우선 선택
                    selected_dest = self._select_destination_for_theme(
                        available_destinations, day_plan["theme"], preferences
                    )

                    if selected_dest:
                        day_plan["destinations"].append(
                            {
                                "destination": selected_dest,
                                "estimated_time": self._estimate_visit_time(
                                    selected_dest
                                ),
                                "order": i + 1,
                            }
                        )
                        used_destinations.add(selected_dest.destination_id)

                itinerary.append(day_plan)

            return itinerary

        except Exception as e:
            logger.error(f"Error optimizing itinerary: {e}")
            return []

    def _get_day_theme(
        self, day: int, total_days: int, user_profile: dict[str, Any]
    ) -> str:
        """일차별 테마 결정"""
        if total_days == 1:
            return "highlights"
        elif day == 1:
            return "arrival_exploration"
        elif day == total_days:
            return "departure_shopping"
        elif day <= total_days // 2:
            return "cultural_sightseeing"
        else:
            return "leisure_experience"

    def _select_destination_for_theme(
        self, destinations: list[Destination], theme: str, preferences: dict[str, Any]
    ) -> Destination | None:
        """테마에 맞는 목적지 선택"""
        theme_categories = {
            "arrival_exploration": ["관광지", "문화시설"],
            "cultural_sightseeing": ["문화시설", "관광지"],
            "leisure_experience": ["레저", "쇼핑"],
            "departure_shopping": ["쇼핑", "음식점"],
            "highlights": ["관광지"],
        }

        preferred_categories = theme_categories.get(theme, ["관광지"])

        # 테마에 맞는 카테고리 우선 선택
        for category in preferred_categories:
            category_destinations = [d for d in destinations if d.category == category]
            if category_destinations:
                return category_destinations[0]

        # 테마에 맞는 것이 없으면 첫 번째 목적지 반환
        return destinations[0] if destinations else None

    def _estimate_visit_time(self, destination: Destination) -> str:
        """방문 소요 시간 추정"""
        time_estimates = {
            "관광지": "2-3시간",
            "음식점": "1-2시간",
            "쇼핑": "1-2시간",
            "문화시설": "1.5-2.5시간",
            "레저": "3-4시간",
            "숙박": "숙박",
        }
        return time_estimates.get(destination.category, "1-2시간")

    async def _create_itinerary_content(
        self, itinerary: list[dict[str, Any]], region: str, duration_days: int
    ) -> str:
        """일정 콘텐츠 생성"""
        try:
            content = f"# {region} {duration_days}일 여행 일정\n\n"
            content += f"**총 여행 기간**: {duration_days}일\n"
            content += f"**여행 지역**: {region}\n\n"

            for day_plan in itinerary:
                day = day_plan["day"]
                theme = day_plan["theme"]
                destinations = day_plan["destinations"]

                content += f"## Day {day} - {self._translate_theme(theme)}\n\n"

                for i, dest_info in enumerate(destinations, 1):
                    destination = dest_info["destination"]
                    estimated_time = dest_info["estimated_time"]

                    content += f"### {i}. {destination.name}\n"
                    content += f"- **카테고리**: {destination.category}\n"
                    content += f"- **예상 소요시간**: {estimated_time}\n"
                    content += (
                        f"- **주소**: {destination.address or '주소 정보 없음'}\n"
                    )

                    # 간단한 설명 추가
                    content += (
                        f"- **설명**: {self._get_simple_description(destination)}\n\n"
                    )

            content += "\n## 여행 팁\n"
            content += "- 교통편과 운영시간을 미리 확인하세요\n"
            content += "- 날씨에 따라 일정 순서를 조정할 수 있습니다\n"
            content += "- 현지 상황에 따라 유연하게 대응하세요\n"

            return content

        except Exception as e:
            logger.error(f"Error creating itinerary content: {e}")
            return f"# {region} {duration_days}일 여행 일정\n\n일정 생성 중 오류가 발생했습니다."

    def _translate_theme(self, theme: str) -> str:
        """테마 번역"""
        theme_translations = {
            "arrival_exploration": "도착 후 탐방",
            "cultural_sightseeing": "문화 관광",
            "leisure_experience": "레저 체험",
            "departure_shopping": "출발 전 쇼핑",
            "highlights": "하이라이트 코스",
        }
        return theme_translations.get(theme, "자유 일정")

    def _get_simple_description(self, destination: Destination) -> str:
        """간단한 설명 생성"""
        category_descriptions = {
            "관광지": "아름다운 풍경과 역사를 감상할 수 있는 곳",
            "음식점": "현지의 맛있는 음식을 경험할 수 있는 곳",
            "쇼핑": "다양한 상품과 기념품을 구매할 수 있는 곳",
            "문화시설": "지역 문화와 예술을 체험할 수 있는 곳",
            "레저": "액티비티와 여가를 즐길 수 있는 곳",
            "숙박": "편안한 휴식을 취할 수 있는 곳",
        }
        return category_descriptions.get(destination.category, "방문할 가치가 있는 곳")


class ContentGenerator:
    """AI 콘텐츠 생성 메인 클래스"""

    def __init__(self, db: Session):
        self.db = db
        self.guide_generator = TravelGuideGenerator(db)
        self.itinerary_generator = ItineraryGenerator(db)
        self.batch_processor = AsyncBatch(batch_size=10, max_concurrent=3)

    async def generate_content(self, request: ContentRequest) -> GeneratedContent:
        """콘텐츠 생성"""
        try:
            if request.content_type == ContentType.TRAVEL_GUIDE:
                return await self.guide_generator.generate_destination_guide(
                    request.destination_id, request.context
                )
            elif request.content_type == ContentType.ITINERARY_SUGGESTION:
                context = request.context or {}
                return await self.itinerary_generator.generate_smart_itinerary(
                    request.user_id,
                    context.get("region", "서울"),
                    context.get("duration_days", 3),
                    context.get("preferences", {}),
                )
            elif request.content_type == ContentType.TRAVEL_TIP:
                return await self._generate_travel_tip(request)
            elif request.content_type == ContentType.WEATHER_ADVICE:
                return await self._generate_weather_advice(request)
            elif request.content_type == ContentType.SEASONAL_CONTENT:
                return await self._generate_seasonal_content(request)
            else:
                return await self._generate_generic_content(request)

        except Exception as e:
            logger.error(f"Error generating content: {e}")
            raise

    async def _generate_travel_tip(self, request: ContentRequest) -> GeneratedContent:
        """여행 팁 생성"""
        try:
            destination_id = request.destination_id
            context = request.context or {}

            # 목적지 정보 수집
            destination = None
            if destination_id:
                destination = (
                    self.db.query(Destination)
                    .filter(Destination.destination_id == destination_id)
                    .first()
                )

            # 팁 콘텐츠 생성
            tips_content = await self._create_travel_tips_content(destination, context)

            title = f"{destination.name} 여행 팁" if destination else "여행 팁"

            return GeneratedContent(
                content_id=f"tips_{destination_id or 'general'}_{int(datetime.now().timestamp())}",
                title=title,
                content=tips_content,
                content_type=ContentType.TRAVEL_TIP,
                style=request.style,
                metadata={
                    "destination_id": destination_id,
                    "tip_count": tips_content.count("\n- "),
                    "context": context,
                },
                quality_score=0.75,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=14),
            )

        except Exception as e:
            logger.error(f"Error generating travel tip: {e}")
            raise

    async def _create_travel_tips_content(
        self, destination: Destination | None, context: dict[str, Any]
    ) -> str:
        """여행 팁 콘텐츠 생성"""
        try:
            if destination:
                content = f"# {destination.name} 여행 팁\n\n"

                # 카테고리별 맞춤 팁
                category_tips = {
                    "관광지": [
                        "이른 아침이나 늦은 오후에 방문하면 인파를 피할 수 있습니다",
                        "카메라 배터리와 메모리 카드를 충분히 준비하세요",
                        "편한 신발을 착용하는 것을 추천합니다",
                    ],
                    "음식점": [
                        "현지 인기 메뉴를 미리 알아보고 방문하세요",
                        "피크 시간을 피해 방문하면 더 여유롭게 식사할 수 있습니다",
                        "알레르기가 있다면 미리 확인하세요",
                    ],
                    "쇼핑": [
                        "가격 비교를 통해 합리적인 구매를 하세요",
                        "현금과 카드를 모두 준비하세요",
                        "면세점 이용 시 여권을 꼭 지참하세요",
                    ],
                    "문화시설": [
                        "운영시간과 휴관일을 미리 확인하세요",
                        "할인 혜택이나 패키지를 알아보세요",
                        "조용한 관람 매너를 지켜주세요",
                    ],
                    "레저": [
                        "날씨와 계절을 고려해 적절한 복장을 준비하세요",
                        "안전 장비와 주의사항을 반드시 확인하세요",
                        "사전 예약이 필요한지 확인하세요",
                    ],
                }

                tips = category_tips.get(
                    destination.category,
                    [
                        "방문 전 운영시간을 확인하세요",
                        "현지 상황을 미리 알아보세요",
                        "충분한 시간을 확보하고 방문하세요",
                    ],
                )

                content += "## 추천 팁\n"
                for tip in tips:
                    content += f"- {tip}\n"

            else:
                content = "# 일반 여행 팁\n\n"
                content += "## 여행 전 준비사항\n"
                content += "- 여행 일정과 교통편을 미리 확인하세요\n"
                content += "- 날씨 예보를 체크하고 적절한 옷을 준비하세요\n"
                content += "- 필요한 서류와 물품을 체크리스트로 관리하세요\n\n"

                content += "## 여행 중 주의사항\n"
                content += "- 귀중품 관리에 특별히 주의하세요\n"
                content += "- 현지 문화와 관습을 존중하세요\n"
                content += "- 응급상황에 대비해 연락처를 준비하세요\n"

            return content

        except Exception as e:
            logger.error(f"Error creating travel tips content: {e}")
            return "# 여행 팁\n\n여행을 계획할 때는 안전과 준비가 가장 중요합니다."

    async def _generate_weather_advice(
        self, request: ContentRequest
    ) -> GeneratedContent:
        """날씨 조언 생성"""
        try:
            context = request.context or {}
            region = context.get("region", "전국")

            # 최근 날씨 데이터 조회
            recent_weather = (
                self.db.query(Weather)
                .filter(Weather.region == region)
                .order_by(desc(Weather.date))
                .first()
            )

            # 날씨 조언 콘텐츠 생성
            advice_content = await self._create_weather_advice_content(
                recent_weather, context
            )

            return GeneratedContent(
                content_id=f"weather_{region}_{int(datetime.now().timestamp())}",
                title=f"{region} 날씨별 여행 조언",
                content=advice_content,
                content_type=ContentType.WEATHER_ADVICE,
                style=request.style,
                metadata={
                    "region": region,
                    "weather_data": bool(recent_weather),
                    "context": context,
                },
                quality_score=0.70,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=3),
            )

        except Exception as e:
            logger.error(f"Error generating weather advice: {e}")
            raise

    async def _create_weather_advice_content(
        self, weather: Weather | None, context: dict[str, Any]
    ) -> str:
        """날씨 조언 콘텐츠 생성"""
        try:
            region = context.get("region", "전국")
            content = f"# {region} 날씨별 여행 조언\n\n"

            if weather:
                content += "## 현재 날씨 상황\n"
                content += f"- **날짜**: {weather.date.strftime('%Y-%m-%d')}\n"
                content += f"- **기온**: {weather.temperature}°C\n"
                content += f"- **습도**: {weather.humidity}%\n"
                content += f"- **강수량**: {weather.precipitation}mm\n"
                content += f"- **날씨**: {weather.weather_condition}\n\n"

                # 날씨별 조언
                temp = weather.temperature
                if temp >= 28:
                    content += "## 더운 날씨 대비 조언\n"
                    content += "- 충분한 수분 섭취를 하세요\n"
                    content += "- 자외선 차단제를 꼭 발라주세요\n"
                    content += "- 시원한 실내 장소를 이용하세요\n"
                elif temp <= 5:
                    content += "## 추운 날씨 대비 조언\n"
                    content += "- 보온을 위한 겹겹이 입기를 추천합니다\n"
                    content += "- 미끄럼 방지 신발을 착용하세요\n"
                    content += "- 따뜻한 음료를 준비하세요\n"
                else:
                    content += "## 적정 날씨 조언\n"
                    content += "- 야외 활동하기 좋은 날씨입니다\n"
                    content += "- 가벼운 외투를 준비하세요\n"
                    content += "- 다양한 활동을 계획해보세요\n"

                if weather.precipitation > 5:
                    content += "\n## 비 대비 조언\n"
                    content += "- 우산이나 우비를 준비하세요\n"
                    content += "- 실내 관광지를 우선 고려하세요\n"
                    content += "- 미끄러운 길에 주의하세요\n"

            else:
                content += "## 일반적인 날씨 대비 조언\n"
                content += "- 여행 전 일기예보를 확인하세요\n"
                content += "- 다양한 날씨에 대비한 옷을 준비하세요\n"
                content += "- 실내외 활동을 균형있게 계획하세요\n"

            return content

        except Exception as e:
            logger.error(f"Error creating weather advice content: {e}")
            return f"# {region} 날씨 조언\n\n여행 전 날씨를 확인하고 적절히 준비하세요."

    async def _generate_seasonal_content(
        self, request: ContentRequest
    ) -> GeneratedContent:
        """계절별 콘텐츠 생성"""
        try:
            current_month = datetime.now().month
            season = self._get_season(current_month)
            context = request.context or {}

            # 계절별 콘텐츠 생성
            seasonal_content = await self._create_seasonal_content(season, context)

            return GeneratedContent(
                content_id=f"seasonal_{season}_{int(datetime.now().timestamp())}",
                title=f"{season} 여행 추천",
                content=seasonal_content,
                content_type=ContentType.SEASONAL_CONTENT,
                style=request.style,
                metadata={"season": season, "month": current_month, "context": context},
                quality_score=0.80,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=30),
            )

        except Exception as e:
            logger.error(f"Error generating seasonal content: {e}")
            raise

    def _get_season(self, month: int) -> str:
        """계절 판단"""
        if month in [12, 1, 2]:
            return "겨울"
        elif month in [3, 4, 5]:
            return "봄"
        elif month in [6, 7, 8]:
            return "여름"
        else:
            return "가을"

    async def _create_seasonal_content(
        self, season: str, context: dict[str, Any]
    ) -> str:
        """계절별 콘텐츠 생성"""
        try:
            content = f"# {season} 여행 추천\n\n"

            seasonal_info = {
                "봄": {
                    "특징": "따뜻한 날씨와 벚꽃이 아름다운 계절",
                    "추천활동": ["벚꽃 명소 탐방", "야외 피크닉", "등산", "사진 촬영"],
                    "주의사항": [
                        "일교차가 클 수 있으니 겹겹이 입기",
                        "꽃가루 알레르기 주의",
                    ],
                    "준비물": ["가벼운 외투", "선크림", "카메라"],
                },
                "여름": {
                    "특징": "더위와 휴가철이 겹치는 활동적인 계절",
                    "추천활동": ["해수욕", "물놀이", "여름 축제", "피서지 방문"],
                    "주의사항": ["자외선 차단", "충분한 수분 섭취", "폭염 주의"],
                    "준비물": ["선크림", "모자", "충분한 물", "시원한 옷"],
                },
                "가을": {
                    "특징": "단풍과 선선한 날씨가 매력적인 계절",
                    "추천활동": ["단풍 구경", "등산", "수확 체험", "야외 활동"],
                    "주의사항": ["일교차 주의", "건조한 날씨 대비"],
                    "준비물": ["얇은 외투", "보습제", "편한 신발"],
                },
                "겨울": {
                    "특징": "추위와 함께 겨울 스포츠를 즐길 수 있는 계절",
                    "추천활동": ["스키", "온천", "겨울 축제", "실내 관광"],
                    "주의사항": ["방한 대비", "빙판길 주의", "실내외 온도차"],
                    "준비물": ["두꺼운 외투", "장갑", "목도리", "방한용 신발"],
                },
            }

            info = seasonal_info.get(season, seasonal_info["봄"])

            content += f"## {season}의 특징\n"
            content += f"{info['특징']}\n\n"

            content += "## 추천 활동\n"
            for activity in info["추천활동"]:
                content += f"- {activity}\n"
            content += "\n"

            content += "## 주의사항\n"
            for note in info["주의사항"]:
                content += f"- {note}\n"
            content += "\n"

            content += "## 준비물\n"
            for item in info["준비물"]:
                content += f"- {item}\n"

            return content

        except Exception as e:
            logger.error(f"Error creating seasonal content: {e}")
            return f"# {season} 여행\n\n{season}에 맞는 여행을 계획해보세요."

    async def _generate_generic_content(
        self, request: ContentRequest
    ) -> GeneratedContent:
        """일반 콘텐츠 생성"""
        try:
            content_type = request.content_type.value
            content = f"# {content_type} 콘텐츠\n\n"
            content += "곧 더 자세한 정보가 제공될 예정입니다.\n"
            content += "현재는 기본 정보만 제공됩니다."

            return GeneratedContent(
                content_id=f"generic_{content_type}_{int(datetime.now().timestamp())}",
                title=f"{content_type} 정보",
                content=content,
                content_type=request.content_type,
                style=request.style,
                metadata={"generic": True},
                quality_score=0.50,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=7),
            )

        except Exception as e:
            logger.error(f"Error generating generic content: {e}")
            raise

    async def batch_generate_content(
        self, requests: list[ContentRequest]
    ) -> list[GeneratedContent]:
        """배치 콘텐츠 생성"""
        try:
            results = await self.batch_processor.process_batch(
                requests, self.generate_content
            )

            # 성공한 결과만 반환
            successful_results = [
                result for result in results if isinstance(result, GeneratedContent)
            ]

            return successful_results

        except Exception as e:
            logger.error(f"Error in batch content generation: {e}")
            return []

    def get_content_statistics(self) -> dict[str, Any]:
        """콘텐츠 생성 통계"""
        # 실제 구현에서는 데이터베이스에서 통계 조회
        return {
            "total_generated": 0,
            "by_type": {},
            "by_style": {},
            "avg_quality_score": 0.0,
            "generation_rate": 0.0,
        }


# 콘텐츠 생성 시스템 싱글톤
content_generator = None


def get_content_generator(db: Session) -> ContentGenerator:
    """콘텐츠 생성 시스템 인스턴스 반환"""
    global content_generator
    if content_generator is None:
        content_generator = ContentGenerator(db)
    return content_generator


logger.info("AI content generation system initialized")
