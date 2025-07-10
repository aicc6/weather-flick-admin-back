"""
사용자 행동 분석 및 개인화 엔진
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Review, TravelPlan, UserPreference

logger = get_logger("behavior_analysis")


class UserBehaviorAnalyzer:
    """사용자 행동 분석기"""

    def __init__(self, db: Session):
        self.db = db

    def analyze_user_behavior(self, user_id: str) -> dict[str, Any]:
        """사용자 행동 종합 분석"""
        try:
            analysis = {
                "user_id": user_id,
                "travel_patterns": self._analyze_travel_patterns(user_id),
                "preference_evolution": self._analyze_preference_evolution(user_id),
                "engagement_metrics": self._analyze_engagement_metrics(user_id),
                "seasonal_behavior": self._analyze_seasonal_behavior(user_id),
                "decision_making_patterns": self._analyze_decision_patterns(user_id),
                "social_influence": self._analyze_social_influence(user_id),
                "budget_patterns": self._analyze_budget_patterns(user_id),
                "activity_timeline": self._analyze_activity_timeline(user_id),
                "prediction_scores": self._calculate_prediction_scores(user_id),
                "analysis_timestamp": datetime.now().isoformat(),
            }

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing user behavior: {e}")
            return {}

    def _analyze_travel_patterns(self, user_id: str) -> dict[str, Any]:
        """여행 패턴 분석"""
        try:
            travel_plans = (
                self.db.query(TravelPlan).filter(TravelPlan.user_id == user_id).all()
            )

            if not travel_plans:
                return {}

            # 여행 빈도 분석
            travel_frequency = self._calculate_travel_frequency(travel_plans)

            # 여행 기간 분석
            duration_patterns = self._analyze_duration_patterns(travel_plans)

            # 목적지 선호도 분석
            destination_preferences = self._analyze_destination_preferences(user_id)

            # 계획 수립 패턴
            planning_patterns = self._analyze_planning_patterns(travel_plans)

            return {
                "travel_frequency": travel_frequency,
                "duration_patterns": duration_patterns,
                "destination_preferences": destination_preferences,
                "planning_patterns": planning_patterns,
                "total_trips": len(travel_plans),
            }

        except Exception as e:
            logger.error(f"Error analyzing travel patterns: {e}")
            return {}

    def _analyze_preference_evolution(self, user_id: str) -> dict[str, Any]:
        """선호도 변화 분석"""
        try:
            # 시간대별 리뷰 분석
            reviews = (
                self.db.query(Review)
                .filter(Review.user_id == user_id)
                .order_by(Review.created_at)
                .all()
            )

            if not reviews:
                return {}

            # 6개월 단위로 선호도 변화 추적
            time_windows = self._create_time_windows(reviews)
            preference_evolution = []

            for window in time_windows:
                window_reviews = [
                    r
                    for r in reviews
                    if window["start"] <= r.created_at <= window["end"]
                ]
                if window_reviews:
                    preferences = self._extract_preferences_from_reviews(window_reviews)
                    preference_evolution.append(
                        {
                            "period": window["label"],
                            "preferences": preferences,
                            "review_count": len(window_reviews),
                        }
                    )

            # 선호도 변화 트렌드 계산
            trends = self._calculate_preference_trends(preference_evolution)

            return {
                "evolution_timeline": preference_evolution,
                "trends": trends,
                "stability_score": self._calculate_preference_stability(
                    preference_evolution
                ),
            }

        except Exception as e:
            logger.error(f"Error analyzing preference evolution: {e}")
            return {}

    def _analyze_engagement_metrics(self, user_id: str) -> dict[str, Any]:
        """참여도 지표 분석"""
        try:
            # 활동 데이터 수집
            travel_plans = (
                self.db.query(TravelPlan).filter(TravelPlan.user_id == user_id).all()
            )
            reviews = self.db.query(Review).filter(Review.user_id == user_id).all()

            # 참여도 계산
            engagement_score = self._calculate_engagement_score(travel_plans, reviews)

            # 활동 패턴
            activity_patterns = self._analyze_activity_patterns(user_id)

            # 콘텐츠 상호작용
            content_interaction = self._analyze_content_interaction(user_id)

            return {
                "engagement_score": engagement_score,
                "activity_patterns": activity_patterns,
                "content_interaction": content_interaction,
                "loyalty_indicators": self._calculate_loyalty_indicators(
                    travel_plans, reviews
                ),
            }

        except Exception as e:
            logger.error(f"Error analyzing engagement metrics: {e}")
            return {}

    def _analyze_seasonal_behavior(self, user_id: str) -> dict[str, Any]:
        """계절별 행동 분석"""
        try:
            travel_plans = (
                self.db.query(TravelPlan).filter(TravelPlan.user_id == user_id).all()
            )

            seasonal_data = defaultdict(list)

            for plan in travel_plans:
                if plan.start_date:
                    season = self._get_season(plan.start_date)
                    seasonal_data[season].append(plan)

            seasonal_analysis = {}
            for season, plans in seasonal_data.items():
                seasonal_analysis[season] = {
                    "trip_count": len(plans),
                    "avg_duration": self._calculate_avg_duration(plans),
                    "preferred_destinations": self._get_seasonal_destinations(plans),
                    "budget_range": self._get_seasonal_budget_range(plans),
                }

            # 계절 선호도 점수
            seasonal_preferences = self._calculate_seasonal_preferences(
                seasonal_analysis
            )

            return {
                "seasonal_breakdown": seasonal_analysis,
                "seasonal_preferences": seasonal_preferences,
                "peak_travel_season": (
                    max(
                        seasonal_analysis.keys(),
                        key=lambda x: seasonal_analysis[x]["trip_count"],
                    )
                    if seasonal_analysis
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Error analyzing seasonal behavior: {e}")
            return {}

    def _analyze_decision_patterns(self, user_id: str) -> dict[str, Any]:
        """의사결정 패턴 분석"""
        try:
            travel_plans = (
                self.db.query(TravelPlan).filter(TravelPlan.user_id == user_id).all()
            )

            # 계획 수립 리드타임 분석
            lead_times = []
            for plan in travel_plans:
                if plan.start_date and plan.created_at:
                    lead_time = (plan.start_date - plan.created_at).days
                    lead_times.append(lead_time)

            # 의사결정 스타일 분류
            decision_style = self._classify_decision_style(lead_times)

            # 선택 패턴 분석
            choice_patterns = self._analyze_choice_patterns(user_id)

            # 변경 패턴 분석
            modification_patterns = self._analyze_modification_patterns(travel_plans)

            return {
                "decision_style": decision_style,
                "avg_lead_time": np.mean(lead_times) if lead_times else 0,
                "lead_time_std": np.std(lead_times) if lead_times else 0,
                "choice_patterns": choice_patterns,
                "modification_patterns": modification_patterns,
            }

        except Exception as e:
            logger.error(f"Error analyzing decision patterns: {e}")
            return {}

    def _analyze_social_influence(self, user_id: str) -> dict[str, Any]:
        """소셜 영향도 분석"""
        try:
            # 리뷰 영향력 분석
            reviews = self.db.query(Review).filter(Review.user_id == user_id).all()

            # 평점 분포
            rating_distribution = Counter([r.rating for r in reviews if r.rating])

            # 리뷰 품질 점수
            review_quality = self._calculate_review_quality(reviews)

            # 트렌드 팔로우 경향
            trend_following = self._analyze_trend_following(user_id)

            return {
                "review_influence": {
                    "total_reviews": len(reviews),
                    "avg_rating": (
                        np.mean([r.rating for r in reviews if r.rating])
                        if reviews
                        else 0
                    ),
                    "rating_distribution": dict(rating_distribution),
                    "quality_score": review_quality,
                },
                "trend_following": trend_following,
                "social_engagement_score": self._calculate_social_engagement_score(
                    reviews
                ),
            }

        except Exception as e:
            logger.error(f"Error analyzing social influence: {e}")
            return {}

    def _analyze_budget_patterns(self, user_id: str) -> dict[str, Any]:
        """예산 패턴 분석"""
        try:
            # 사용자 선호도에서 예산 정보 조회
            preferences = (
                self.db.query(UserPreference)
                .filter(UserPreference.user_id == user_id)
                .first()
            )

            budget_analysis = {}

            if preferences and preferences.budget_range:
                budget_analysis["declared_budget"] = preferences.budget_range

            # 여행 계획 기반 예산 추정
            travel_plans = (
                self.db.query(TravelPlan).filter(TravelPlan.user_id == user_id).all()
            )

            estimated_budgets = self._estimate_trip_budgets(travel_plans)

            if estimated_budgets:
                budget_analysis.update(
                    {
                        "estimated_avg_budget": np.mean(estimated_budgets),
                        "budget_variance": np.var(estimated_budgets),
                        "budget_trend": self._calculate_budget_trend(estimated_budgets),
                    }
                )

            return budget_analysis

        except Exception as e:
            logger.error(f"Error analyzing budget patterns: {e}")
            return {}

    def _analyze_activity_timeline(self, user_id: str) -> dict[str, Any]:
        """활동 타임라인 분석"""
        try:
            # 모든 활동 수집
            activities = []

            # 여행 계획 활동
            travel_plans = (
                self.db.query(TravelPlan).filter(TravelPlan.user_id == user_id).all()
            )
            for plan in travel_plans:
                activities.append(
                    {
                        "type": "travel_plan",
                        "timestamp": plan.created_at,
                        "data": {"title": plan.title},
                    }
                )

            # 리뷰 활동
            reviews = self.db.query(Review).filter(Review.user_id == user_id).all()
            for review in reviews:
                activities.append(
                    {
                        "type": "review",
                        "timestamp": review.created_at,
                        "data": {"rating": review.rating},
                    }
                )

            # 시간순 정렬
            activities.sort(
                key=lambda x: x["timestamp"] if x["timestamp"] else datetime.min
            )

            # 활동 패턴 분석
            activity_patterns = self._analyze_timeline_patterns(activities)

            return {
                "total_activities": len(activities),
                "activity_timeline": activities[-50:],  # 최근 50개 활동
                "patterns": activity_patterns,
                "activity_distribution": self._calculate_activity_distribution(
                    activities
                ),
            }

        except Exception as e:
            logger.error(f"Error analyzing activity timeline: {e}")
            return {}

    def _calculate_prediction_scores(self, user_id: str) -> dict[str, float]:
        """예측 점수 계산"""
        try:
            # 행동 데이터 기반 예측 점수
            travel_plans = (
                self.db.query(TravelPlan).filter(TravelPlan.user_id == user_id).all()
            )
            reviews = self.db.query(Review).filter(Review.user_id == user_id).all()

            scores = {
                "travel_likelihood": self._predict_travel_likelihood(travel_plans),
                "satisfaction_prediction": self._predict_satisfaction(reviews),
                "churn_risk": self._calculate_churn_risk(user_id),
                "upsell_potential": self._calculate_upsell_potential(user_id),
                "recommendation_receptiveness": self._calculate_recommendation_receptiveness(
                    user_id
                ),
            }

            return scores

        except Exception as e:
            logger.error(f"Error calculating prediction scores: {e}")
            return {}

    # Helper methods
    def _calculate_travel_frequency(self, travel_plans: list) -> dict[str, Any]:
        """여행 빈도 계산"""
        if not travel_plans:
            return {}

        # 월별 여행 횟수
        monthly_counts = defaultdict(int)
        for plan in travel_plans:
            if plan.created_at:
                month_key = plan.created_at.strftime("%Y-%m")
                monthly_counts[month_key] += 1

        # 평균 월간 여행 횟수
        avg_monthly = np.mean(list(monthly_counts.values())) if monthly_counts else 0

        return {
            "avg_monthly_trips": avg_monthly,
            "total_months_active": len(monthly_counts),
            "peak_month_trips": max(monthly_counts.values()) if monthly_counts else 0,
        }

    def _analyze_duration_patterns(self, travel_plans: list) -> dict[str, Any]:
        """여행 기간 패턴 분석"""
        durations = []
        for plan in travel_plans:
            if plan.start_date and plan.end_date:
                duration = (plan.end_date - plan.start_date).days
                if duration > 0:
                    durations.append(duration)

        if not durations:
            return {}

        return {
            "avg_duration": np.mean(durations),
            "median_duration": np.median(durations),
            "std_duration": np.std(durations),
            "preferred_duration_range": self._get_preferred_duration_range(durations),
        }

    def _analyze_destination_preferences(self, user_id: str) -> dict[str, Any]:
        """목적지 선호도 분석"""
        # 여행 계획과 리뷰를 통한 목적지 선호도 분석
        # 실제 구현에서는 travel_day_destinations 테이블과 조인
        return {"preferred_regions": [], "preferred_categories": [], "repeat_visits": 0}

    def _get_season(self, date: datetime) -> str:
        """계절 판별"""
        month = date.month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"

    def _classify_decision_style(self, lead_times: list[int]) -> str:
        """의사결정 스타일 분류"""
        if not lead_times:
            return "unknown"

        avg_lead_time = np.mean(lead_times)

        if avg_lead_time < 7:
            return "spontaneous"
        elif avg_lead_time < 30:
            return "moderate_planner"
        elif avg_lead_time < 90:
            return "advance_planner"
        else:
            return "long_term_planner"

    def _predict_travel_likelihood(self, travel_plans: list) -> float:
        """여행 가능성 예측"""
        if not travel_plans:
            return 0.0

        # 최근 활동 기반 예측
        recent_plans = [
            p
            for p in travel_plans
            if p.created_at and (datetime.now() - p.created_at).days <= 90
        ]

        base_score = min(len(recent_plans) * 0.2, 1.0)

        # 패턴 기반 조정
        if len(travel_plans) > 5:
            base_score *= 1.2

        return min(base_score, 1.0)

    def _calculate_churn_risk(self, user_id: str) -> float:
        """이탈 위험도 계산"""
        # 최근 활동 기반 이탈 위험도
        recent_activity = (
            self.db.query(TravelPlan)
            .filter(
                and_(
                    TravelPlan.user_id == user_id,
                    TravelPlan.created_at >= datetime.now() - timedelta(days=180),
                )
            )
            .count()
        )

        if recent_activity == 0:
            return 0.8
        elif recent_activity < 2:
            return 0.4
        else:
            return 0.1

    # 추가 helper 메서드들은 실제 구현에서 필요에 따라 작성
    def _analyze_planning_patterns(self, travel_plans: list) -> dict[str, Any]:
        return {}

    def _create_time_windows(self, reviews: list) -> list[dict]:
        return []

    def _extract_preferences_from_reviews(self, reviews: list) -> dict:
        return {}

    def _calculate_preference_trends(self, evolution: list) -> dict:
        return {}

    def _calculate_preference_stability(self, evolution: list) -> float:
        return 0.0

    def _calculate_engagement_score(self, travel_plans: list, reviews: list) -> float:
        return 0.0

    def _analyze_activity_patterns(self, user_id: str) -> dict:
        return {}

    def _analyze_content_interaction(self, user_id: str) -> dict:
        return {}

    def _calculate_loyalty_indicators(self, travel_plans: list, reviews: list) -> dict:
        return {}

    def _calculate_avg_duration(self, plans: list) -> float:
        return 0.0

    def _get_seasonal_destinations(self, plans: list) -> list:
        return []

    def _get_seasonal_budget_range(self, plans: list) -> dict:
        return {}

    def _calculate_seasonal_preferences(self, seasonal_analysis: dict) -> dict:
        return {}

    def _analyze_choice_patterns(self, user_id: str) -> dict:
        return {}

    def _analyze_modification_patterns(self, travel_plans: list) -> dict:
        return {}

    def _calculate_review_quality(self, reviews: list) -> float:
        return 0.0

    def _analyze_trend_following(self, user_id: str) -> dict:
        return {}

    def _calculate_social_engagement_score(self, reviews: list) -> float:
        return 0.0

    def _estimate_trip_budgets(self, travel_plans: list) -> list[float]:
        return []

    def _calculate_budget_trend(self, budgets: list[float]) -> str:
        return "stable"

    def _analyze_timeline_patterns(self, activities: list) -> dict:
        return {}

    def _calculate_activity_distribution(self, activities: list) -> dict:
        return {}

    def _predict_satisfaction(self, reviews: list) -> float:
        return 0.0

    def _calculate_upsell_potential(self, user_id: str) -> float:
        return 0.0

    def _calculate_recommendation_receptiveness(self, user_id: str) -> float:
        return 0.0

    def _get_preferred_duration_range(self, durations: list[int]) -> str:
        return "unknown"


class PersonalizationEngine:
    """개인화 엔진"""

    def __init__(self, db: Session):
        self.db = db
        self.behavior_analyzer = UserBehaviorAnalyzer(db)

    def generate_personalized_recommendations(self, user_id: str) -> dict[str, Any]:
        """개인화된 추천 생성"""
        try:
            # 사용자 행동 분석
            behavior_analysis = self.behavior_analyzer.analyze_user_behavior(user_id)

            # 개인화 전략 결정
            personalization_strategy = self._determine_personalization_strategy(
                behavior_analysis
            )

            # 맞춤형 콘텐츠 생성
            personalized_content = self._generate_personalized_content(
                user_id, personalization_strategy
            )

            return {
                "user_id": user_id,
                "personalization_strategy": personalization_strategy,
                "personalized_content": personalized_content,
                "behavior_insights": behavior_analysis,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating personalized recommendations: {e}")
            return {}

    def _determine_personalization_strategy(
        self, behavior_analysis: dict[str, Any]
    ) -> dict[str, str]:
        """개인화 전략 결정"""
        strategy = {
            "primary_approach": "balanced",
            "content_focus": "general",
            "recommendation_style": "moderate",
            "communication_tone": "friendly",
        }

        # 행동 분석 기반 전략 조정
        if (
            behavior_analysis.get("decision_patterns", {}).get("decision_style")
            == "spontaneous"
        ):
            strategy["recommendation_style"] = "immediate"
            strategy["content_focus"] = "trending"

        return strategy

    def _generate_personalized_content(
        self, user_id: str, strategy: dict[str, str]
    ) -> dict[str, Any]:
        """개인화된 콘텐츠 생성"""
        return {
            "recommendations": [],
            "personalized_messages": [],
            "targeted_offers": [],
            "content_suggestions": [],
        }


# 전역 인스턴스
def get_behavior_analyzer(db: Session = None):
    """행동 분석기 인스턴스 반환"""
    if db is None:
        from app.database import get_db

        db = next(get_db())
    return UserBehaviorAnalyzer(db)


def get_personalization_engine(db: Session) -> PersonalizationEngine:
    """개인화 엔진 인스턴스 반환"""
    return PersonalizationEngine(db)


logger.info("User behavior analysis and personalization engine initialized")
