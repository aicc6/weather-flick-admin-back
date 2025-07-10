"""
사용자 행동 분석 API 라우터
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.ai.behavior_analysis import PersonalizationEngine, UserBehaviorAnalyzer
from app.auth.dependencies import get_current_admin
from app.database import get_db
from app.logging_config import get_logger
from app.utils.cache import CACHE_PREFIX, CACHE_TTL, cache_result

logger = get_logger("ai_behavior")

router = APIRouter(prefix="/ai/behavior", tags=["AI Behavior Analysis"])


class BehaviorAnalysisRequest(BaseModel):
    """행동 분석 요청 모델"""

    analysis_type: str = Field(
        ..., description="분석 유형: full, travel_patterns, preferences, engagement"
    )
    time_range: int | None = Field(None, ge=1, le=365, description="분석 기간 (일)")
    include_predictions: bool = Field(True, description="예측 정보 포함 여부")


class PersonalizationRequest(BaseModel):
    """개인화 요청 모델"""

    content_types: list[str] = Field(
        default=["recommendations", "offers"], description="요청할 콘텐츠 유형"
    )
    preferences: dict[str, Any] | None = Field(None, description="추가 선호도 정보")


@router.post("/analyze", response_model=None)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["ANALYTICS"])
async def analyze_user_behavior(
    request: BehaviorAnalysisRequest,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """사용자 행동 종합 분석"""
    try:
        admin_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        # 분석기 인스턴스 생성
        analyzer = UserBehaviorAnalyzer(db)

        # 분석 유형에 따른 처리
        if request.analysis_type == "full":
            analysis_result = analyzer.analyze_user_behavior(user_id)
        elif request.analysis_type == "travel_patterns":
            analysis_result = {
                "travel_patterns": analyzer._analyze_travel_patterns(user_id)
            }
        elif request.analysis_type == "preferences":
            analysis_result = {
                "preference_evolution": analyzer._analyze_preference_evolution(user_id)
            }
        elif request.analysis_type == "engagement":
            analysis_result = {
                "engagement_metrics": analyzer._analyze_engagement_metrics(user_id)
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid analysis type")

        # 예측 정보 추가
        if request.include_predictions:
            prediction_scores = analyzer._calculate_prediction_scores(user_id)
            analysis_result["predictions"] = prediction_scores

        return {
            "user_id": user_id,
            "analysis_type": request.analysis_type,
            "time_range_days": request.time_range,
            "results": analysis_result,
            "analyzed_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing user behavior: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze user behavior")


@router.get("/travel-patterns", response_model=None)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["ANALYTICS"])
async def get_travel_patterns(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """여행 패턴 분석"""
    try:
        admin_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        analyzer = UserBehaviorAnalyzer(db)
        travel_patterns = analyzer._analyze_travel_patterns(user_id)

        return {
            "user_id": user_id,
            "travel_patterns": travel_patterns,
            "analyzed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting travel patterns: {e}")
        raise HTTPException(status_code=500, detail="Failed to get travel patterns")


@router.get("/seasonal-behavior", response_model=None)
@cache_result(ttl=CACHE_TTL["LONG"], prefix=CACHE_PREFIX["ANALYTICS"])
async def get_seasonal_behavior(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """계절별 행동 패턴"""
    try:
        admin_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        analyzer = UserBehaviorAnalyzer(db)
        seasonal_behavior = analyzer._analyze_seasonal_behavior(user_id)

        return {
            "user_id": user_id,
            "seasonal_behavior": seasonal_behavior,
            "analyzed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting seasonal behavior: {e}")
        raise HTTPException(status_code=500, detail="Failed to get seasonal behavior")


@router.get("/engagement-metrics", response_model=None)
@cache_result(ttl=CACHE_TTL["SHORT"], prefix=CACHE_PREFIX["ANALYTICS"])
async def get_engagement_metrics(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """참여도 지표"""
    try:
        admin_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        analyzer = UserBehaviorAnalyzer(db)
        engagement_metrics = analyzer._analyze_engagement_metrics(user_id)

        return {
            "user_id": user_id,
            "engagement_metrics": engagement_metrics,
            "analyzed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting engagement metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get engagement metrics")


@router.get("/decision-patterns", response_model=None)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["ANALYTICS"])
async def get_decision_patterns(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """의사결정 패턴"""
    try:
        admin_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        analyzer = UserBehaviorAnalyzer(db)
        decision_patterns = analyzer._analyze_decision_patterns(user_id)

        return {
            "user_id": user_id,
            "decision_patterns": decision_patterns,
            "analyzed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting decision patterns: {e}")
        raise HTTPException(status_code=500, detail="Failed to get decision patterns")


@router.get("/predictions", response_model=None)
@cache_result(ttl=CACHE_TTL["SHORT"], prefix=CACHE_PREFIX["ANALYTICS"])
async def get_prediction_scores(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """예측 점수"""
    try:
        admin_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        analyzer = UserBehaviorAnalyzer(db)
        prediction_scores = analyzer._calculate_prediction_scores(user_id)

        return {
            "user_id": user_id,
            "prediction_scores": prediction_scores,
            "analyzed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting prediction scores: {e}")
        raise HTTPException(status_code=500, detail="Failed to get prediction scores")


@router.post("/personalize", response_model=None)
@cache_result(ttl=CACHE_TTL["SHORT"], prefix=CACHE_PREFIX["RECOMMENDATIONS"])
async def generate_personalized_content(
    request: PersonalizationRequest,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """개인화된 콘텐츠 생성"""
    try:
        admin_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        engine = PersonalizationEngine(db)
        personalized_content = engine.generate_personalized_recommendations(user_id)

        # 요청된 콘텐츠 유형만 필터링
        filtered_content = {}
        for content_type in request.content_types:
            if content_type in personalized_content.get("personalized_content", {}):
                filtered_content[content_type] = personalized_content[
                    "personalized_content"
                ][content_type]

        return {
            "user_id": user_id,
            "requested_content_types": request.content_types,
            "personalized_content": filtered_content,
            "personalization_strategy": personalized_content.get(
                "personalization_strategy", {}
            ),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error generating personalized content: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate personalized content"
        )


@router.get("/activity-timeline", response_model=None)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["ANALYTICS"])
async def get_activity_timeline(
    limit: int = Query(50, ge=1, le=200, description="활동 개수"),
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """활동 타임라인"""
    try:
        admin_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        analyzer = UserBehaviorAnalyzer(db)
        activity_timeline = analyzer._analyze_activity_timeline(user_id)

        # 제한된 개수만 반환
        if activity_timeline.get("activity_timeline"):
            activity_timeline["activity_timeline"] = activity_timeline[
                "activity_timeline"
            ][-limit:]

        return {
            "user_id": user_id,
            "activity_timeline": activity_timeline,
            "limit": limit,
            "analyzed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting activity timeline: {e}")
        raise HTTPException(status_code=500, detail="Failed to get activity timeline")


@router.get("/insights", response_model=None)
async def get_behavior_insights(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """행동 인사이트 요약"""
    try:
        admin_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        # 주요 인사이트 수집
        analyzer = UserBehaviorAnalyzer(db)
        behavior_analysis = analyzer.analyze_user_behavior(user_id)

        # 인사이트 요약 생성
        insights = _generate_insights_summary(behavior_analysis)

        return {
            "user_id": user_id,
            "insights": insights,
            "confidence_score": _calculate_insights_confidence(behavior_analysis),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting behavior insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to get behavior insights")


@router.get("/compare-users", response_model=None)
async def compare_user_behaviors(
    target_user_id: str = Query(..., description="비교할 사용자 ID"),
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """사용자 행동 비교 (관리자 전용)"""
    try:
        # 관리자 백엔드에서는 이미 관리자 인증이 완료된 상태
        admin_id = current_admin.admin_id

        # 두 사용자의 행동 분석
        analyzer = UserBehaviorAnalyzer(db)
        user1_analysis = analyzer.analyze_user_behavior(user_id1)
        user2_analysis = analyzer.analyze_user_behavior(target_user_id)

        # 비교 결과 생성
        comparison = _compare_user_behaviors(user1_analysis, user2_analysis)

        return {
            "user_id1": user_id1,
            "target_user_id": target_user_id,
            "comparison": comparison,
            "analyzed_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing user behaviors: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare user behaviors")


def _generate_insights_summary(
    behavior_analysis: dict[str, Any],
) -> list[dict[str, str]]:
    """인사이트 요약 생성"""
    insights = []

    # 여행 패턴 인사이트
    travel_patterns = behavior_analysis.get("travel_patterns", {})
    if travel_patterns.get("total_trips", 0) > 0:
        insights.append(
            {
                "type": "travel_frequency",
                "title": "여행 빈도",
                "description": f"총 {travel_patterns['total_trips']}회의 여행을 계획했습니다.",
                "importance": "medium",
            }
        )

    # 계절 선호도 인사이트
    seasonal_behavior = behavior_analysis.get("seasonal_behavior", {})
    peak_season = seasonal_behavior.get("peak_travel_season")
    if peak_season:
        season_names = {
            "spring": "봄",
            "summer": "여름",
            "fall": "가을",
            "winter": "겨울",
        }
        insights.append(
            {
                "type": "seasonal_preference",
                "title": "선호 계절",
                "description": f"{season_names.get(peak_season, peak_season)} 여행을 선호합니다.",
                "importance": "high",
            }
        )

    # 의사결정 스타일 인사이트
    decision_patterns = behavior_analysis.get("decision_patterns", {})
    decision_style = decision_patterns.get("decision_style")
    if decision_style:
        style_descriptions = {
            "spontaneous": "즉흥적인 여행을 선호하는 스타일입니다.",
            "moderate_planner": "적당한 계획을 세우는 스타일입니다.",
            "advance_planner": "미리 계획을 세우는 스타일입니다.",
            "long_term_planner": "장기간 미리 계획하는 스타일입니다.",
        }
        insights.append(
            {
                "type": "decision_style",
                "title": "계획 스타일",
                "description": style_descriptions.get(
                    decision_style, "특별한 패턴이 없습니다."
                ),
                "importance": "medium",
            }
        )

    return insights


def _calculate_insights_confidence(behavior_analysis: dict[str, Any]) -> float:
    """인사이트 신뢰도 계산"""
    confidence_factors = []

    # 데이터 충분성
    travel_patterns = behavior_analysis.get("travel_patterns", {})
    total_trips = travel_patterns.get("total_trips", 0)
    if total_trips >= 5:
        confidence_factors.append(0.3)
    elif total_trips >= 2:
        confidence_factors.append(0.2)

    # 리뷰 데이터
    review_patterns = behavior_analysis.get("review_patterns", {})
    total_reviews = review_patterns.get("total_reviews", 0)
    if total_reviews >= 10:
        confidence_factors.append(0.3)
    elif total_reviews >= 3:
        confidence_factors.append(0.2)

    # 활동 기간
    engagement_metrics = behavior_analysis.get("engagement_metrics", {})
    if engagement_metrics:
        confidence_factors.append(0.2)

    return min(sum(confidence_factors), 1.0)


def _compare_user_behaviors(
    analysis1: dict[str, Any], analysis2: dict[str, Any]
) -> dict[str, Any]:
    """사용자 행동 비교"""
    comparison = {"similarity_score": 0.0, "differences": [], "similarities": []}

    # 간단한 비교 로직
    travel_patterns1 = analysis1.get("travel_patterns", {})
    travel_patterns2 = analysis2.get("travel_patterns", {})

    trips1 = travel_patterns1.get("total_trips", 0)
    trips2 = travel_patterns2.get("total_trips", 0)

    if abs(trips1 - trips2) <= 2:
        comparison["similarities"].append("비슷한 여행 빈도")
        comparison["similarity_score"] += 0.3
    else:
        comparison["differences"].append("다른 여행 빈도")

    return comparison


logger.info("AI behavior analysis router initialized")
