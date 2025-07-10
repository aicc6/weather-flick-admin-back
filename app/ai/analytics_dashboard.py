"""
고급 분석 대시보드 시스템
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import and_, asc, desc, func
from sqlalchemy.orm import Session

from app.ai.ml_models import get_ml_integration
from app.logging_config import get_logger
from app.models import (
    Destination,
    Review,
    TravelPlan,
    User,
    UserPreference,
)
from app.utils.async_processing import AsyncBatch

logger = get_logger("analytics_dashboard")


class DashboardType(Enum):
    """대시보드 유형"""

    OVERVIEW = "overview"
    USER_ANALYTICS = "user_analytics"
    DESTINATION_ANALYTICS = "destination_analytics"
    TRAVEL_PATTERNS = "travel_patterns"
    PERFORMANCE_METRICS = "performance_metrics"
    PREDICTION_ANALYTICS = "prediction_analytics"
    REAL_TIME_MONITORING = "real_time_monitoring"
    RECOMMENDATION_INSIGHTS = "recommendation_insights"


class MetricPeriod(Enum):
    """메트릭 기간"""

    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class AnalyticsMetric:
    """분석 메트릭"""

    name: str
    value: float
    unit: str
    trend: str  # up, down, stable
    change_percent: float
    period: MetricPeriod
    timestamp: datetime
    metadata: dict[str, Any] | None = None


@dataclass
class DashboardWidget:
    """대시보드 위젯"""

    widget_id: str
    title: str
    widget_type: str  # chart, table, metric, map, etc.
    data: Any
    config: dict[str, Any]
    last_updated: datetime
    refresh_interval: int = 300  # seconds


@dataclass
class DashboardData:
    """대시보드 데이터"""

    dashboard_type: DashboardType
    title: str
    description: str
    widgets: list[DashboardWidget]
    metrics: list[AnalyticsMetric]
    filters: dict[str, Any]
    generated_at: datetime
    expires_at: datetime


class UserAnalytics:
    """사용자 분석"""

    def __init__(self, db: Session):
        self.db = db

    async def get_user_overview_metrics(
        self, period: MetricPeriod = MetricPeriod.MONTHLY
    ) -> list[AnalyticsMetric]:
        """사용자 개요 메트릭"""
        try:
            period_start = self._get_period_start(period)

            # 총 사용자 수
            total_users = self.db.query(User).count()

            # 신규 사용자 수
            new_users = (
                self.db.query(User).filter(User.created_at >= period_start).count()
            )

            # 활성 사용자 수 (최근 30일 내 로그인)
            active_users = (
                self.db.query(User)
                .filter(
                    and_(
                        User.last_login.isnot(None),
                        User.last_login >= datetime.now() - timedelta(days=30),
                    )
                )
                .count()
            )

            # 이전 기간과 비교
            prev_period_start = self._get_period_start(period, offset=1)
            prev_new_users = (
                self.db.query(User)
                .filter(
                    and_(
                        User.created_at >= prev_period_start,
                        User.created_at < period_start,
                    )
                )
                .count()
            )

            new_users_change = self._calculate_change_percent(new_users, prev_new_users)

            metrics = [
                AnalyticsMetric(
                    name="총 사용자 수",
                    value=total_users,
                    unit="명",
                    trend="up" if new_users > 0 else "stable",
                    change_percent=0.0,
                    period=period,
                    timestamp=datetime.now(),
                ),
                AnalyticsMetric(
                    name="신규 사용자",
                    value=new_users,
                    unit="명",
                    trend=self._get_trend(new_users_change),
                    change_percent=new_users_change,
                    period=period,
                    timestamp=datetime.now(),
                ),
                AnalyticsMetric(
                    name="활성 사용자",
                    value=active_users,
                    unit="명",
                    trend="stable",
                    change_percent=0.0,
                    period=period,
                    timestamp=datetime.now(),
                ),
            ]

            return metrics

        except Exception as e:
            logger.error(f"Error getting user overview metrics: {e}")
            return []

    async def get_user_engagement_data(self) -> dict[str, Any]:
        """사용자 참여도 데이터"""
        try:
            # 사용자별 여행 계획 수
            travel_plans_data = self.db.query(
                func.count(TravelPlan.plan_id).label("plan_count"),
                func.count(func.distinct(TravelPlan.user_id)).label("user_count"),
            ).scalar()

            # 사용자별 리뷰 수
            reviews_data = self.db.query(
                func.count(Review.review_id).label("review_count"),
                func.count(func.distinct(Review.user_id)).label("user_count"),
            ).first()

            # 월별 활동 추이
            monthly_activity = (
                self.db.query(
                    func.extract("year", TravelPlan.created_at).label("year"),
                    func.extract("month", TravelPlan.created_at).label("month"),
                    func.count(TravelPlan.plan_id).label("plan_count"),
                )
                .filter(TravelPlan.created_at >= datetime.now() - timedelta(days=365))
                .group_by(
                    func.extract("year", TravelPlan.created_at),
                    func.extract("month", TravelPlan.created_at),
                )
                .order_by(asc("year"), asc("month"))
                .all()
            )

            activity_chart_data = []
            for activity in monthly_activity:
                activity_chart_data.append(
                    {
                        "period": f"{int(activity.year)}-{int(activity.month):02d}",
                        "value": activity.plan_count,
                    }
                )

            return {
                "engagement_summary": {
                    "avg_plans_per_user": travel_plans_data
                    / max(1, self.db.query(User).count()),
                    "avg_reviews_per_user": (
                        reviews_data.review_count / max(1, reviews_data.user_count)
                        if reviews_data
                        else 0
                    ),
                },
                "activity_trend": activity_chart_data,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting user engagement data: {e}")
            return {}

    async def get_user_segmentation_data(self) -> dict[str, Any]:
        """사용자 세분화 데이터"""
        try:
            # 활동 수준별 사용자 분류
            user_segments = []

            # 고활동 사용자 (월 2회 이상 계획)
            high_activity_users = (
                self.db.query(
                    TravelPlan.user_id,
                    func.count(TravelPlan.plan_id).label("plan_count"),
                )
                .filter(TravelPlan.created_at >= datetime.now() - timedelta(days=30))
                .group_by(TravelPlan.user_id)
                .having(func.count(TravelPlan.plan_id) >= 2)
                .count()
            )

            # 중활동 사용자 (월 1회 계획)
            medium_activity_users = (
                self.db.query(
                    TravelPlan.user_id,
                    func.count(TravelPlan.plan_id).label("plan_count"),
                )
                .filter(TravelPlan.created_at >= datetime.now() - timedelta(days=30))
                .group_by(TravelPlan.user_id)
                .having(func.count(TravelPlan.plan_id) == 1)
                .count()
            )

            # 저활동 사용자
            total_users = self.db.query(User).count()
            low_activity_users = (
                total_users - high_activity_users - medium_activity_users
            )

            segmentation_data = [
                {
                    "segment": "고활동",
                    "count": high_activity_users,
                    "percentage": (high_activity_users / total_users) * 100,
                },
                {
                    "segment": "중활동",
                    "count": medium_activity_users,
                    "percentage": (medium_activity_users / total_users) * 100,
                },
                {
                    "segment": "저활동",
                    "count": low_activity_users,
                    "percentage": (low_activity_users / total_users) * 100,
                },
            ]

            # 지역별 사용자 분포
            regional_distribution = (
                self.db.query(
                    UserPreference.preferred_region,
                    func.count(UserPreference.user_id).label("user_count"),
                )
                .filter(UserPreference.preferred_region.isnot(None))
                .group_by(UserPreference.preferred_region)
                .order_by(desc("user_count"))
                .limit(10)
                .all()
            )

            regional_data = []
            for region_data in regional_distribution:
                regional_data.append(
                    {
                        "region": region_data.preferred_region,
                        "count": region_data.user_count,
                    }
                )

            return {
                "activity_segmentation": segmentation_data,
                "regional_distribution": regional_data,
                "total_users": total_users,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting user segmentation data: {e}")
            return {}

    def _get_period_start(self, period: MetricPeriod, offset: int = 0) -> datetime:
        """기간 시작일 계산"""
        now = datetime.now()

        if period == MetricPeriod.DAILY:
            return now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
                days=offset
            )
        elif period == MetricPeriod.WEEKLY:
            days_since_monday = now.weekday()
            return (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(weeks=offset)
        elif period == MetricPeriod.MONTHLY:
            return now.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=offset * 30)
        elif period == MetricPeriod.YEARLY:
            return now.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=offset * 365)
        else:
            return now - timedelta(hours=1)

    def _calculate_change_percent(self, current: float, previous: float) -> float:
        """변화율 계산"""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - previous) / previous) * 100

    def _get_trend(self, change_percent: float) -> str:
        """트렌드 결정"""
        if abs(change_percent) < 5:
            return "stable"
        elif change_percent > 0:
            return "up"
        else:
            return "down"


class DestinationAnalytics:
    """목적지 분석"""

    def __init__(self, db: Session):
        self.db = db

    async def get_destination_popularity_metrics(self) -> list[AnalyticsMetric]:
        """목적지 인기도 메트릭"""
        try:
            # 가장 인기있는 목적지 (리뷰 수 기준)
            popular_destinations = (
                self.db.query(
                    Destination.name,
                    func.count(Review.review_id).label("review_count"),
                    func.avg(Review.rating).label("avg_rating"),
                )
                .join(Review, Destination.destination_id == Review.destination_id)
                .group_by(Destination.destination_id, Destination.name)
                .order_by(desc("review_count"))
                .limit(5)
                .all()
            )

            # 평점이 높은 목적지
            top_rated_destinations = (
                self.db.query(
                    Destination.name,
                    func.avg(Review.rating).label("avg_rating"),
                    func.count(Review.review_id).label("review_count"),
                )
                .join(Review, Destination.destination_id == Review.destination_id)
                .group_by(Destination.destination_id, Destination.name)
                .having(func.count(Review.review_id) >= 5)  # 최소 5개 리뷰
                .order_by(desc("avg_rating"))
                .limit(5)
                .all()
            )

            metrics = []

            if popular_destinations:
                most_popular = popular_destinations[0]
                metrics.append(
                    AnalyticsMetric(
                        name="가장 인기있는 목적지",
                        value=most_popular.review_count,
                        unit="리뷰",
                        trend="up",
                        change_percent=0.0,
                        period=MetricPeriod.MONTHLY,
                        timestamp=datetime.now(),
                        metadata={"destination_name": most_popular.name},
                    )
                )

            if top_rated_destinations:
                top_rated = top_rated_destinations[0]
                metrics.append(
                    AnalyticsMetric(
                        name="최고 평점 목적지",
                        value=round(top_rated.avg_rating, 2),
                        unit="점",
                        trend="stable",
                        change_percent=0.0,
                        period=MetricPeriod.MONTHLY,
                        timestamp=datetime.now(),
                        metadata={"destination_name": top_rated.name},
                    )
                )

            return metrics

        except Exception as e:
            logger.error(f"Error getting destination popularity metrics: {e}")
            return []

    async def get_destination_performance_data(self) -> dict[str, Any]:
        """목적지 성과 데이터"""
        try:
            # 카테고리별 목적지 분포
            category_distribution = (
                self.db.query(
                    Destination.category,
                    func.count(Destination.destination_id).label("count"),
                )
                .group_by(Destination.category)
                .all()
            )

            category_data = []
            for cat_data in category_distribution:
                category_data.append(
                    {"category": cat_data.category, "count": cat_data.count}
                )

            # 지역별 목적지 분포
            regional_distribution = (
                self.db.query(
                    Destination.region,
                    func.count(Destination.destination_id).label("count"),
                )
                .group_by(Destination.region)
                .order_by(desc("count"))
                .all()
            )

            regional_data = []
            for region_data in regional_distribution:
                regional_data.append(
                    {"region": region_data.region, "count": region_data.count}
                )

            # 평점 분포
            rating_distribution = (
                self.db.query(
                    func.floor(Review.rating).label("rating_floor"),
                    func.count(Review.review_id).label("count"),
                )
                .filter(Review.rating.isnot(None))
                .group_by(func.floor(Review.rating))
                .order_by("rating_floor")
                .all()
            )

            rating_data = []
            for rating in rating_distribution:
                rating_data.append(
                    {"rating": f"{int(rating.rating_floor)}점", "count": rating.count}
                )

            return {
                "category_distribution": category_data,
                "regional_distribution": regional_data,
                "rating_distribution": rating_data,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting destination performance data: {e}")
            return {}

    async def get_destination_trends_data(self) -> dict[str, Any]:
        """목적지 트렌드 데이터"""
        try:
            # 월별 리뷰 트렌드
            monthly_reviews = (
                self.db.query(
                    func.extract("year", Review.created_at).label("year"),
                    func.extract("month", Review.created_at).label("month"),
                    func.count(Review.review_id).label("review_count"),
                )
                .filter(Review.created_at >= datetime.now() - timedelta(days=365))
                .group_by(
                    func.extract("year", Review.created_at),
                    func.extract("month", Review.created_at),
                )
                .order_by(asc("year"), asc("month"))
                .all()
            )

            review_trend_data = []
            for review in monthly_reviews:
                review_trend_data.append(
                    {
                        "period": f"{int(review.year)}-{int(review.month):02d}",
                        "value": review.review_count,
                    }
                )

            # 최근 급상승 목적지
            recent_trending = (
                self.db.query(
                    Destination.name,
                    Destination.category,
                    func.count(Review.review_id).label("recent_reviews"),
                )
                .join(Review, Destination.destination_id == Review.destination_id)
                .filter(Review.created_at >= datetime.now() - timedelta(days=30))
                .group_by(
                    Destination.destination_id, Destination.name, Destination.category
                )
                .order_by(desc("recent_reviews"))
                .limit(10)
                .all()
            )

            trending_data = []
            for trending in recent_trending:
                trending_data.append(
                    {
                        "name": trending.name,
                        "category": trending.category,
                        "recent_reviews": trending.recent_reviews,
                    }
                )

            return {
                "review_trends": review_trend_data,
                "trending_destinations": trending_data,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting destination trends data: {e}")
            return {}


class TravelPatternAnalytics:
    """여행 패턴 분석"""

    def __init__(self, db: Session):
        self.db = db

    async def get_travel_pattern_metrics(self) -> list[AnalyticsMetric]:
        """여행 패턴 메트릭"""
        try:
            # 평균 여행 기간
            avg_duration = (
                self.db.query(
                    func.avg(
                        func.datediff(TravelPlan.end_date, TravelPlan.start_date)
                    ).label("avg_duration")
                )
                .filter(
                    and_(
                        TravelPlan.start_date.isnot(None),
                        TravelPlan.end_date.isnot(None),
                    )
                )
                .scalar()
            )

            # 월별 여행 계획 수
            monthly_plans = (
                self.db.query(func.count(TravelPlan.plan_id))
                .filter(TravelPlan.created_at >= datetime.now() - timedelta(days=30))
                .scalar()
            )

            # 이전 달과 비교
            prev_month_plans = (
                self.db.query(func.count(TravelPlan.plan_id))
                .filter(
                    and_(
                        TravelPlan.created_at >= datetime.now() - timedelta(days=60),
                        TravelPlan.created_at < datetime.now() - timedelta(days=30),
                    )
                )
                .scalar()
            )

            plans_change = (
                (monthly_plans - prev_month_plans) / max(prev_month_plans, 1)
            ) * 100

            metrics = [
                AnalyticsMetric(
                    name="평균 여행 기간",
                    value=round(avg_duration or 0, 1),
                    unit="일",
                    trend="stable",
                    change_percent=0.0,
                    period=MetricPeriod.MONTHLY,
                    timestamp=datetime.now(),
                ),
                AnalyticsMetric(
                    name="월간 여행 계획",
                    value=monthly_plans or 0,
                    unit="건",
                    trend=(
                        "up"
                        if plans_change > 0
                        else "down" if plans_change < 0 else "stable"
                    ),
                    change_percent=plans_change,
                    period=MetricPeriod.MONTHLY,
                    timestamp=datetime.now(),
                ),
            ]

            return metrics

        except Exception as e:
            logger.error(f"Error getting travel pattern metrics: {e}")
            return []

    async def get_seasonal_pattern_data(self) -> dict[str, Any]:
        """계절별 패턴 데이터"""
        try:
            # 월별 여행 계획 분포
            monthly_distribution = (
                self.db.query(
                    func.extract("month", TravelPlan.start_date).label("month"),
                    func.count(TravelPlan.plan_id).label("plan_count"),
                )
                .filter(TravelPlan.start_date.isnot(None))
                .group_by(func.extract("month", TravelPlan.start_date))
                .order_by("month")
                .all()
            )

            seasonal_data = []
            month_names = [
                "1월",
                "2월",
                "3월",
                "4월",
                "5월",
                "6월",
                "7월",
                "8월",
                "9월",
                "10월",
                "11월",
                "12월",
            ]

            for month_data in monthly_distribution:
                month_idx = int(month_data.month) - 1
                seasonal_data.append(
                    {"month": month_names[month_idx], "plans": month_data.plan_count}
                )

            # 요일별 여행 시작 패턴
            weekday_distribution = (
                self.db.query(
                    func.extract("dow", TravelPlan.start_date).label("weekday"),
                    func.count(TravelPlan.plan_id).label("plan_count"),
                )
                .filter(TravelPlan.start_date.isnot(None))
                .group_by(func.extract("dow", TravelPlan.start_date))
                .order_by("weekday")
                .all()
            )

            weekday_data = []
            weekday_names = [
                "일요일",
                "월요일",
                "화요일",
                "수요일",
                "목요일",
                "금요일",
                "토요일",
            ]

            for weekday in weekday_distribution:
                day_idx = int(weekday.weekday)
                weekday_data.append(
                    {"weekday": weekday_names[day_idx], "plans": weekday.plan_count}
                )

            return {
                "seasonal_patterns": seasonal_data,
                "weekday_patterns": weekday_data,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting seasonal pattern data: {e}")
            return {}

    async def get_duration_analysis_data(self) -> dict[str, Any]:
        """여행 기간 분석 데이터"""
        try:
            # 여행 기간별 분포
            duration_distribution = (
                self.db.query(
                    func.datediff(TravelPlan.end_date, TravelPlan.start_date).label(
                        "duration"
                    ),
                    func.count(TravelPlan.plan_id).label("count"),
                )
                .filter(
                    and_(
                        TravelPlan.start_date.isnot(None),
                        TravelPlan.end_date.isnot(None),
                    )
                )
                .group_by(func.datediff(TravelPlan.end_date, TravelPlan.start_date))
                .order_by("duration")
                .all()
            )

            duration_data = []
            for duration in duration_distribution:
                if duration.duration <= 7:  # 7일 이하만 분석
                    duration_data.append(
                        {"duration": f"{duration.duration}일", "count": duration.count}
                    )

            # 지역별 평균 여행 기간
            regional_duration = (
                self.db.query(
                    UserPreference.preferred_region,
                    func.avg(
                        func.datediff(TravelPlan.end_date, TravelPlan.start_date)
                    ).label("avg_duration"),
                )
                .join(User, UserPreference.user_id == User.user_id)
                .join(TravelPlan, User.user_id == TravelPlan.user_id)
                .filter(
                    and_(
                        TravelPlan.start_date.isnot(None),
                        TravelPlan.end_date.isnot(None),
                        UserPreference.preferred_region.isnot(None),
                    )
                )
                .group_by(UserPreference.preferred_region)
                .order_by(desc("avg_duration"))
                .limit(10)
                .all()
            )

            regional_data = []
            for region in regional_duration:
                regional_data.append(
                    {
                        "region": region.preferred_region,
                        "avg_duration": round(region.avg_duration, 1),
                    }
                )

            return {
                "duration_distribution": duration_data,
                "regional_duration": regional_data,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting duration analysis data: {e}")
            return {}


class PerformanceMetrics:
    """성능 메트릭"""

    def __init__(self, db: Session):
        self.db = db

    async def get_system_performance_metrics(self) -> list[AnalyticsMetric]:
        """시스템 성능 메트릭"""
        try:
            # AI 추천 시스템 성능 (가상 데이터)
            recommendation_accuracy = 0.78  # 실제로는 ML 모델에서 가져옴

            # API 응답 시간 (가상 데이터)
            avg_response_time = 250  # ms

            # 사용자 만족도 (리뷰 평점 기준)
            user_satisfaction = (
                self.db.query(func.avg(Review.rating))
                .filter(
                    and_(
                        Review.rating.isnot(None),
                        Review.created_at >= datetime.now() - timedelta(days=30),
                    )
                )
                .scalar()
            )

            # 추천 클릭률 (가상 데이터)
            recommendation_ctr = 0.15  # 15%

            metrics = [
                AnalyticsMetric(
                    name="추천 정확도",
                    value=recommendation_accuracy,
                    unit="%",
                    trend="up",
                    change_percent=2.5,
                    period=MetricPeriod.MONTHLY,
                    timestamp=datetime.now(),
                ),
                AnalyticsMetric(
                    name="평균 응답 시간",
                    value=avg_response_time,
                    unit="ms",
                    trend="down",  # 낮을수록 좋음
                    change_percent=-5.2,
                    period=MetricPeriod.DAILY,
                    timestamp=datetime.now(),
                ),
                AnalyticsMetric(
                    name="사용자 만족도",
                    value=round(user_satisfaction or 0, 2),
                    unit="점",
                    trend="stable",
                    change_percent=0.8,
                    period=MetricPeriod.MONTHLY,
                    timestamp=datetime.now(),
                ),
                AnalyticsMetric(
                    name="추천 클릭률",
                    value=recommendation_ctr,
                    unit="%",
                    trend="up",
                    change_percent=3.2,
                    period=MetricPeriod.WEEKLY,
                    timestamp=datetime.now(),
                ),
            ]

            return metrics

        except Exception as e:
            logger.error(f"Error getting system performance metrics: {e}")
            return []

    async def get_ml_model_performance_data(self) -> dict[str, Any]:
        """ML 모델 성능 데이터"""
        try:
            # 실제로는 ML 모델 통합 시스템에서 데이터 가져옴
            ml_integration = get_ml_integration()
            performance_report = ml_integration.get_model_performance_report()

            # 모델별 성능 요약
            model_performance = []
            for model in performance_report.get("models", []):
                model_performance.append(
                    {
                        "name": model["name"],
                        "accuracy": model["accuracy"],
                        "precision": model["precision"],
                        "recall": model["recall"],
                        "f1_score": model["f1_score"],
                    }
                )

            # 성능 트렌드 (가상 데이터)
            performance_trend = [
                {"date": "2024-01", "accuracy": 0.72},
                {"date": "2024-02", "accuracy": 0.75},
                {"date": "2024-03", "accuracy": 0.78},
                {"date": "2024-04", "accuracy": 0.81},
                {"date": "2024-05", "accuracy": 0.78},
            ]

            return {
                "model_performance": model_performance,
                "performance_trend": performance_trend,
                "best_performing_model": performance_report.get("best_performing"),
                "recommendations": performance_report.get("recommendations", []),
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting ML model performance data: {e}")
            return {}


class AnalyticsDashboard:
    """고급 분석 대시보드 메인 클래스"""

    def __init__(self, db: Session):
        self.db = db
        self.user_analytics = UserAnalytics(db)
        self.destination_analytics = DestinationAnalytics(db)
        self.travel_pattern_analytics = TravelPatternAnalytics(db)
        self.performance_metrics = PerformanceMetrics(db)
        self.batch_processor = AsyncBatch(batch_size=5, max_concurrent=3)

    async def generate_dashboard(
        self, dashboard_type: DashboardType, filters: dict[str, Any] | None = None
    ) -> DashboardData:
        """대시보드 생성"""
        try:
            if dashboard_type == DashboardType.OVERVIEW:
                return await self._generate_overview_dashboard(filters)
            elif dashboard_type == DashboardType.USER_ANALYTICS:
                return await self._generate_user_analytics_dashboard(filters)
            elif dashboard_type == DashboardType.DESTINATION_ANALYTICS:
                return await self._generate_destination_analytics_dashboard(filters)
            elif dashboard_type == DashboardType.TRAVEL_PATTERNS:
                return await self._generate_travel_patterns_dashboard(filters)
            elif dashboard_type == DashboardType.PERFORMANCE_METRICS:
                return await self._generate_performance_dashboard(filters)
            elif dashboard_type == DashboardType.REAL_TIME_MONITORING:
                return await self._generate_realtime_dashboard(filters)
            else:
                return await self._generate_overview_dashboard(filters)

        except Exception as e:
            logger.error(f"Error generating dashboard: {e}")
            raise

    async def _generate_overview_dashboard(
        self, filters: dict[str, Any] | None = None
    ) -> DashboardData:
        """개요 대시보드 생성"""
        try:
            # 주요 메트릭 수집
            user_metrics = await self.user_analytics.get_user_overview_metrics()
            destination_metrics = (
                await self.destination_analytics.get_destination_popularity_metrics()
            )
            travel_metrics = (
                await self.travel_pattern_analytics.get_travel_pattern_metrics()
            )
            performance_metrics = (
                await self.performance_metrics.get_system_performance_metrics()
            )

            all_metrics = (
                user_metrics
                + destination_metrics
                + travel_metrics
                + performance_metrics
            )

            # 위젯 생성
            widgets = [
                DashboardWidget(
                    widget_id="overview_metrics",
                    title="주요 지표",
                    widget_type="metrics_grid",
                    data={"metrics": [asdict(metric) for metric in all_metrics[:8]]},
                    config={"columns": 4},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="user_engagement",
                    title="사용자 참여도",
                    widget_type="line_chart",
                    data=await self.user_analytics.get_user_engagement_data(),
                    config={"height": 300},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="destination_performance",
                    title="목적지 성과",
                    widget_type="bar_chart",
                    data=await self.destination_analytics.get_destination_performance_data(),
                    config={"height": 250},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="seasonal_patterns",
                    title="계절별 여행 패턴",
                    widget_type="area_chart",
                    data=await self.travel_pattern_analytics.get_seasonal_pattern_data(),
                    config={"height": 200},
                    last_updated=datetime.now(),
                ),
            ]

            return DashboardData(
                dashboard_type=DashboardType.OVERVIEW,
                title="전체 개요 대시보드",
                description="시스템 전반의 주요 지표와 트렌드",
                widgets=widgets,
                metrics=all_metrics,
                filters=filters or {},
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=1),
            )

        except Exception as e:
            logger.error(f"Error generating overview dashboard: {e}")
            raise

    async def _generate_user_analytics_dashboard(
        self, filters: dict[str, Any] | None = None
    ) -> DashboardData:
        """사용자 분석 대시보드 생성"""
        try:
            # 사용자 관련 메트릭 및 데이터 수집
            user_metrics = await self.user_analytics.get_user_overview_metrics()
            engagement_data = await self.user_analytics.get_user_engagement_data()
            segmentation_data = await self.user_analytics.get_user_segmentation_data()

            widgets = [
                DashboardWidget(
                    widget_id="user_metrics",
                    title="사용자 지표",
                    widget_type="metrics_grid",
                    data={"metrics": [asdict(metric) for metric in user_metrics]},
                    config={"columns": 3},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="user_activity_trend",
                    title="사용자 활동 추이",
                    widget_type="line_chart",
                    data=engagement_data,
                    config={"height": 350},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="user_segmentation",
                    title="사용자 세분화",
                    widget_type="pie_chart",
                    data=segmentation_data,
                    config={"height": 300},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="regional_distribution",
                    title="지역별 사용자 분포",
                    widget_type="map_chart",
                    data=segmentation_data,
                    config={"height": 400},
                    last_updated=datetime.now(),
                ),
            ]

            return DashboardData(
                dashboard_type=DashboardType.USER_ANALYTICS,
                title="사용자 분석 대시보드",
                description="사용자 행동 패턴 및 세분화 분석",
                widgets=widgets,
                metrics=user_metrics,
                filters=filters or {},
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=2),
            )

        except Exception as e:
            logger.error(f"Error generating user analytics dashboard: {e}")
            raise

    async def _generate_destination_analytics_dashboard(
        self, filters: dict[str, Any] | None = None
    ) -> DashboardData:
        """목적지 분석 대시보드 생성"""
        try:
            destination_metrics = (
                await self.destination_analytics.get_destination_popularity_metrics()
            )
            performance_data = (
                await self.destination_analytics.get_destination_performance_data()
            )
            trends_data = await self.destination_analytics.get_destination_trends_data()

            widgets = [
                DashboardWidget(
                    widget_id="destination_metrics",
                    title="목적지 지표",
                    widget_type="metrics_grid",
                    data={
                        "metrics": [asdict(metric) for metric in destination_metrics]
                    },
                    config={"columns": 2},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="category_distribution",
                    title="카테고리별 분포",
                    widget_type="pie_chart",
                    data=performance_data,
                    config={"height": 300},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="regional_performance",
                    title="지역별 성과",
                    widget_type="bar_chart",
                    data=performance_data,
                    config={"height": 350},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="trending_destinations",
                    title="트렌딩 목적지",
                    widget_type="table",
                    data=trends_data,
                    config={"paginate": True},
                    last_updated=datetime.now(),
                ),
            ]

            return DashboardData(
                dashboard_type=DashboardType.DESTINATION_ANALYTICS,
                title="목적지 분석 대시보드",
                description="목적지별 성과 및 트렌드 분석",
                widgets=widgets,
                metrics=destination_metrics,
                filters=filters or {},
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=2),
            )

        except Exception as e:
            logger.error(f"Error generating destination analytics dashboard: {e}")
            raise

    async def _generate_travel_patterns_dashboard(
        self, filters: dict[str, Any] | None = None
    ) -> DashboardData:
        """여행 패턴 대시보드 생성"""
        try:
            pattern_metrics = (
                await self.travel_pattern_analytics.get_travel_pattern_metrics()
            )
            seasonal_data = (
                await self.travel_pattern_analytics.get_seasonal_pattern_data()
            )
            duration_data = (
                await self.travel_pattern_analytics.get_duration_analysis_data()
            )

            widgets = [
                DashboardWidget(
                    widget_id="pattern_metrics",
                    title="여행 패턴 지표",
                    widget_type="metrics_grid",
                    data={"metrics": [asdict(metric) for metric in pattern_metrics]},
                    config={"columns": 2},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="seasonal_patterns",
                    title="계절별 패턴",
                    widget_type="line_chart",
                    data=seasonal_data,
                    config={"height": 300},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="weekday_patterns",
                    title="요일별 패턴",
                    widget_type="bar_chart",
                    data=seasonal_data,
                    config={"height": 250},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="duration_analysis",
                    title="여행 기간 분석",
                    widget_type="histogram",
                    data=duration_data,
                    config={"height": 300},
                    last_updated=datetime.now(),
                ),
            ]

            return DashboardData(
                dashboard_type=DashboardType.TRAVEL_PATTERNS,
                title="여행 패턴 분석 대시보드",
                description="여행 행동 패턴 및 계절성 분석",
                widgets=widgets,
                metrics=pattern_metrics,
                filters=filters or {},
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=3),
            )

        except Exception as e:
            logger.error(f"Error generating travel patterns dashboard: {e}")
            raise

    async def _generate_performance_dashboard(
        self, filters: dict[str, Any] | None = None
    ) -> DashboardData:
        """성능 대시보드 생성"""
        try:
            perf_metrics = (
                await self.performance_metrics.get_system_performance_metrics()
            )
            ml_performance_data = (
                await self.performance_metrics.get_ml_model_performance_data()
            )

            widgets = [
                DashboardWidget(
                    widget_id="performance_metrics",
                    title="시스템 성능 지표",
                    widget_type="metrics_grid",
                    data={"metrics": [asdict(metric) for metric in perf_metrics]},
                    config={"columns": 4},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="ml_model_performance",
                    title="ML 모델 성능",
                    widget_type="table",
                    data=ml_performance_data,
                    config={"sortable": True},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="performance_trend",
                    title="성능 트렌드",
                    widget_type="line_chart",
                    data=ml_performance_data,
                    config={"height": 300},
                    last_updated=datetime.now(),
                ),
                DashboardWidget(
                    widget_id="recommendations",
                    title="개선 권장사항",
                    widget_type="list",
                    data=ml_performance_data,
                    config={"max_items": 10},
                    last_updated=datetime.now(),
                ),
            ]

            return DashboardData(
                dashboard_type=DashboardType.PERFORMANCE_METRICS,
                title="성능 모니터링 대시보드",
                description="시스템 성능 및 ML 모델 성과 분석",
                widgets=widgets,
                metrics=perf_metrics,
                filters=filters or {},
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=30),
            )

        except Exception as e:
            logger.error(f"Error generating performance dashboard: {e}")
            raise

    async def _generate_realtime_dashboard(
        self, filters: dict[str, Any] | None = None
    ) -> DashboardData:
        """실시간 모니터링 대시보드 생성"""
        try:
            # 실시간 데이터 (가상)
            realtime_metrics = [
                AnalyticsMetric(
                    name="현재 접속자",
                    value=127,
                    unit="명",
                    trend="up",
                    change_percent=5.2,
                    period=MetricPeriod.REAL_TIME,
                    timestamp=datetime.now(),
                ),
                AnalyticsMetric(
                    name="금일 신규 가입",
                    value=23,
                    unit="명",
                    trend="up",
                    change_percent=12.5,
                    period=MetricPeriod.DAILY,
                    timestamp=datetime.now(),
                ),
                AnalyticsMetric(
                    name="시간당 요청",
                    value=1245,
                    unit="건",
                    trend="stable",
                    change_percent=-2.1,
                    period=MetricPeriod.HOURLY,
                    timestamp=datetime.now(),
                ),
            ]

            widgets = [
                DashboardWidget(
                    widget_id="realtime_metrics",
                    title="실시간 지표",
                    widget_type="metrics_grid",
                    data={"metrics": [asdict(metric) for metric in realtime_metrics]},
                    config={"columns": 3, "auto_refresh": True},
                    last_updated=datetime.now(),
                    refresh_interval=30,
                ),
                DashboardWidget(
                    widget_id="active_users_chart",
                    title="실시간 활성 사용자",
                    widget_type="realtime_chart",
                    data={"type": "line", "realtime": True},
                    config={"height": 300, "auto_refresh": True},
                    last_updated=datetime.now(),
                    refresh_interval=60,
                ),
                DashboardWidget(
                    widget_id="system_health",
                    title="시스템 상태",
                    widget_type="status_grid",
                    data={
                        "services": [
                            {"name": "API 서버", "status": "healthy"},
                            {"name": "데이터베이스", "status": "healthy"},
                            {"name": "AI 엔진", "status": "healthy"},
                            {"name": "캐시 서버", "status": "warning"},
                        ]
                    },
                    config={"auto_refresh": True},
                    last_updated=datetime.now(),
                    refresh_interval=120,
                ),
            ]

            return DashboardData(
                dashboard_type=DashboardType.REAL_TIME_MONITORING,
                title="실시간 모니터링 대시보드",
                description="시스템 실시간 상태 및 활동 모니터링",
                widgets=widgets,
                metrics=realtime_metrics,
                filters=filters or {},
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=5),
            )

        except Exception as e:
            logger.error(f"Error generating realtime dashboard: {e}")
            raise

    async def refresh_dashboard_widget(
        self, dashboard_type: DashboardType, widget_id: str
    ) -> DashboardWidget | None:
        """위젯 새로고침"""
        try:
            # 위젯별 새로고침 로직
            if widget_id == "realtime_metrics":
                # 실시간 메트릭 업데이트
                pass
            elif widget_id == "user_activity_trend":
                # 사용자 활동 트렌드 업데이트
                pass
            # ... 기타 위젯들

            # 새로운 위젯 데이터 반환
            return None  # 실제 구현에서는 업데이트된 위젯 반환

        except Exception as e:
            logger.error(f"Error refreshing widget {widget_id}: {e}")
            return None

    def get_dashboard_statistics(self) -> dict[str, Any]:
        """대시보드 통계"""
        return {
            "total_dashboards": 6,
            "total_widgets": 20,
            "avg_generation_time": 2.5,  # seconds
            "cache_hit_rate": 0.75,
            "last_updated": datetime.now().isoformat(),
        }


# 분석 대시보드 시스템 싱글톤
analytics_dashboard = None


def get_analytics_dashboard(db: Session) -> AnalyticsDashboard:
    """분석 대시보드 시스템 인스턴스 반환"""
    global analytics_dashboard
    if analytics_dashboard is None:
        analytics_dashboard = AnalyticsDashboard(db)
    return analytics_dashboard


logger.info("Advanced analytics dashboard system initialized")
