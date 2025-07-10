"""
실시간 여행 트렌드 분석 API 라우터
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.ai.trend_analysis import TrendAnalyzer, TrendPredictor
from app.auth.dependencies import get_current_admin
from app.database import get_db
from app.logging_config import get_logger
from app.utils.cache import CACHE_PREFIX, CACHE_TTL, cache_result

logger = get_logger("ai_trends")

router = APIRouter(prefix="/ai/trends", tags=["AI Trend Analysis"])


class TrendAnalysisRequest(BaseModel):
    """트렌드 분석 요청 모델"""

    time_window: int = Field(7, ge=1, le=90, description="분석 기간 (일)")
    trend_types: list[str] = Field(
        default=["destinations", "bookings", "reviews"],
        description="분석할 트렌드 유형",
    )
    include_predictions: bool = Field(True, description="예측 포함 여부")


class TrendPredictionRequest(BaseModel):
    """트렌드 예측 요청 모델"""

    prediction_days: int = Field(30, ge=1, le=365, description="예측 기간 (일)")
    prediction_types: list[str] = Field(
        default=["demand", "destinations", "pricing"], description="예측할 트렌드 유형"
    )


@router.get("/realtime", response_model=None)
@cache_result(ttl=CACHE_TTL["SHORT"], prefix=CACHE_PREFIX["TRENDS"])
async def get_realtime_trends(
    time_window: int = Query(7, ge=1, le=90, description="분석 기간 (일)"),
    db=Depends(get_db),
):
    """실시간 트렌드 분석"""
    try:
        analyzer = TrendAnalyzer(db)
        trend_analysis = await analyzer.analyze_realtime_trends(time_window)

        return {
            "success": True,
            "time_window_days": time_window,
            "trends": trend_analysis,
            "analyzed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting realtime trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get realtime trends")


@router.post("/analyze", response_model=None)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["TRENDS"])
async def analyze_trends(
    request: TrendAnalysisRequest,
    db=Depends(get_db),
):
    """맞춤형 트렌드 분석"""
    try:
        analyzer = TrendAnalyzer(db)
        # 전체 트렌드 분석 실행
        full_analysis = await analyzer.analyze_realtime_trends(request.time_window)

        # 요청된 트렌드 유형만 필터링
        filtered_analysis = {}
        for trend_type in request.trend_types:
            if f"{trend_type}_trends" in full_analysis:
                filtered_analysis[f"{trend_type}_trends"] = full_analysis[
                    f"{trend_type}_trends"
                ]

        # 예측 포함
        predictions = {}
        if request.include_predictions:
            predictor = TrendPredictor(db)
            predictions = await predictor.predict_future_trends(30)

        return {
            "success": True,
            "analysis_request": request.dict(),
            "trend_analysis": filtered_analysis,
            "predictions": predictions if request.include_predictions else None,
            "analyzed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error analyzing trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze trends")


@router.get("/destinations", response_model=None)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["TRENDS"])
async def get_destination_trends(
    time_window: int = Query(7, ge=1, le=90, description="분석 기간"),
    limit: int = Query(20, ge=5, le=100, description="결과 개수"),
    db=Depends(get_db),
):
    """목적지 트렌드"""
    try:
        analyzer = TrendAnalyzer(db)
        destination_trends = await analyzer._analyze_destination_trends(time_window)

        # 상위 N개만 반환
        if destination_trends.get("trending_destinations"):
            destination_trends["trending_destinations"] = destination_trends[
                "trending_destinations"
            ][:limit]

        return {
            "success": True,
            "time_window_days": time_window,
            "destination_trends": destination_trends,
            "analyzed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting destination trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get destination trends")


@router.get("/search-trends", response_model=None)
@cache_result(ttl=CACHE_TTL["SHORT"], prefix=CACHE_PREFIX["TRENDS"])
async def get_search_trends(
    time_window: int = Query(7, ge=1, le=90, description="분석 기간"),
    category: str | None = Query(None, description="검색 카테고리"),
    db=Depends(get_db),
):
    """검색 트렌드"""
    try:
        analyzer = TrendAnalyzer(db)
        search_trends = await analyzer._analyze_search_trends(time_window)

        # 카테고리별 필터링
        if category and search_trends.get("search_categories"):
            if category in search_trends["search_categories"]:
                search_trends["filtered_keywords"] = search_trends["search_categories"][
                    category
                ]

        return {
            "success": True,
            "time_window_days": time_window,
            "category_filter": category,
            "search_trends": search_trends,
            "analyzed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting search trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get search trends")


@router.get("/booking-trends", response_model=None)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["TRENDS"])
async def get_booking_trends(
    time_window: int = Query(7, ge=1, le=90, description="분석 기간"),
    db=Depends(get_db),
):
    """예약 트렌드"""
    try:
        analyzer = TrendAnalyzer(db)
        booking_trends = await analyzer._analyze_booking_trends(time_window)

        return {
            "success": True,
            "time_window_days": time_window,
            "booking_trends": booking_trends,
            "analyzed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting booking trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get booking trends")


@router.get("/seasonal", response_model=None)
@cache_result(ttl=CACHE_TTL["LONG"], prefix=CACHE_PREFIX["TRENDS"])
async def get_seasonal_trends(db=Depends(get_db)):
    """계절별 트렌드"""
    try:
        analyzer = TrendAnalyzer(db)
        seasonal_trends = await analyzer._analyze_seasonal_trends()

        return {
            "success": True,
            "seasonal_trends": seasonal_trends,
            "analyzed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting seasonal trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get seasonal trends")


@router.get("/demographic", response_model=None)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["TRENDS"])
async def get_demographic_trends(
    time_window: int = Query(7, ge=1, le=90, description="분석 기간"),
    db=Depends(get_db),
):
    """인구통계학적 트렌드"""
    try:
        analyzer = TrendAnalyzer(db)
        demographic_trends = await analyzer._analyze_demographic_trends(time_window)

        return {
            "success": True,
            "time_window_days": time_window,
            "demographic_trends": demographic_trends,
            "analyzed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting demographic trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get demographic trends")


@router.post("/predictions", response_model=None)
@cache_result(ttl=CACHE_TTL["LONG"], prefix=CACHE_PREFIX["PREDICTIONS"])
async def predict_trends(
    request: TrendPredictionRequest,
    db=Depends(get_db),
):
    """트렌드 예측"""
    try:
        predictor = TrendPredictor(db)
        predictions = await predictor.predict_future_trends(request.prediction_days)

        # 요청된 예측 유형만 필터링
        filtered_predictions = {}
        for pred_type in request.prediction_types:
            key = f"{pred_type}_predictions"
            if key in predictions:
                filtered_predictions[key] = predictions[key]

        return {
            "success": True,
            "prediction_request": request.dict(),
            "predictions": filtered_predictions,
            "full_predictions": predictions,
            "predicted_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error predicting trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to predict trends")


@router.get("/insights", response_model=None)
async def get_trend_insights(
    time_window: int = Query(7, ge=1, le=90, description="분석 기간"),
    db=Depends(get_db),
):
    """트렌드 인사이트"""
    try:
        analyzer = TrendAnalyzer(db)
        # 전체 트렌드 분석
        trend_analysis = await analyzer.analyze_realtime_trends(time_window)

        # 인사이트 생성
        insights = _generate_trend_insights(trend_analysis)

        return {
            "success": True,
            "time_window_days": time_window,
            "insights": insights,
            "trend_summary": trend_analysis.get("trend_summary", {}),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting trend insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trend insights")


@router.get("/alerts", response_model=None)
async def get_trend_alerts(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """트렌드 알림"""
    try:
        # 관리자만 접근 가능
        if not current_user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Admin access required")

        analyzer = TrendAnalyzer(db)
        # 최근 트렌드 분석
        recent_trends = await analyzer.analyze_realtime_trends(1)  # 1일 데이터

        # 알림 생성
        alerts = _generate_trend_alerts(recent_trends)

        return {
            "success": True,
            "alerts": alerts,
            "alert_count": len(alerts),
            "generated_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trend alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trend alerts")


@router.post("/refresh-cache", response_model=None)
async def refresh_trend_cache(
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """트렌드 캐시 갱신 (관리자 전용)"""
    try:
        # 관리자만 접근 가능
        if not current_user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Admin access required")

        analyzer = TrendAnalyzer(db)
        # 백그라운드에서 캐시 갱신
        background_tasks.add_task(_refresh_trend_cache_background, analyzer)

        return {
            "success": True,
            "message": "Trend cache refresh initiated",
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing trend cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh trend cache")


@router.get("/export", response_model=None)
async def export_trend_data(
    time_window: int = Query(7, ge=1, le=90, description="분석 기간"),
    format: str = Query("json", regex="^(json|csv)$", description="내보내기 형식"),
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """트렌드 데이터 내보내기 (관리자 전용)"""
    try:
        # 관리자만 접근 가능
        if not current_user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Admin access required")

        analyzer = TrendAnalyzer(db)
        # 트렌드 데이터 수집
        trend_data = await analyzer.analyze_realtime_trends(time_window)

        # 형식에 따른 처리
        if format == "csv":
            # CSV 형식으로 변환 (실제 구현에서는 pandas 사용)
            exported_data = _convert_to_csv(trend_data)
            media_type = "text/csv"
            filename = f"trend_data_{datetime.now().strftime('%Y%m%d')}.csv"
        else:
            exported_data = trend_data
            media_type = "application/json"
            filename = f"trend_data_{datetime.now().strftime('%Y%m%d')}.json"

        return {
            "success": True,
            "export_format": format,
            "filename": filename,
            "data": exported_data,
            "exported_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting trend data: {e}")
        raise HTTPException(status_code=500, detail="Failed to export trend data")


def _generate_trend_insights(trend_analysis: dict[str, Any]) -> list[dict[str, str]]:
    """트렌드 인사이트 생성"""
    insights = []

    # 목적지 트렌드 인사이트
    dest_trends = trend_analysis.get("destination_trends", {})
    if dest_trends.get("trending_destinations"):
        top_dest = dest_trends["trending_destinations"][0]
        insights.append(
            {
                "type": "destination_popularity",
                "title": "인기 급상승 목적지",
                "description": "가장 인기있는 목적지입니다.",
                "importance": "high",
            }
        )

    # 예약 트렌드 인사이트
    booking_trends = trend_analysis.get("booking_trends", {})
    total_bookings = booking_trends.get("total_bookings", 0)
    if total_bookings > 100:
        insights.append(
            {
                "type": "booking_volume",
                "title": "예약 활동 증가",
                "description": f"최근 {total_bookings}건의 활발한 예약 활동이 있었습니다.",
                "importance": "medium",
            }
        )

    # 리뷰 트렌드 인사이트
    review_trends = trend_analysis.get("review_trends", {})
    satisfaction_metrics = review_trends.get("satisfaction_metrics", {})
    satisfaction_rate = satisfaction_metrics.get("satisfaction_rate", 0)

    if satisfaction_rate > 0.8:
        insights.append(
            {
                "type": "satisfaction",
                "title": "높은 만족도",
                "description": f"사용자 만족도가 {satisfaction_rate:.1%}로 높습니다.",
                "importance": "high",
            }
        )

    return insights


def _generate_trend_alerts(trend_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """트렌드 알림 생성"""
    alerts = []

    # 급격한 변화 감지
    booking_trends = trend_analysis.get("booking_trends", {})
    total_bookings = booking_trends.get("total_bookings", 0)

    if total_bookings > 200:
        alerts.append(
            {
                "type": "spike",
                "severity": "high",
                "title": "예약 급증 감지",
                "description": "예약량이 평소보다 크게 증가했습니다.",
                "action_required": True,
            }
        )
    elif total_bookings < 10:
        alerts.append(
            {
                "type": "drop",
                "severity": "medium",
                "title": "예약 감소 감지",
                "description": "예약량이 평소보다 감소했습니다.",
                "action_required": True,
            }
        )

    # 리뷰 트렌드 알림
    review_trends = trend_analysis.get("review_trends", {})
    satisfaction_metrics = review_trends.get("satisfaction_metrics", {})
    satisfaction_rate = satisfaction_metrics.get("satisfaction_rate", 1.0)

    if satisfaction_rate < 0.6:
        alerts.append(
            {
                "type": "satisfaction_drop",
                "severity": "high",
                "title": "만족도 하락 경고",
                "description": "사용자 만족도가 크게 하락했습니다.",
                "action_required": True,
            }
        )

    return alerts


async def _refresh_trend_cache_background(analyzer):
    """백그라운드에서 트렌드 캐시 갱신"""
    try:
        # 다양한 시간 윈도우로 트렌드 분석 실행
        time_windows = [1, 7, 30]
        for window in time_windows:
            await analyzer.analyze_realtime_trends(window)

        logger.info("Trend cache refreshed successfully")

    except Exception as e:
        logger.error(f"Error refreshing trend cache in background: {e}")


def _convert_to_csv(data: dict[str, Any]) -> str:
    """JSON 데이터를 CSV로 변환"""
    # 실제 구현에서는 pandas를 사용하여 변환
    return "timestamp,metric,value\n2024-01-01,bookings,100\n"


logger.info("AI trends router initialized")
