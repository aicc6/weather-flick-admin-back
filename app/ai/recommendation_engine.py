"""
AI 기반 여행 추천 시스템
"""

from datetime import datetime
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Destination, Review, TravelPlan, User, UserPreference

logger = get_logger("ai_recommendation")


class UserProfile:
    """사용자 프로필 분석"""

    def __init__(self, user_id: str, db: Session):
        self.user_id = user_id
        self.db = db
        self.profile_data = self._build_profile()

    def _build_profile(self) -> dict[str, Any]:
        """사용자 프로필 구축"""
        try:
            # 기본 사용자 정보
            user = self.db.query(User).filter(User.user_id == self.user_id).first()
            if not user:
                return {}

            # 사용자 선호도 정보
            preferences = (
                self.db.query(UserPreference)
                .filter(UserPreference.user_id == self.user_id)
                .first()
            )

            # 여행 계획 분석
            travel_plans = (
                self.db.query(TravelPlan)
                .filter(TravelPlan.user_id == self.user_id)
                .all()
            )

            # 리뷰 분석
            reviews = self.db.query(Review).filter(Review.user_id == self.user_id).all()

            profile = {
                "user_id": self.user_id,
                "basic_info": {
                    "preferred_region": user.preferred_region,
                    "preferred_theme": user.preferred_theme,
                    "created_at": user.created_at,
                },
                "preferences": self._analyze_preferences(preferences),
                "travel_history": self._analyze_travel_history(travel_plans),
                "review_patterns": self._analyze_review_patterns(reviews),
                "behavioral_score": self._calculate_behavioral_score(
                    travel_plans, reviews
                ),
            }

            return profile

        except Exception as e:
            logger.error(f"Error building user profile: {e}")
            return {}

    def _analyze_preferences(
        self, preferences: UserPreference | None
    ) -> dict[str, Any]:
        """사용자 선호도 분석"""
        if not preferences:
            return {}

        return {
            "preferred_regions": preferences.preferred_regions or [],
            "preferred_themes": preferences.preferred_themes or [],
            "preferred_activities": preferences.preferred_activities or [],
            "weather_preferences": preferences.weather_preferences or {},
            "accessibility_needs": preferences.accessibility_needs or {},
            "budget_range": preferences.budget_range,
            "travel_style": preferences.travel_style,
        }

    def _analyze_travel_history(self, travel_plans: list[TravelPlan]) -> dict[str, Any]:
        """여행 이력 분석"""
        if not travel_plans:
            return {}

        # 계절별 여행 패턴
        seasonal_patterns = {}
        destination_frequency = {}

        for plan in travel_plans:
            if plan.start_date:
                season = self._get_season(plan.start_date)
                seasonal_patterns[season] = seasonal_patterns.get(season, 0) + 1

            # 목적지 빈도 (실제 구현에서는 travel_days와 연결)
            # destination_frequency 계산 로직 추가 필요

        return {
            "total_trips": len(travel_plans),
            "seasonal_patterns": seasonal_patterns,
            "destination_frequency": destination_frequency,
            "avg_trip_duration": self._calculate_avg_duration(travel_plans),
            "planning_lead_time": self._calculate_planning_lead_time(travel_plans),
        }

    def _analyze_review_patterns(self, reviews: list[Review]) -> dict[str, Any]:
        """리뷰 패턴 분석"""
        if not reviews:
            return {}

        ratings = [review.rating for review in reviews if review.rating]

        return {
            "total_reviews": len(reviews),
            "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
            "rating_distribution": self._calculate_rating_distribution(ratings),
            "review_sentiment": self._analyze_review_sentiment(reviews),
            "favorite_categories": self._extract_favorite_categories(reviews),
        }

    def _calculate_behavioral_score(
        self, travel_plans: list[TravelPlan], reviews: list[Review]
    ) -> dict[str, float]:
        """행동 점수 계산"""
        return {
            "activity_level": len(travel_plans) * 0.3 + len(reviews) * 0.2,
            "engagement_score": len(reviews) / max(len(travel_plans), 1),
            "satisfaction_score": self._calculate_satisfaction_score(reviews),
            "loyalty_score": self._calculate_loyalty_score(travel_plans),
        }

    def _get_season(self, date: datetime) -> str:
        """계절 계산"""
        month = date.month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"

    def _calculate_avg_duration(self, travel_plans: list[TravelPlan]) -> float:
        """평균 여행 기간 계산"""
        durations = []
        for plan in travel_plans:
            if plan.start_date and plan.end_date:
                duration = (plan.end_date - plan.start_date).days
                durations.append(duration)

        return sum(durations) / len(durations) if durations else 0

    def _calculate_planning_lead_time(self, travel_plans: list[TravelPlan]) -> float:
        """평균 계획 선행 시간 계산"""
        lead_times = []
        for plan in travel_plans:
            if plan.start_date and plan.created_at:
                lead_time = (plan.start_date - plan.created_at).days
                lead_times.append(lead_time)

        return sum(lead_times) / len(lead_times) if lead_times else 0

    def _calculate_rating_distribution(self, ratings: list[float]) -> dict[str, int]:
        """평점 분포 계산"""
        distribution = {}
        for rating in ratings:
            key = f"{int(rating)}.0"
            distribution[key] = distribution.get(key, 0) + 1

        return distribution

    def _analyze_review_sentiment(self, reviews: list[Review]) -> dict[str, Any]:
        """리뷰 감정 분석 (간단한 키워드 기반)"""
        positive_keywords = ["좋", "훌륭", "최고", "추천", "만족", "감동"]
        negative_keywords = ["나쁘", "최악", "실망", "별로", "불만"]

        positive_count = 0
        negative_count = 0

        for review in reviews:
            if review.content:
                content = review.content.lower()
                for keyword in positive_keywords:
                    if keyword in content:
                        positive_count += 1
                        break
                for keyword in negative_keywords:
                    if keyword in content:
                        negative_count += 1
                        break

        total = positive_count + negative_count
        return {
            "positive_ratio": positive_count / total if total > 0 else 0,
            "negative_ratio": negative_count / total if total > 0 else 0,
            "sentiment_score": (
                (positive_count - negative_count) / total if total > 0 else 0
            ),
        }

    def _extract_favorite_categories(self, reviews: list[Review]) -> dict[str, int]:
        """선호 카테고리 추출"""
        # 실제 구현에서는 destination과 조인하여 카테고리 정보 추출
        return {}

    def _calculate_satisfaction_score(self, reviews: list[Review]) -> float:
        """만족도 점수 계산"""
        ratings = [review.rating for review in reviews if review.rating]
        return sum(ratings) / len(ratings) / 5.0 if ratings else 0

    def _calculate_loyalty_score(self, travel_plans: list[TravelPlan]) -> float:
        """충성도 점수 계산"""
        if not travel_plans:
            return 0

        # 최근 활동 가중치
        recent_plans = [
            p
            for p in travel_plans
            if p.created_at and (datetime.now() - p.created_at).days <= 365
        ]

        return len(recent_plans) / len(travel_plans)


