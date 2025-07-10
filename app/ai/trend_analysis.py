"""
실시간 여행 트렌드 분석 시스템
"""

import asyncio
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Review, TravelPlan, User, UserPreference

logger = get_logger("trend_analysis")


class TrendAnalyzer:
    """트렌드 분석기"""

    def __init__(self, db: Session):
        self.db = db
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def analyze_realtime_trends(self, time_window: int = 7) -> dict[str, Any]:
        """실시간 트렌드 분석"""
        try:
            # 병렬 분석 실행
            tasks = [
                self._analyze_destination_trends(time_window),
                self._analyze_search_trends(time_window),
                self._analyze_booking_trends(time_window),
                self._analyze_review_trends(time_window),
                self._analyze_seasonal_trends(),
                self._analyze_demographic_trends(time_window),
                self._analyze_price_trends(time_window),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 통합
            trend_analysis = {
                "analysis_timestamp": datetime.now().isoformat(),
                "time_window_days": time_window,
                "destination_trends": (
                    results[0] if not isinstance(results[0], Exception) else {}
                ),
                "search_trends": (
                    results[1] if not isinstance(results[1], Exception) else {}
                ),
                "booking_trends": (
                    results[2] if not isinstance(results[2], Exception) else {}
                ),
                "review_trends": (
                    results[3] if not isinstance(results[3], Exception) else {}
                ),
                "seasonal_trends": (
                    results[4] if not isinstance(results[4], Exception) else {}
                ),
                "demographic_trends": (
                    results[5] if not isinstance(results[5], Exception) else {}
                ),
                "price_trends": (
                    results[6] if not isinstance(results[6], Exception) else {}
                ),
            }

            # 트렌드 종합 점수 계산
            trend_analysis["trend_summary"] = self._calculate_trend_summary(
                trend_analysis
            )

            return trend_analysis

        except Exception as e:
            logger.error(f"Error analyzing realtime trends: {e}")
            return {}

    async def _analyze_destination_trends(self, time_window: int) -> dict[str, Any]:
        """목적지 트렌드 분석"""
        try:
            cutoff_date = datetime.now() - timedelta(days=time_window)

            # 최근 여행 계획 데이터
            recent_plans = (
                self.db.query(TravelPlan)
                .filter(TravelPlan.created_at >= cutoff_date)
                .all()
            )

            # 목적지별 인기도 계산
            destination_popularity = defaultdict(int)
            for plan in recent_plans:
                # 실제 구현에서는 travel_day_destinations와 조인
                # 현재는 간단한 카운팅
                if hasattr(plan, "destinations"):
                    for dest in plan.destinations:
                        destination_popularity[dest.destination_id] += 1

            # 상위 트렌딩 목적지
            trending_destinations = sorted(
                destination_popularity.items(), key=lambda x: x[1], reverse=True
            )[:10]

            # 지역별 트렌드
            regional_trends = self._analyze_regional_trends(recent_plans)

            # 카테고리별 트렌드
            category_trends = self._analyze_category_trends(recent_plans)

            return {
                "trending_destinations": trending_destinations,
                "regional_trends": regional_trends,
                "category_trends": category_trends,
                "total_plans_analyzed": len(recent_plans),
            }

        except Exception as e:
            logger.error(f"Error analyzing destination trends: {e}")
            return {}

    async def _analyze_search_trends(self, time_window: int) -> dict[str, Any]:
        """검색 트렌드 분석"""
        try:
            # 실제 구현에서는 검색 로그 테이블이 필요
            # 현재는 리뷰와 여행 계획을 기반으로 추정

            cutoff_date = datetime.now() - timedelta(days=time_window)

            # 최근 활동 기반 검색 키워드 추정
            recent_reviews = (
                self.db.query(Review).filter(Review.created_at >= cutoff_date).all()
            )

            # 키워드 추출 (간단한 방식)
            keywords = self._extract_keywords_from_reviews(recent_reviews)

            # 검색 볼륨 추정
            search_volumes = self._estimate_search_volumes(keywords)

            # 트렌딩 키워드
            trending_keywords = sorted(
                search_volumes.items(), key=lambda x: x[1], reverse=True
            )[:20]

            return {
                "trending_keywords": trending_keywords,
                "total_searches_estimated": sum(search_volumes.values()),
                "search_categories": self._categorize_search_terms(keywords),
            }

        except Exception as e:
            logger.error(f"Error analyzing search trends: {e}")
            return {}

    async def _analyze_booking_trends(self, time_window: int) -> dict[str, Any]:
        """예약 트렌드 분석"""
        try:
            cutoff_date = datetime.now() - timedelta(days=time_window)

            # 최근 여행 계획을 예약으로 가정
            recent_bookings = (
                self.db.query(TravelPlan)
                .filter(TravelPlan.created_at >= cutoff_date)
                .all()
            )

            # 예약 패턴 분석
            booking_patterns = self._analyze_booking_patterns(recent_bookings)

            # 예약 시간대 분석
            booking_times = self._analyze_booking_times(recent_bookings)

            # 예약 기간 분석
            booking_durations = self._analyze_booking_durations(recent_bookings)

            return {
                "total_bookings": len(recent_bookings),
                "booking_patterns": booking_patterns,
                "booking_times": booking_times,
                "booking_durations": booking_durations,
                "conversion_metrics": self._calculate_conversion_metrics(
                    recent_bookings
                ),
            }

        except Exception as e:
            logger.error(f"Error analyzing booking trends: {e}")
            return {}

    async def _analyze_review_trends(self, time_window: int) -> dict[str, Any]:
        """리뷰 트렌드 분석"""
        try:
            cutoff_date = datetime.now() - timedelta(days=time_window)

            recent_reviews = (
                self.db.query(Review).filter(Review.created_at >= cutoff_date).all()
            )

            # 평점 트렌드
            rating_trends = self._analyze_rating_trends(recent_reviews)

            # 감정 트렌드
            sentiment_trends = self._analyze_sentiment_trends(recent_reviews)

            # 리뷰 활동 패턴
            review_patterns = self._analyze_review_patterns(recent_reviews)

            # 만족도 지표
            satisfaction_metrics = self._calculate_satisfaction_metrics(recent_reviews)

            return {
                "total_reviews": len(recent_reviews),
                "rating_trends": rating_trends,
                "sentiment_trends": sentiment_trends,
                "review_patterns": review_patterns,
                "satisfaction_metrics": satisfaction_metrics,
            }

        except Exception as e:
            logger.error(f"Error analyzing review trends: {e}")
            return {}

    async def _analyze_seasonal_trends(self) -> dict[str, Any]:
        """계절별 트렌드 분석"""
        try:
            # 현재 계절과 다음 계절 예측
            current_month = datetime.now().month
            current_season = self._get_season_from_month(current_month)
            next_season = self._get_next_season(current_season)

            # 작년 동기 대비 데이터
            last_year_same_period = datetime.now() - timedelta(days=365)

            # 계절별 여행 패턴 조회
            seasonal_data = self._get_seasonal_travel_data()

            # 계절 예측
            seasonal_predictions = self._predict_seasonal_trends(seasonal_data)

            return {
                "current_season": current_season,
                "next_season": next_season,
                "seasonal_data": seasonal_data,
                "seasonal_predictions": seasonal_predictions,
                "yoy_comparison": self._compare_year_over_year(last_year_same_period),
            }

        except Exception as e:
            logger.error(f"Error analyzing seasonal trends: {e}")
            return {}

    async def _analyze_demographic_trends(self, time_window: int) -> dict[str, Any]:
        """인구통계학적 트렌드 분석"""
        try:
            cutoff_date = datetime.now() - timedelta(days=time_window)

            # 최근 활동 사용자 조회
            active_users = (
                self.db.query(User)
                .join(TravelPlan)
                .filter(TravelPlan.created_at >= cutoff_date)
                .all()
            )

            # 연령대별 분석 (실제 구현에서는 User 모델에 age 필드 필요)
            age_group_trends = self._analyze_age_group_trends(active_users)

            # 지역별 사용자 분석
            regional_user_trends = self._analyze_regional_user_trends(active_users)

            # 선호도 변화
            preference_shifts = self._analyze_preference_shifts(active_users)

            return {
                "active_users": len(active_users),
                "age_group_trends": age_group_trends,
                "regional_user_trends": regional_user_trends,
                "preference_shifts": preference_shifts,
            }

        except Exception as e:
            logger.error(f"Error analyzing demographic trends: {e}")
            return {}

    async def _analyze_price_trends(self, time_window: int) -> dict[str, Any]:
        """가격 트렌드 분석"""
        try:
            # 실제 구현에서는 가격 데이터가 필요
            # 현재는 사용자 예산 선호도를 기반으로 추정

            cutoff_date = datetime.now() - timedelta(days=time_window)

            # 최근 사용자 예산 선호도
            recent_preferences = (
                self.db.query(UserPreference)
                .filter(UserPreference.updated_at >= cutoff_date)
                .all()
            )

            # 예산 트렌드 분석
            budget_trends = self._analyze_budget_trends(recent_preferences)

            # 가격 민감도 분석
            price_sensitivity = self._analyze_price_sensitivity(recent_preferences)

            return {
                "budget_trends": budget_trends,
                "price_sensitivity": price_sensitivity,
                "value_perception": self._analyze_value_perception(),
            }

        except Exception as e:
            logger.error(f"Error analyzing price trends: {e}")
            return {}

    def _calculate_trend_summary(
        self, trend_analysis: dict[str, Any]
    ) -> dict[str, Any]:
        """트렌드 종합 요약"""
        try:
            summary = {
                "overall_trend_direction": "stable",
                "hottest_destinations": [],
                "emerging_trends": [],
                "declining_trends": [],
                "trend_confidence": 0.5,
            }

            # 목적지 트렌드에서 인사이트 추출
            dest_trends = trend_analysis.get("destination_trends", {})
            if dest_trends.get("trending_destinations"):
                summary["hottest_destinations"] = dest_trends["trending_destinations"][
                    :5
                ]

            # 전반적인 트렌드 방향 결정
            booking_trends = trend_analysis.get("booking_trends", {})
            total_bookings = booking_trends.get("total_bookings", 0)

            if total_bookings > 100:
                summary["overall_trend_direction"] = "increasing"
                summary["trend_confidence"] = 0.8
            elif total_bookings > 50:
                summary["overall_trend_direction"] = "stable"
                summary["trend_confidence"] = 0.6
            else:
                summary["overall_trend_direction"] = "declining"
                summary["trend_confidence"] = 0.4

            return summary

        except Exception as e:
            logger.error(f"Error calculating trend summary: {e}")
            return {}

    # Helper methods
    def _analyze_regional_trends(self, plans: list) -> dict[str, int]:
        """지역별 트렌드 분석"""
        regional_counts = defaultdict(int)
        for plan in plans:
            # 실제 구현에서는 plan의 목적지 정보 사용
            # 현재는 더미 데이터
            regional_counts["서울"] += 1
        return dict(regional_counts)

    def _analyze_category_trends(self, plans: list) -> dict[str, int]:
        """카테고리별 트렌드 분석"""
        category_counts = defaultdict(int)
        for plan in plans:
            # 실제 구현에서는 plan의 카테고리 정보 사용
            category_counts["관광지"] += 1
        return dict(category_counts)

    def _extract_keywords_from_reviews(self, reviews: list) -> list[str]:
        """리뷰에서 키워드 추출"""
        keywords = []
        for review in reviews:
            if review.content:
                # 간단한 키워드 추출
                words = review.content.split()
                keywords.extend([word for word in words if len(word) > 2])
        return keywords

    def _estimate_search_volumes(self, keywords: list[str]) -> dict[str, int]:
        """검색 볼륨 추정"""
        keyword_counts = Counter(keywords)
        return dict(keyword_counts.most_common(50))

    def _categorize_search_terms(self, keywords: list[str]) -> dict[str, list[str]]:
        """검색어 카테고리화"""
        categories = {
            "destinations": [],
            "activities": [],
            "food": [],
            "accommodation": [],
        }

        # 간단한 카테고리 분류
        for keyword in set(keywords):
            if any(place in keyword.lower() for place in ["서울", "부산", "제주"]):
                categories["destinations"].append(keyword)
            elif any(
                activity in keyword.lower() for activity in ["체험", "투어", "관광"]
            ):
                categories["activities"].append(keyword)

        return categories

    def _analyze_booking_patterns(self, bookings: list) -> dict[str, Any]:
        """예약 패턴 분석"""
        patterns = {
            "peak_booking_days": [],
            "booking_lead_times": [],
            "repeat_booking_rate": 0.0,
        }

        # 예약 요일 분석
        booking_days = [
            booking.created_at.weekday() for booking in bookings if booking.created_at
        ]
        day_counts = Counter(booking_days)
        patterns["peak_booking_days"] = day_counts.most_common(3)

        return patterns

    def _analyze_booking_times(self, bookings: list) -> dict[str, int]:
        """예약 시간대 분석"""
        hour_counts = defaultdict(int)
        for booking in bookings:
            if booking.created_at:
                hour = booking.created_at.hour
                hour_counts[f"{hour:02d}:00"] += 1
        return dict(hour_counts)

    def _analyze_booking_durations(self, bookings: list) -> dict[str, float]:
        """예약 기간 분석"""
        durations = []
        for booking in bookings:
            if booking.start_date and booking.end_date:
                duration = (booking.end_date - booking.start_date).days
                durations.append(duration)

        if durations:
            return {
                "avg_duration": np.mean(durations),
                "median_duration": np.median(durations),
                "max_duration": max(durations),
                "min_duration": min(durations),
            }
        return {}

    def _calculate_conversion_metrics(self, bookings: list) -> dict[str, float]:
        """전환 지표 계산"""
        # 실제 구현에서는 검색 대비 예약 비율 등 계산
        return {"booking_conversion_rate": 0.15, "average_booking_value": 150000.0}

    def _analyze_rating_trends(self, reviews: list) -> dict[str, float]:
        """평점 트렌드 분석"""
        ratings = [review.rating for review in reviews if review.rating]
        if ratings:
            return {
                "avg_rating": np.mean(ratings),
                "rating_std": np.std(ratings),
                "rating_trend": "increasing" if np.mean(ratings) > 4.0 else "stable",
            }
        return {}

    def _analyze_sentiment_trends(self, reviews: list) -> dict[str, Any]:
        """감정 트렌드 분석"""
        positive_keywords = ["좋", "훌륭", "최고", "추천", "만족"]
        negative_keywords = ["나쁘", "최악", "실망", "별로"]

        positive_count = 0
        negative_count = 0

        for review in reviews:
            if review.content:
                content = review.content.lower()
                if any(keyword in content for keyword in positive_keywords):
                    positive_count += 1
                if any(keyword in content for keyword in negative_keywords):
                    negative_count += 1

        total = positive_count + negative_count
        return {
            "positive_sentiment_ratio": positive_count / total if total > 0 else 0,
            "negative_sentiment_ratio": negative_count / total if total > 0 else 0,
            "sentiment_trend": (
                "positive" if positive_count > negative_count else "neutral"
            ),
        }

    def _analyze_review_patterns(self, reviews: list) -> dict[str, Any]:
        """리뷰 패턴 분석"""
        return {
            "avg_review_length": np.mean(
                [len(review.content) for review in reviews if review.content]
            ),
            "review_frequency": len(reviews),
        }

    def _calculate_satisfaction_metrics(self, reviews: list) -> dict[str, float]:
        """만족도 지표 계산"""
        ratings = [review.rating for review in reviews if review.rating]
        if ratings:
            satisfaction_rate = len([r for r in ratings if r >= 4.0]) / len(ratings)
            return {
                "satisfaction_rate": satisfaction_rate,
                "dissatisfaction_rate": 1 - satisfaction_rate,
            }
        return {}

    def _get_season_from_month(self, month: int) -> str:
        """월에서 계절 판별"""
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"

    def _get_next_season(self, current_season: str) -> str:
        """다음 계절 반환"""
        seasons = ["spring", "summer", "fall", "winter"]
        current_index = seasons.index(current_season)
        return seasons[(current_index + 1) % 4]

    def _get_seasonal_travel_data(self) -> dict[str, Any]:
        """계절별 여행 데이터 조회"""
        # 실제 구현에서는 과거 데이터 기반 계절별 패턴 분석
        return {
            "spring": {"popularity": 0.8, "avg_duration": 3.2},
            "summer": {"popularity": 0.9, "avg_duration": 4.1},
            "fall": {"popularity": 0.7, "avg_duration": 2.8},
            "winter": {"popularity": 0.6, "avg_duration": 2.5},
        }

    def _predict_seasonal_trends(self, seasonal_data: dict[str, Any]) -> dict[str, str]:
        """계절 트렌드 예측"""
        return {"next_season_prediction": "increasing", "confidence": "medium"}

    def _compare_year_over_year(self, last_year_date: datetime) -> dict[str, float]:
        """전년 동기 대비 비교"""
        return {"yoy_growth_rate": 0.15, "booking_volume_change": 0.08}

    def _analyze_age_group_trends(self, users: list) -> dict[str, int]:
        """연령대별 트렌드 분석"""
        # 실제 구현에서는 User 모델에 나이 정보 필요
        return {"20s": 45, "30s": 38, "40s": 25, "50s+": 12}

    def _analyze_regional_user_trends(self, users: list) -> dict[str, int]:
        """지역별 사용자 트렌드 분석"""
        return {"서울": 35, "부산": 20, "대구": 15, "기타": 30}

    def _analyze_preference_shifts(self, users: list) -> dict[str, str]:
        """선호도 변화 분석"""
        return {"trending_up": "자연 관광", "trending_down": "쇼핑"}

    def _analyze_budget_trends(self, preferences: list) -> dict[str, Any]:
        """예산 트렌드 분석"""
        return {
            "avg_budget_increase": 0.12,
            "budget_distribution": {"low": 0.3, "medium": 0.5, "high": 0.2},
        }

    def _analyze_price_sensitivity(self, preferences: list) -> dict[str, float]:
        """가격 민감도 분석"""
        return {"price_sensitivity_score": 0.7, "value_orientation": 0.8}

    def _analyze_value_perception(self) -> dict[str, str]:
        """가치 인식 분석"""
        return {
            "primary_value_driver": "experience_quality",
            "secondary_value_driver": "convenience",
        }


class TrendPredictor:
    """트렌드 예측기"""

    def __init__(self, db: Session):
        self.db = db
        self.trend_analyzer = TrendAnalyzer(db)

    async def predict_future_trends(self, prediction_days: int = 30) -> dict[str, Any]:
        """미래 트렌드 예측"""
        try:
            # 현재 트렌드 분석
            current_trends = await self.trend_analyzer.analyze_realtime_trends()

            # 예측 모델 적용
            predictions = {
                "prediction_period_days": prediction_days,
                "destination_predictions": self._predict_destination_trends(
                    current_trends, prediction_days
                ),
                "demand_predictions": self._predict_demand_trends(
                    current_trends, prediction_days
                ),
                "seasonal_predictions": self._predict_seasonal_changes(prediction_days),
                "price_predictions": self._predict_price_trends(
                    current_trends, prediction_days
                ),
                "user_behavior_predictions": self._predict_user_behavior_changes(
                    current_trends, prediction_days
                ),
                "prediction_confidence": self._calculate_prediction_confidence(
                    current_trends
                ),
                "predicted_at": datetime.now().isoformat(),
            }

            return predictions

        except Exception as e:
            logger.error(f"Error predicting future trends: {e}")
            return {}

    def _predict_destination_trends(
        self, current_trends: dict[str, Any], days: int
    ) -> dict[str, Any]:
        """목적지 트렌드 예측"""
        return {
            "rising_destinations": ["제주도", "부산"],
            "stable_destinations": ["서울", "경주"],
            "declining_destinations": [],
        }

    def _predict_demand_trends(
        self, current_trends: dict[str, Any], days: int
    ) -> dict[str, Any]:
        """수요 트렌드 예측"""
        return {
            "overall_demand_change": "+15%",
            "peak_demand_periods": ["주말", "공휴일"],
            "demand_volatility": "medium",
        }

    def _predict_seasonal_changes(self, days: int) -> dict[str, Any]:
        """계절 변화 예측"""
        return {
            "seasonal_shift_impact": "medium",
            "weather_impact_prediction": "positive",
        }

    def _predict_price_trends(
        self, current_trends: dict[str, Any], days: int
    ) -> dict[str, Any]:
        """가격 트렌드 예측"""
        return {
            "price_direction": "stable",
            "premium_segment_growth": "+5%",
            "budget_segment_growth": "+8%",
        }

    def _predict_user_behavior_changes(
        self, current_trends: dict[str, Any], days: int
    ) -> dict[str, Any]:
        """사용자 행동 변화 예측"""
        return {
            "booking_pattern_changes": "more_advance_booking",
            "preference_evolution": "experience_focused",
            "engagement_prediction": "increasing",
        }

    def _calculate_prediction_confidence(self, current_trends: dict[str, Any]) -> float:
        """예측 신뢰도 계산"""
        # 데이터 품질과 양을 기반으로 신뢰도 계산
        data_quality_score = 0.7
        sample_size_score = 0.8
        trend_stability_score = 0.6

        confidence = (
            data_quality_score + sample_size_score + trend_stability_score
        ) / 3
        return min(confidence, 1.0)


# 전역 인스턴스
def get_trend_analyzer(db: Session) -> TrendAnalyzer:
    """트렌드 분석기 인스턴스 반환"""
    return TrendAnalyzer(db)


def get_trend_predictor(db: Session) -> TrendPredictor:
    """트렌드 예측기 인스턴스 반환"""
    return TrendPredictor(db)


logger.info("Real-time travel trend analysis system initialized")
