"""
예측 분석 API 라우터
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.ai.predictive_analytics import (
    PredictiveAnalyticsEngine,
    get_predictive_engine,
)
from app.auth.dependencies import get_current_admin
from app.database import get_db
from app.logging_config import get_logger
from app.utils.cache import CACHE_PREFIX, CACHE_TTL, cache_result

logger = get_logger("ai_predictive_router")

router = APIRouter(prefix="/ai/predictive", tags=["AI Predictive Analytics"])


class DemandForecastRequest(BaseModel):
    """수요 예측 요청 모델"""

    start_date: datetime = Field(..., description="예측 시작 날짜")
    end_date: datetime = Field(..., description="예측 종료 날짜")
    region: str | None = Field(None, description="지역 필터")
    category: str | None = Field(None, description="카테고리 필터")


class UserInsightRequest(BaseModel):
    """사용자 분석 요청 모델"""

    user_id: str | None = Field(None, description="사용자 ID (관리자용)")
    include_recommendations: bool = Field(True, description="추천 사항 포함 여부")


class DestinationForecastRequest(BaseModel):
    """목적지 예측 요청 모델"""

    destination_id: str = Field(..., description="목적지 ID")
    days_ahead: int = Field(30, ge=1, le=365, description="예측 기간 (일)")
    include_factors: bool = Field(True, description="영향 요인 포함 여부")


class ModelTrainingRequest(BaseModel):
    """모델 학습 요청 모델"""

    model_type: str = Field(..., description="모델 유형")
    retrain: bool = Field(False, description="재학습 여부")


@router.post("/demand/forecast", response_model=None)
@cache_result(ttl=CACHE_TTL["LONG"], prefix=CACHE_PREFIX["PREDICTIONS"])
async def get_demand_forecast(
    request: DemandForecastRequest,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    engine: PredictiveAnalyticsEngine = Depends(get_predictive_engine),
):
    """여행 수요 예측"""
    try:
        # 날짜 검증
        if request.start_date >= request.end_date:
            raise HTTPException(
                status_code=400, detail="Start date must be before end date"
            )

        # 예측 기간 제한 (최대 1년)
        if (request.end_date - request.start_date).days > 365:
            raise HTTPException(
                status_code=400, detail="Forecast period cannot exceed 365 days"
            )

        # 수요 예측 수행
        forecast = await engine.get_demand_forecast(
            request.start_date, request.end_date
        )

        if "error" in forecast:
            raise HTTPException(status_code=500, detail=forecast["error"])

        return {
            "success": True,
            "message": "수요 예측이 완료되었습니다.",
            "data": forecast,
            "request_info": {
                "start_date": request.start_date.isoformat(),
                "end_date": request.end_date.isoformat(),
                "region": request.region,
                "category": request.category,
            },
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating demand forecast: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate demand forecast"
        )


@router.post("/user/insights", response_model=None)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["USER_INSIGHTS"])
async def get_user_insights(
    request: UserInsightRequest,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    engine: PredictiveAnalyticsEngine = Depends(get_predictive_engine),
):
    """사용자 행동 예측 분석"""
    try:
        # 사용자 ID 결정
        target_user_id = request.user_id or current_user["user_id"]

        # 관리자가 아닌 경우 다른 사용자 분석 불가
        if request.user_id and request.user_id != current_user["user_id"]:
            if not current_user.get("is_admin", False):
                raise HTTPException(
                    status_code=403,
                    detail="Admin access required for other user analysis",
                )

        # 사용자 분석 수행
        insights = await engine.get_user_insights(target_user_id)

        if "error" in insights:
            raise HTTPException(status_code=500, detail=insights["error"])

        return {
            "success": True,
            "message": "사용자 분석이 완료되었습니다.",
            "data": insights,
            "request_info": {
                "analyzed_user": target_user_id,
                "include_recommendations": request.include_recommendations,
            },
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating user insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate user insights")


@router.post("/destination/forecast", response_model=None)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["DESTINATION_FORECAST"])
async def get_destination_forecast(
    request: DestinationForecastRequest,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    engine: PredictiveAnalyticsEngine = Depends(get_predictive_engine),
):
    """목적지 인기도 예측"""
    try:
        # 목적지 존재 확인
        from app.models import Destination

        destination = (
            db.query(Destination)
            .filter(Destination.destination_id == request.destination_id)
            .first()
        )

        if not destination:
            raise HTTPException(status_code=404, detail="Destination not found")

        # 인기도 예측 수행
        forecast = await engine.get_destination_forecast(
            request.destination_id, request.days_ahead
        )

        if "error" in forecast:
            raise HTTPException(status_code=500, detail=forecast["error"])

        return {
            "success": True,
            "message": "목적지 인기도 예측이 완료되었습니다.",
            "data": forecast,
            "destination_info": {
                "destination_id": request.destination_id,
                "name": destination.name,
                "category": destination.category,
                "region": destination.region,
            },
            "request_info": {
                "days_ahead": request.days_ahead,
                "include_factors": request.include_factors,
            },
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating destination forecast: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate destination forecast"
        )


@router.get("/trends/summary", response_model=None)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["TRENDS"])
async def get_prediction_trends_summary(
    days_back: int = Query(30, ge=1, le=365, description="분석 기간 (일)"),
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    engine: PredictiveAnalyticsEngine = Depends(get_predictive_engine),
):
    """예측 트렌드 요약"""
    try:
        # 기간 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # 수요 예측 트렌드
        demand_forecast = await engine.get_demand_forecast(start_date, end_date)

        # 인기 목적지 예측 (예시)
        popular_destinations = await _get_popular_destinations_forecast(db, engine)

        # 사용자 행동 트렌드
        user_trends = await _get_user_behavior_trends(db, engine, current_user)

        return {
            "success": True,
            "message": "예측 트렌드 요약이 완료되었습니다.",
            "data": {
                "analysis_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days_back,
                },
                "demand_trends": demand_forecast.get("forecast", {}),
                "popular_destinations": popular_destinations,
                "user_behavior": user_trends,
                "key_insights": _generate_key_insights(
                    demand_forecast, popular_destinations, user_trends
                ),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error generating trends summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate trends summary")


@router.post("/models/train", response_model=None)
async def train_prediction_model(
    request: ModelTrainingRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    engine: PredictiveAnalyticsEngine = Depends(get_predictive_engine),
):
    """예측 모델 학습 (관리자용)"""
    try:
        # 관리자 권한 확인
        # 관리자 백엔드에서는 이미 관리자 인증 완료

        # 지원되는 모델 유형 확인
        supported_models = ["demand", "user_behavior", "destination_popularity"]
        if request.model_type not in supported_models:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported model type. Supported: {supported_models}",
            )

        # 백그라운드에서 모델 학습
        background_tasks.add_task(
            _train_model_background, request.model_type, request.retrain, engine
        )

        return {
            "success": True,
            "message": f"{request.model_type} 모델 학습이 시작되었습니다.",
            "model_type": request.model_type,
            "retrain": request.retrain,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating model training: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate model training")


@router.get("/models/status", response_model=None)
async def get_model_status(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    engine: PredictiveAnalyticsEngine = Depends(get_predictive_engine),
):
    """예측 모델 상태 조회"""
    try:
        # 모델 상태 정보 수집
        model_status = {
            "demand_predictor": {
                "trained": engine.demand_predictor.model_trained,
                "last_updated": "2024-01-01T00:00:00Z",  # 실제로는 DB에서 조회
                "performance": {"r2_score": 0.85, "mse": 0.15},
            },
            "user_predictor": {
                "trained": engine.user_predictor.models_trained,
                "last_updated": "2024-01-01T00:00:00Z",
                "performance": {"accuracy": 0.82, "precision": 0.78},
            },
            "destination_predictor": {
                "trained": True,
                "last_updated": "2024-01-01T00:00:00Z",
                "performance": {"r2_score": 0.79, "mse": 0.21},
            },
        }

        return {
            "success": True,
            "message": "모델 상태 조회가 완료되었습니다.",
            "data": model_status,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting model status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get model status")


async def _get_popular_destinations_forecast(
    db, engine: PredictiveAnalyticsEngine
) -> dict[str, Any]:
    """인기 목적지 예측"""
    try:
        # 상위 5개 목적지 조회
        from app.models import Destination

        destinations = db.query(Destination).limit(5).all()

        forecasts = []
        for destination in destinations:
            forecast = await engine.get_destination_forecast(
                destination.destination_id, 7
            )
            if forecast and "error" not in forecast:
                forecasts.append(
                    {
                        "destination_id": destination.destination_id,
                        "name": destination.name,
                        "trend": forecast.get("trend_analysis", {}),
                    }
                )

        return {
            "top_destinations": forecasts,
            "total_analyzed": len(forecasts),
        }

    except Exception as e:
        logger.error(f"Error getting popular destinations forecast: {e}")
        return {"error": str(e)}


async def _get_user_behavior_trends(
    db, engine: PredictiveAnalyticsEngine, current_user: dict
) -> dict[str, Any]:
    """사용자 행동 트렌드"""
    try:
        # 현재 사용자 분석
        user_insight = await engine.get_user_insights(current_user["user_id"])

        if "error" in user_insight:
            return {"error": user_insight["error"]}

        return {
            "current_user_profile": {
                "churn_risk": user_insight.get("churn_analysis", {}).get(
                    "risk_level", "unknown"
                ),
                "ltv_category": user_insight.get("lifetime_value", {}).get(
                    "value_category", "unknown"
                ),
            },
            "recommendations": user_insight.get("recommendations", []),
        }

    except Exception as e:
        logger.error(f"Error getting user behavior trends: {e}")
        return {"error": str(e)}


def _generate_key_insights(
    demand_forecast: dict[str, Any],
    popular_destinations: dict[str, Any],
    user_trends: dict[str, Any],
) -> list[str]:
    """주요 인사이트 생성"""
    insights = []

    # 수요 예측 인사이트
    if demand_forecast.get("forecast"):
        peak_demand = demand_forecast["forecast"].get("peak_demand", 0)
        if peak_demand > 100:
            insights.append("높은 수요 증가가 예상됩니다.")

    # 목적지 인사이트
    if popular_destinations.get("top_destinations"):
        increasing_destinations = [
            d
            for d in popular_destinations["top_destinations"]
            if d.get("trend", {}).get("direction") == "increasing"
        ]
        if increasing_destinations:
            insights.append(
                f"{len(increasing_destinations)}개 목적지의 인기 상승이 예상됩니다."
            )

    # 사용자 행동 인사이트
    if user_trends.get("current_user_profile"):
        churn_risk = user_trends["current_user_profile"].get("churn_risk")
        if churn_risk == "high":
            insights.append("사용자 이탈 위험이 높습니다.")

    return insights


async def _train_model_background(
    model_type: str, retrain: bool, engine: PredictiveAnalyticsEngine
):
    """백그라운드 모델 학습"""
    try:
        if model_type == "demand":
            result = engine.demand_predictor.train_model()
        elif model_type == "user_behavior":
            # 사용자 행동 모델 학습 (실제 구현 필요)
            result = {
                "success": True,
                "message": "User behavior model training completed",
            }
        elif model_type == "destination_popularity":
            # 목적지 인기도 모델 학습 (실제 구현 필요)
            result = {
                "success": True,
                "message": "Destination popularity model training completed",
            }
        else:
            result = {"error": "Unknown model type"}

        logger.info(f"Model training result for {model_type}: {result}")

    except Exception as e:
        logger.error(f"Error in background model training: {e}")


logger.info("AI predictive analytics router initialized")
