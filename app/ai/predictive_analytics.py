"""
예측 분석 시스템
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np
try:
    import pandas as pd
except ImportError:
    pd = None
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import (
    Destination,
    Review,
    TravelPlan,
    User,
)

logger = get_logger("predictive_analytics")


@dataclass
class PredictionResult:
    """예측 결과"""

    prediction: float
    confidence: float
    factors: dict[str, float]
    timestamp: datetime
    model_version: str


class TravelDemandPredictor:
    """여행 수요 예측"""

    def __init__(self, db: Session):
        self.db = db
        self.model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.feature_columns = [
            "month",
            "day_of_week",
            "season",
            "temperature",
            "precipitation",
            "holiday_flag",
            "school_vacation",
            "economic_index",
        ]
        self.model_trained = False

    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """특성 준비"""
        # 날짜 특성 추출
        data["month"] = data["date"].dt.month
        data["day_of_week"] = data["date"].dt.dayofweek
        data["season"] = data["date"].dt.month.apply(self._get_season)

        # 기상 특성 (기본값 설정)
        data["temperature"] = data.get("temperature", 15.0)
        data["precipitation"] = data.get("precipitation", 0.0)

        # 사회적 특성
        data["holiday_flag"] = data["date"].apply(self._is_holiday)
        data["school_vacation"] = data["date"].apply(self._is_school_vacation)
        data["economic_index"] = 100.0  # 기본값

        return data[self.feature_columns]

    def _get_season(self, month: int) -> int:
        """계절 인덱스 반환"""
        if month in [12, 1, 2]:
            return 0  # 겨울
        elif month in [3, 4, 5]:
            return 1  # 봄
        elif month in [6, 7, 8]:
            return 2  # 여름
        else:
            return 3  # 가을

    def _is_holiday(self, date: datetime) -> int:
        """휴일 여부 확인"""
        # 간단한 휴일 체크 (실제로는 더 복잡한 로직 필요)
        return 1 if date.weekday() in [5, 6] else 0

    def _is_school_vacation(self, date: datetime) -> int:
        """학교 방학 여부 확인"""
        month = date.month
        # 여름방학(7-8월), 겨울방학(12-2월)
        return 1 if month in [7, 8, 12, 1, 2] else 0

    def collect_training_data(self) -> pd.DataFrame:
        """학습 데이터 수집"""
        try:
            # 여행 계획 데이터 수집
            travel_plans = (
                self.db.query(TravelPlan)
                .filter(TravelPlan.created_at >= datetime.now() - timedelta(days=365))
                .all()
            )

            # 데이터프레임 생성
            data = []
            for plan in travel_plans:
                data.append(
                    {
                        "date": plan.created_at,
                        "demand": 1,  # 여행 계획 생성 = 수요
                        "plan_id": plan.plan_id,
                        "user_id": plan.user_id,
                    }
                )

            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)

            # 일별 수요 집계
            daily_demand = (
                df.groupby(df["date"].dt.date).agg({"demand": "sum"}).reset_index()
            )
            daily_demand["date"] = pd.to_datetime(daily_demand["date"])

            return daily_demand

        except Exception as e:
            logger.error(f"Error collecting training data: {e}")
            return pd.DataFrame()

    def train_model(self) -> dict[str, Any]:
        """모델 학습"""
        try:
            # 학습 데이터 수집
            training_data = self.collect_training_data()

            if training_data.empty:
                return {"error": "No training data available"}

            # 특성 준비
            features = self.prepare_features(training_data)
            target = training_data["demand"]

            # 데이터 분할
            X_train, X_test, y_train, y_test = train_test_split(
                features, target, test_size=0.2, random_state=42
            )

            # 특성 스케일링
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # 모델 학습
            self.model.fit(X_train_scaled, y_train)

            # 모델 성능 평가
            y_pred = self.model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            self.model_trained = True

            return {
                "success": True,
                "mse": mse,
                "r2_score": r2,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "feature_importance": dict(
                    zip(self.feature_columns, self.model.feature_importances_, strict=False)
                ),
            }

        except Exception as e:
            logger.error(f"Error training demand prediction model: {e}")
            return {"error": str(e)}

    def predict_demand(
        self, start_date: datetime, end_date: datetime
    ) -> list[PredictionResult]:
        """수요 예측"""
        try:
            if not self.model_trained:
                train_result = self.train_model()
                if "error" in train_result:
                    return []

            # 예측 기간 생성
            date_range = pd.date_range(start=start_date, end=end_date, freq="D")

            # 예측 데이터 준비
            prediction_data = pd.DataFrame({"date": date_range})
            features = self.prepare_features(prediction_data)

            # 특성 스케일링
            features_scaled = self.scaler.transform(features)

            # 예측 수행
            predictions = self.model.predict(features_scaled)

            # 결과 생성
            results = []
            for i, (date, pred) in enumerate(zip(date_range, predictions, strict=False)):
                # 특성 중요도 계산
                feature_importance = dict(
                    zip(self.feature_columns, self.model.feature_importances_, strict=False)
                )

                results.append(
                    PredictionResult(
                        prediction=max(0, pred),  # 음수 예측 방지
                        confidence=0.8,  # 신뢰도 (실제로는 더 정교한 계산 필요)
                        factors=feature_importance,
                        timestamp=datetime.now(),
                        model_version="v1.0",
                    )
                )

            return results

        except Exception as e:
            logger.error(f"Error predicting demand: {e}")
            return []


class UserBehaviorPredictor:
    """사용자 행동 예측"""

    def __init__(self, db: Session):
        self.db = db
        self.churn_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.ltv_model = LinearRegression()
        self.scaler = StandardScaler()
        self.models_trained = False

    def prepare_user_features(self, user_id: str) -> dict[str, float]:
        """사용자 특성 준비"""
        try:
            # 사용자 기본 정보
            user = self.db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return {}

            # 활동 기록
            travel_plans = (
                self.db.query(TravelPlan).filter(TravelPlan.user_id == user_id).all()
            )

            reviews = self.db.query(Review).filter(Review.user_id == user_id).all()

            # 특성 계산
            days_since_signup = (datetime.now() - user.created_at).days
            days_since_last_login = (
                datetime.now() - (user.last_login or user.created_at)
            ).days

            features = {
                "days_since_signup": days_since_signup,
                "days_since_last_login": days_since_last_login,
                "total_travel_plans": len(travel_plans),
                "total_reviews": len(reviews),
                "avg_rating": (
                    sum(r.rating for r in reviews if r.rating) / len(reviews)
                    if reviews
                    else 0
                ),
                "activity_frequency": len(travel_plans)
                / max(days_since_signup, 1)
                * 30,  # 월 평균
                "engagement_score": len(reviews) / max(len(travel_plans), 1),
                "recency_score": max(0, 30 - days_since_last_login) / 30,
            }

            return features

        except Exception as e:
            logger.error(f"Error preparing user features: {e}")
            return {}

    def predict_churn_probability(self, user_id: str) -> PredictionResult:
        """이탈 확률 예측"""
        try:
            features = self.prepare_user_features(user_id)
            if not features:
                return PredictionResult(
                    prediction=0.5,
                    confidence=0.1,
                    factors={},
                    timestamp=datetime.now(),
                    model_version="v1.0",
                )

            # 간단한 규칙 기반 예측 (실제로는 ML 모델 사용)
            churn_score = 0.0

            # 최근 로그인 시간 기반
            if features["days_since_last_login"] > 30:
                churn_score += 0.4
            elif features["days_since_last_login"] > 14:
                churn_score += 0.2

            # 활동 빈도 기반
            if features["activity_frequency"] < 0.5:
                churn_score += 0.3

            # 참여도 기반
            if features["engagement_score"] < 0.3:
                churn_score += 0.2

            # 최근성 기반
            if features["recency_score"] < 0.3:
                churn_score += 0.1

            churn_probability = min(1.0, churn_score)

            return PredictionResult(
                prediction=churn_probability,
                confidence=0.7,
                factors=features,
                timestamp=datetime.now(),
                model_version="v1.0",
            )

        except Exception as e:
            logger.error(f"Error predicting churn probability: {e}")
            return PredictionResult(
                prediction=0.5,
                confidence=0.1,
                factors={},
                timestamp=datetime.now(),
                model_version="v1.0",
            )

    def predict_lifetime_value(self, user_id: str) -> PredictionResult:
        """생애 가치 예측"""
        try:
            features = self.prepare_user_features(user_id)
            if not features:
                return PredictionResult(
                    prediction=0.0,
                    confidence=0.1,
                    factors={},
                    timestamp=datetime.now(),
                    model_version="v1.0",
                )

            # 간단한 LTV 계산
            monthly_value = features["activity_frequency"] * 10000  # 월 평균 가치
            retention_months = max(
                1, (1 - features["days_since_last_login"] / 365) * 12
            )
            ltv = monthly_value * retention_months

            return PredictionResult(
                prediction=ltv,
                confidence=0.6,
                factors=features,
                timestamp=datetime.now(),
                model_version="v1.0",
            )

        except Exception as e:
            logger.error(f"Error predicting LTV: {e}")
            return PredictionResult(
                prediction=0.0,
                confidence=0.1,
                factors={},
                timestamp=datetime.now(),
                model_version="v1.0",
            )


class DestinationPopularityPredictor:
    """목적지 인기도 예측"""

    def __init__(self, db: Session):
        self.db = db
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.label_encoders = {}

    def prepare_destination_features(self, destination_id: str) -> dict[str, float]:
        """목적지 특성 준비"""
        try:
            destination = (
                self.db.query(Destination)
                .filter(Destination.destination_id == destination_id)
                .first()
            )

            if not destination:
                return {}

            # 리뷰 데이터
            reviews = (
                self.db.query(Review)
                .filter(Review.destination_id == destination_id)
                .all()
            )

            # 여행 계획 데이터 (실제로는 travel_day_destinations 테이블 조인)
            # 여기서는 간단히 리뷰 수로 대체
            visit_count = len(reviews)

            features = {
                "category_encoded": self._encode_category(destination.category),
                "region_encoded": self._encode_region(destination.region),
                "latitude": destination.latitude or 0.0,
                "longitude": destination.longitude or 0.0,
                "review_count": len(reviews),
                "avg_rating": (
                    sum(r.rating for r in reviews if r.rating) / len(reviews)
                    if reviews
                    else 0
                ),
                "recent_reviews": len(
                    [
                        r
                        for r in reviews
                        if r.created_at >= datetime.now() - timedelta(days=30)
                    ]
                ),
                "visit_count": visit_count,
                "rating_variance": self._calculate_rating_variance(reviews),
            }

            return features

        except Exception as e:
            logger.error(f"Error preparing destination features: {e}")
            return {}

    def _encode_category(self, category: str) -> float:
        """카테고리 인코딩"""
        if "category" not in self.label_encoders:
            self.label_encoders["category"] = LabelEncoder()
            # 실제 구현에서는 모든 카테고리로 fit
            categories = ["관광지", "음식점", "숙박", "쇼핑", "문화시설", "레저"]
            self.label_encoders["category"].fit(categories)

        try:
            return float(self.label_encoders["category"].transform([category])[0])
        except:
            return 0.0

    def _encode_region(self, region: str) -> float:
        """지역 인코딩"""
        if "region" not in self.label_encoders:
            self.label_encoders["region"] = LabelEncoder()
            # 실제 구현에서는 모든 지역으로 fit
            regions = [
                "서울",
                "부산",
                "대구",
                "인천",
                "광주",
                "대전",
                "울산",
                "세종",
                "경기",
                "강원",
                "충북",
                "충남",
                "전북",
                "전남",
                "경북",
                "경남",
                "제주",
            ]
            self.label_encoders["region"].fit(regions)

        try:
            return float(self.label_encoders["region"].transform([region])[0])
        except:
            return 0.0

    def _calculate_rating_variance(self, reviews: list[Review]) -> float:
        """평점 분산 계산"""
        ratings = [r.rating for r in reviews if r.rating]
        if len(ratings) < 2:
            return 0.0

        mean_rating = sum(ratings) / len(ratings)
        variance = sum((r - mean_rating) ** 2 for r in ratings) / len(ratings)
        return variance

    def predict_popularity_trend(
        self, destination_id: str, days_ahead: int = 30
    ) -> list[PredictionResult]:
        """인기도 트렌드 예측"""
        try:
            features = self.prepare_destination_features(destination_id)
            if not features:
                return []

            # 간단한 트렌드 예측
            base_popularity = features["visit_count"] + features["recent_reviews"]

            results = []
            for i in range(days_ahead):
                # 시간에 따른 인기도 변화 시뮬레이션
                trend_factor = 1.0 + (i / days_ahead) * 0.1  # 약간의 증가 트렌드
                seasonal_factor = 1.0 + 0.2 * np.sin(2 * np.pi * i / 365)  # 계절적 요소

                predicted_popularity = base_popularity * trend_factor * seasonal_factor

                results.append(
                    PredictionResult(
                        prediction=predicted_popularity,
                        confidence=0.6,
                        factors=features,
                        timestamp=datetime.now(),
                        model_version="v1.0",
                    )
                )

            return results

        except Exception as e:
            logger.error(f"Error predicting popularity trend: {e}")
            return []


class PredictiveAnalyticsEngine:
    """예측 분석 엔진 메인 클래스"""

    def __init__(self, db: Session):
        self.db = db
        self.demand_predictor = TravelDemandPredictor(db)
        self.user_predictor = UserBehaviorPredictor(db)
        self.destination_predictor = DestinationPopularityPredictor(db)

    async def get_demand_forecast(
        self, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """수요 예측 보고서"""
        try:
            predictions = self.demand_predictor.predict_demand(start_date, end_date)

            if not predictions:
                return {"error": "No predictions available"}

            # 예측 결과 요약
            total_demand = sum(p.prediction for p in predictions)
            avg_confidence = sum(p.confidence for p in predictions) / len(predictions)
            peak_demand = max(p.prediction for p in predictions)

            return {
                "success": True,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": len(predictions),
                },
                "forecast": {
                    "total_demand": total_demand,
                    "daily_average": total_demand / len(predictions),
                    "peak_demand": peak_demand,
                    "avg_confidence": avg_confidence,
                },
                "daily_predictions": [
                    {
                        "date": (start_date + timedelta(days=i)).isoformat(),
                        "demand": p.prediction,
                        "confidence": p.confidence,
                    }
                    for i, p in enumerate(predictions)
                ],
                "key_factors": predictions[0].factors if predictions else {},
                "model_info": {
                    "version": predictions[0].model_version if predictions else "v1.0",
                    "last_updated": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Error generating demand forecast: {e}")
            return {"error": str(e)}

    async def get_user_insights(self, user_id: str) -> dict[str, Any]:
        """사용자 예측 분석"""
        try:
            churn_prediction = self.user_predictor.predict_churn_probability(user_id)
            ltv_prediction = self.user_predictor.predict_lifetime_value(user_id)

            return {
                "success": True,
                "user_id": user_id,
                "churn_analysis": {
                    "probability": churn_prediction.prediction,
                    "risk_level": self._get_churn_risk_level(
                        churn_prediction.prediction
                    ),
                    "confidence": churn_prediction.confidence,
                    "factors": churn_prediction.factors,
                },
                "lifetime_value": {
                    "predicted_ltv": ltv_prediction.prediction,
                    "confidence": ltv_prediction.confidence,
                    "value_category": self._get_ltv_category(ltv_prediction.prediction),
                },
                "recommendations": self._generate_user_recommendations(
                    churn_prediction, ltv_prediction
                ),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating user insights: {e}")
            return {"error": str(e)}

    async def get_destination_forecast(
        self, destination_id: str, days_ahead: int = 30
    ) -> dict[str, Any]:
        """목적지 인기도 예측"""
        try:
            predictions = self.destination_predictor.predict_popularity_trend(
                destination_id, days_ahead
            )

            if not predictions:
                return {"error": "No predictions available"}

            # 트렌드 분석
            trend_direction = "stable"
            if len(predictions) > 1:
                start_popularity = predictions[0].prediction
                end_popularity = predictions[-1].prediction
                change_rate = (end_popularity - start_popularity) / start_popularity

                if change_rate > 0.1:
                    trend_direction = "increasing"
                elif change_rate < -0.1:
                    trend_direction = "decreasing"

            return {
                "success": True,
                "destination_id": destination_id,
                "forecast_period": f"{days_ahead} days",
                "trend_analysis": {
                    "direction": trend_direction,
                    "current_popularity": predictions[0].prediction,
                    "predicted_popularity": predictions[-1].prediction,
                    "avg_confidence": sum(p.confidence for p in predictions)
                    / len(predictions),
                },
                "daily_predictions": [
                    {
                        "day": i + 1,
                        "popularity": p.prediction,
                        "confidence": p.confidence,
                    }
                    for i, p in enumerate(predictions)
                ],
                "key_factors": predictions[0].factors if predictions else {},
                "recommendations": self._generate_destination_recommendations(
                    predictions
                ),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating destination forecast: {e}")
            return {"error": str(e)}

    def _get_churn_risk_level(self, probability: float) -> str:
        """이탈 위험 수준 분류"""
        if probability < 0.3:
            return "low"
        elif probability < 0.7:
            return "medium"
        else:
            return "high"

    def _get_ltv_category(self, ltv: float) -> str:
        """LTV 카테고리 분류"""
        if ltv < 50000:
            return "low"
        elif ltv < 200000:
            return "medium"
        else:
            return "high"

    def _generate_user_recommendations(
        self, churn_prediction: PredictionResult, ltv_prediction: PredictionResult
    ) -> list[str]:
        """사용자 추천 사항 생성"""
        recommendations = []

        if churn_prediction.prediction > 0.7:
            recommendations.append("높은 이탈 위험 - 개인화된 혜택 제공 필요")
            recommendations.append("맞춤형 여행 추천 강화")

        if ltv_prediction.prediction > 100000:
            recommendations.append("고가치 고객 - VIP 서비스 제공 고려")

        if churn_prediction.factors.get("days_since_last_login", 0) > 30:
            recommendations.append("장기 미접속 - 재참여 캠페인 필요")

        return recommendations

    def _generate_destination_recommendations(
        self, predictions: list[PredictionResult]
    ) -> list[str]:
        """목적지 추천 사항 생성"""
        recommendations = []

        if predictions:
            trend = predictions[-1].prediction - predictions[0].prediction

            if trend > 0:
                recommendations.append("인기 상승 예상 - 마케팅 강화 시점")
            elif trend < 0:
                recommendations.append("인기 하락 예상 - 프로모션 필요")

            avg_confidence = sum(p.confidence for p in predictions) / len(predictions)
            if avg_confidence < 0.5:
                recommendations.append("예측 신뢰도 낮음 - 추가 데이터 수집 필요")

        return recommendations


# 예측 분석 엔진 싱글톤
predictive_engine = None


def get_predictive_engine(db) -> PredictiveAnalyticsEngine:
    """예측 분석 엔진 인스턴스 반환"""
    global predictive_engine
    if predictive_engine is None:
        predictive_engine = PredictiveAnalyticsEngine(db)
    return predictive_engine


logger.info("Predictive analytics engine initialized")