class RecommendationEngine:
    """추천 엔진 메인 클래스"""

    def __init__(self, db: Session):
        self.db = db
        self.tfidf_vectorizer = TfidfVectorizer(max_features=1000, stop_words="english")
        self.scaler = StandardScaler()
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self._load_models()

    def _load_models(self):
        """저장된 모델 로드"""
        try:
            # 실제 구현에서는 파일에서 모델 로드
            pass
        except Exception as e:
            logger.warning(f"Could not load saved models: {e}")

    def get_content_based_recommendations(
        self, user_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """콘텐츠 기반 추천"""
        try:
            user_profile = UserProfile(user_id, self.db)

            # 사용자 선호도 기반 필터링
            preferences = user_profile.profile_data.get("preferences", {})

            # 기본 쿼리
            query = self.db.query(Destination)

            # 선호 지역 필터
            preferred_regions = preferences.get("preferred_regions", [])
            if preferred_regions:
                query = query.filter(Destination.region.in_(preferred_regions))

            # 선호 테마 필터
            preferred_themes = preferences.get("preferred_themes", [])
            if preferred_themes:
                query = query.filter(Destination.category.in_(preferred_themes))

            destinations = query.limit(
                limit * 2
            ).all()  # 여유있게 가져와서 점수 계산 후 필터

            # 콘텐츠 유사도 계산
            scored_destinations = []
            for destination in destinations:
                score = self._calculate_content_similarity_score(
                    destination, user_profile
                )
                scored_destinations.append(
                    {
                        "destination": destination,
                        "score": score,
                        "recommendation_type": "content_based",
                    }
                )

            # 점수순 정렬
            scored_destinations.sort(key=lambda x: x["score"], reverse=True)

            return scored_destinations[:limit]

        except Exception as e:
            logger.error(f"Error in content-based recommendations: {e}")
            return []

    def get_collaborative_recommendations(
        self, user_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """협업 필터링 추천"""
        try:
            # 유사한 사용자 찾기
            similar_users = self._find_similar_users(user_id)

            if not similar_users:
                return []

            # 유사 사용자들의 선호 목적지 수집
            recommended_destinations = []

            for similar_user_id, similarity_score in similar_users[:5]:  # 상위 5명
                user_destinations = self._get_user_preferred_destinations(
                    similar_user_id
                )

                for destination in user_destinations:
                    # 이미 방문한 목적지는 제외
                    if not self._has_user_visited(user_id, destination.destination_id):
                        recommended_destinations.append(
                            {
                                "destination": destination,
                                "score": similarity_score,
                                "recommendation_type": "collaborative",
                            }
                        )

            # 중복 제거 및 점수 집계
            destination_scores = {}
            for item in recommended_destinations:
                dest_id = item["destination"].destination_id
                if dest_id not in destination_scores:
                    destination_scores[dest_id] = {
                        "destination": item["destination"],
                        "total_score": 0,
                        "count": 0,
                    }
                destination_scores[dest_id]["total_score"] += item["score"]
                destination_scores[dest_id]["count"] += 1

            # 평균 점수 계산 및 정렬
            final_recommendations = []
            for dest_id, data in destination_scores.items():
                avg_score = data["total_score"] / data["count"]
                final_recommendations.append(
                    {
                        "destination": data["destination"],
                        "score": avg_score,
                        "recommendation_type": "collaborative",
                    }
                )

            final_recommendations.sort(key=lambda x: x["score"], reverse=True)

            return final_recommendations[:limit]

        except Exception as e:
            logger.error(f"Error in collaborative recommendations: {e}")
            return []

    def get_weather_based_recommendations(
        self, user_id: str, travel_date: datetime, limit: int = 10
    ) -> list[dict[str, Any]]:
        """날씨 기반 추천"""
        try:
            user_profile = UserProfile(user_id, self.db)
            weather_preferences = user_profile.profile_data.get("preferences", {}).get(
                "weather_preferences", {}
            )

            # 계절 정보
            season = self._get_season(travel_date)

            # 날씨 적합도가 높은 목적지 조회
            # 실제 구현에서는 weather_suitability 테이블과 조인
            destinations = self.db.query(Destination).limit(limit * 3).all()

            scored_destinations = []
            for destination in destinations:
                weather_score = self._calculate_weather_score(
                    destination, season, weather_preferences
                )
                scored_destinations.append(
                    {
                        "destination": destination,
                        "score": weather_score,
                        "recommendation_type": "weather_based",
                        "weather_info": {
                            "season": season,
                            "suitability": weather_score,
                        },
                    }
                )

            scored_destinations.sort(key=lambda x: x["score"], reverse=True)

            return scored_destinations[:limit]

        except Exception as e:
            logger.error(f"Error in weather-based recommendations: {e}")
            return []

    def get_hybrid_recommendations(
        self, user_id: str, limit: int = 10, travel_date: datetime | None = None
    ) -> list[dict[str, Any]]:
        """하이브리드 추천 (여러 방법 조합)"""
        try:
            # 각 추천 방법별로 결과 수집
            content_recs = self.get_content_based_recommendations(user_id, limit // 2)
            collaborative_recs = self.get_collaborative_recommendations(
                user_id, limit // 2
            )

            if travel_date:
                weather_recs = self.get_weather_based_recommendations(
                    user_id, travel_date, limit // 3
                )
            else:
                weather_recs = []

            # 점수 가중치 적용
            weights = {"content_based": 0.4, "collaborative": 0.4, "weather_based": 0.2}

            # 모든 추천 결과 통합
            all_recommendations = content_recs + collaborative_recs + weather_recs

            # 목적지별 점수 집계
            destination_scores = {}
            for rec in all_recommendations:
                dest_id = rec["destination"].destination_id
                rec_type = rec["recommendation_type"]

                if dest_id not in destination_scores:
                    destination_scores[dest_id] = {
                        "destination": rec["destination"],
                        "total_score": 0,
                        "recommendation_types": [],
                        "type_scores": {},
                    }

                weighted_score = rec["score"] * weights.get(rec_type, 0.3)
                destination_scores[dest_id]["total_score"] += weighted_score
                destination_scores[dest_id]["recommendation_types"].append(rec_type)
                destination_scores[dest_id]["type_scores"][rec_type] = rec["score"]

            # 최종 추천 결과 생성
            final_recommendations = []
            for dest_id, data in destination_scores.items():
                final_recommendations.append(
                    {
                        "destination": data["destination"],
                        "score": data["total_score"],
                        "recommendation_type": "hybrid",
                        "contributing_types": list(set(data["recommendation_types"])),
                        "type_scores": data["type_scores"],
                    }
                )

            # 점수순 정렬
            final_recommendations.sort(key=lambda x: x["score"], reverse=True)

            return final_recommendations[:limit]

        except Exception as e:
            logger.error(f"Error in hybrid recommendations: {e}")
            return []

    def _calculate_content_similarity_score(
        self, destination: Destination, user_profile: UserProfile
    ) -> float:
        """콘텐츠 유사도 점수 계산"""
        score = 0.0

        preferences = user_profile.profile_data.get("preferences", {})

        # 지역 선호도 점수
        preferred_regions = preferences.get("preferred_regions", [])
        if destination.region in preferred_regions:
            score += 0.3

        # 카테고리 선호도 점수
        preferred_themes = preferences.get("preferred_themes", [])
        if destination.category in preferred_themes:
            score += 0.4

        # 과거 여행 패턴 점수
        travel_history = user_profile.profile_data.get("travel_history", {})
        seasonal_patterns = travel_history.get("seasonal_patterns", {})

        # 현재 계절 가중치
        current_season = self._get_season(datetime.now())
        if seasonal_patterns.get(current_season, 0) > 0:
            score += 0.2

        # 리뷰 패턴 점수
        review_patterns = user_profile.profile_data.get("review_patterns", {})
        if review_patterns.get("avg_rating", 0) > 4.0:
            score += 0.1

        return min(score, 1.0)

    def _find_similar_users(self, user_id: str) -> list[tuple[str, float]]:
        """유사한 사용자 찾기"""
        try:
            # 간단한 유사도 계산 (실제로는 더 복잡한 알고리즘 사용)
            current_user_profile = UserProfile(user_id, self.db)

            # 다른 사용자들의 프로필 수집
            other_users = (
                self.db.query(User).filter(User.user_id != user_id).limit(100).all()
            )

            similar_users = []
            for user in other_users:
                other_profile = UserProfile(user.user_id, self.db)
                similarity = self._calculate_user_similarity(
                    current_user_profile, other_profile
                )

                if similarity > 0.3:  # 임계값
                    similar_users.append((user.user_id, similarity))

            similar_users.sort(key=lambda x: x[1], reverse=True)
            return similar_users

        except Exception as e:
            logger.error(f"Error finding similar users: {e}")
            return []

    def _calculate_user_similarity(
        self, profile1: UserProfile, profile2: UserProfile
    ) -> float:
        """사용자 간 유사도 계산"""
        similarity = 0.0

        # 선호 지역 유사도
        regions1 = set(
            profile1.profile_data.get("preferences", {}).get("preferred_regions", [])
        )
        regions2 = set(
            profile2.profile_data.get("preferences", {}).get("preferred_regions", [])
        )

        if regions1 and regions2:
            region_similarity = len(regions1.intersection(regions2)) / len(
                regions1.union(regions2)
            )
            similarity += region_similarity * 0.3

        # 선호 테마 유사도
        themes1 = set(
            profile1.profile_data.get("preferences", {}).get("preferred_themes", [])
        )
        themes2 = set(
            profile2.profile_data.get("preferences", {}).get("preferred_themes", [])
        )

        if themes1 and themes2:
            theme_similarity = len(themes1.intersection(themes2)) / len(
                themes1.union(themes2)
            )
            similarity += theme_similarity * 0.4

        # 행동 점수 유사도
        behavior1 = profile1.profile_data.get("behavioral_score", {})
        behavior2 = profile2.profile_data.get("behavioral_score", {})

        if behavior1 and behavior2:
            behavior_similarity = (
                1
                - abs(
                    behavior1.get("activity_level", 0)
                    - behavior2.get("activity_level", 0)
                )
                / 10
            )
            similarity += behavior_similarity * 0.3

        return min(similarity, 1.0)

    def _get_user_preferred_destinations(self, user_id: str) -> list[Destination]:
        """사용자가 선호하는 목적지 조회"""
        # 높은 평점을 준 목적지들
        high_rated_destinations = (
            self.db.query(Destination)
            .join(Review)
            .filter(and_(Review.user_id == user_id, Review.rating >= 4.0))
            .all()
        )

        return high_rated_destinations

    def _has_user_visited(self, user_id: str, destination_id: str) -> bool:
        """사용자가 해당 목적지를 방문했는지 확인"""
        # 실제 구현에서는 travel_day_destinations 테이블 확인
        visited = (
            self.db.query(Review)
            .filter(
                and_(Review.user_id == user_id, Review.destination_id == destination_id)
            )
            .first()
        )

        return visited is not None

    def _calculate_weather_score(
        self, destination: Destination, season: str, weather_preferences: dict[str, Any]
    ) -> float:
        """날씨 점수 계산"""
        # 실제 구현에서는 weather_suitability 테이블과 연동
        base_score = 0.5

        # 계절별 기본 점수
        season_scores = {"spring": 0.8, "summer": 0.6, "fall": 0.7, "winter": 0.4}

        return base_score + season_scores.get(season, 0.5) * 0.5

    def _get_season(self, date: datetime) -> str:
        """계절 계산"""
        month = date.month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"

    def train_model(self):
        """추천 모델 학습"""
        try:
            # 학습 데이터 수집
            training_data = self._collect_training_data()

            if not training_data:
                logger.warning("No training data available")
                return

            # 특성 추출
            features, labels = self._extract_features(training_data)

            # 모델 학습
            self.model.fit(features, labels)

            # 모델 저장
            self._save_model()

            logger.info("Recommendation model trained successfully")

        except Exception as e:
            logger.error(f"Error training recommendation model: {e}")

    def _collect_training_data(self) -> list[dict[str, Any]]:
        """학습 데이터 수집"""
        # 실제 구현에서는 사용자 행동 데이터 수집
        return []

    def _extract_features(
        self, training_data: list[dict[str, Any]]
    ) -> tuple[np.ndarray, np.ndarray]:
        """특성 추출"""
        # 실제 구현에서는 사용자 특성과 목적지 특성을 벡터로 변환
        features = np.array([[1, 2, 3]])  # 예시
        labels = np.array([1])  # 예시

        return features, labels

    def _save_model(self):
        """모델 저장"""
        try:
            # 실제 구현에서는 joblib 또는 pickle로 모델 저장
            pass
        except Exception as e:
            logger.error(f"Error saving model: {e}")


# 추천 엔진 싱글톤
recommendation_engine = None


def get_recommendation_engine(db=None):
    """추천 엔진 인스턴스 반환"""
    global recommendation_engine
    if recommendation_engine is None:
        if db is None:
            from app.database import get_db

            db = next(get_db())
        recommendation_engine = RecommendationEngine(db)
    return recommendation_engine


logger.info("AI recommendation engine initialized")
