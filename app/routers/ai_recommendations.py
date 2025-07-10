"""
AI 기반 여행 추천 시스템 API 라우터
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.ai.recommendation_engine import get_recommendation_engine
from app.auth.dependencies import get_current_admin
from app.database import get_db
from app.logging_config import get_logger
from app.utils.cache import CACHE_PREFIX, CACHE_TTL, cache_result

logger = get_logger("ai_recommendations")

router = APIRouter(prefix="/ai/recommendations", tags=["AI Recommendations"])


class RecommendationRequest(BaseModel):
    """추천 요청 모델"""

    recommendation_type: str = Field(
        ..., description="추천 유형: content, collaborative, weather, hybrid"
    )
    limit: int = Field(10, ge=1, le=50, description="추천 개수")
    travel_date: str | None = Field(None, description="여행 예정일 (YYYY-MM-DD)")
    filters: dict[str, Any] | None = Field(None, description="추가 필터 조건")


class RecommendationResponse(BaseModel):
    """추천 응답 모델"""

    destination_id: str
    name: str
    score: float
    recommendation_type: str
    reasoning: dict[str, Any] | None = None

    class Config:
        from_attributes = True


@router.post("/", response_model=None)
@cache_result(ttl=CACHE_TTL["SHORT"], prefix=CACHE_PREFIX["RECOMMENDATIONS"])
async def get_recommendations(
    request: RecommendationRequest,
    current_admin=Depends(get_current_admin),
    engine=Depends(get_recommendation_engine),
):
    """AI 기반 여행지 추천"""
    try:
        user_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        # 여행 날짜 파싱
        travel_date = None
        if request.travel_date:
            try:
                travel_date = datetime.strptime(request.travel_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
                )

        # 추천 유형에 따른 처리
        if request.recommendation_type == "content":
            recommendations = engine.get_content_based_recommendations(
                user_id, request.limit
            )
        elif request.recommendation_type == "collaborative":
            recommendations = engine.get_collaborative_recommendations(
                user_id, request.limit
            )
        elif request.recommendation_type == "weather":
            if not travel_date:
                raise HTTPException(
                    status_code=400,
                    detail="Travel date required for weather-based recommendations",
                )
            recommendations = engine.get_weather_based_recommendations(
                user_id, travel_date, request.limit
            )
        elif request.recommendation_type == "hybrid":
            recommendations = engine.get_hybrid_recommendations(
                user_id, request.limit, travel_date
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid recommendation type. Use: content, collaborative, weather, hybrid",
            )

        # 응답 형식으로 변환
        response_data = []
        for rec in recommendations:
            destination = rec["destination"]
            response_data.append(
                RecommendationResponse(
                    destination_id=str(destination.destination_id),
                    name=destination.name,
                    score=rec["score"],
                    recommendation_type=rec["recommendation_type"],
                    reasoning=rec.get("reasoning", {}),
                )
            )

        logger.info(
            f"Generated {len(response_data)} recommendations for user {user_id}"
        )
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate recommendations"
        )


@router.get("/user-profile", response_model=None)
async def get_user_profile_analysis(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    engine=Depends(get_recommendation_engine),
):
    """사용자 프로필 분석 정보"""
    try:
        user_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        from app.ai.recommendation_engine import UserProfile

        user_profile = UserProfile(user_id, db)

        return {
            "user_id": user_id,
            "profile_data": user_profile.profile_data,
            "analysis_timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting user profile analysis: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get user profile analysis"
        )


@router.get("/content-based", response_model=None)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["RECOMMENDATIONS"])
async def get_content_based_recommendations(
    limit: int = Query(10, ge=1, le=50, description="추천 개수"),
    current_admin=Depends(get_current_admin),
    engine=Depends(get_recommendation_engine),
):
    """콘텐츠 기반 추천"""
    try:
        user_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        recommendations = engine.get_content_based_recommendations(user_id, limit)

        return {
            "recommendation_type": "content_based",
            "user_id": user_id,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting content-based recommendations: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get content-based recommendations"
        )


@router.get("/collaborative", response_model=None)
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["RECOMMENDATIONS"])
async def get_collaborative_recommendations(
    limit: int = Query(10, ge=1, le=50, description="추천 개수"),
    current_admin=Depends(get_current_admin),
    engine=Depends(get_recommendation_engine),
):
    """협업 필터링 추천"""
    try:
        user_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        recommendations = engine.get_collaborative_recommendations(user_id, limit)

        return {
            "recommendation_type": "collaborative",
            "user_id": user_id,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting collaborative recommendations: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get collaborative recommendations"
        )


@router.get("/weather-based", response_model=None)
@cache_result(ttl=CACHE_TTL["SHORT"], prefix=CACHE_PREFIX["RECOMMENDATIONS"])
async def get_weather_based_recommendations(
    travel_date: str = Query(..., description="여행 예정일 (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=50, description="추천 개수"),
    current_admin=Depends(get_current_admin),
    engine=Depends(get_recommendation_engine),
):
    """날씨 기반 추천"""
    try:
        user_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        # 날짜 파싱
        try:
            parsed_date = datetime.strptime(travel_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
            )

        recommendations = engine.get_weather_based_recommendations(
            user_id, parsed_date, limit
        )

        return {
            "recommendation_type": "weather_based",
            "user_id": user_id,
            "travel_date": travel_date,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting weather-based recommendations: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get weather-based recommendations"
        )


@router.get("/hybrid", response_model=None)
@cache_result(ttl=CACHE_TTL["SHORT"], prefix=CACHE_PREFIX["RECOMMENDATIONS"])
async def get_hybrid_recommendations(
    limit: int = Query(10, ge=1, le=50, description="추천 개수"),
    travel_date: str | None = Query(None, description="여행 예정일 (YYYY-MM-DD)"),
    current_admin=Depends(get_current_admin),
    engine=Depends(get_recommendation_engine),
):
    """하이브리드 추천 (여러 방법 조합)"""
    try:
        user_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        # 날짜 파싱 (선택사항)
        parsed_date = None
        if travel_date:
            try:
                parsed_date = datetime.strptime(travel_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
                )

        recommendations = engine.get_hybrid_recommendations(user_id, limit, parsed_date)

        return {
            "recommendation_type": "hybrid",
            "user_id": user_id,
            "travel_date": travel_date,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting hybrid recommendations: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get hybrid recommendations"
        )


@router.post("/train-model", response_model=None)
async def train_recommendation_model(
    current_admin=Depends(get_current_admin),
    engine=Depends(get_recommendation_engine),
):
    """추천 모델 학습 (관리자만 사용)"""
    try:
        # 관리자 권한 확인
        if not current_user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Admin access required")

        # 모델 학습 실행
        engine.train_model()

        return {
            "success": True,
            "message": "Recommendation model training initiated",
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error training recommendation model: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to train recommendation model"
        )


@router.get("/stats", response_model=None)
async def get_recommendation_stats(
    db=Depends(get_db), current_admin=Depends(get_current_admin)
):
    """추천 시스템 통계"""
    try:
        user_id = current_admin.admin_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        from app.ai.recommendation_engine import UserProfile

        user_profile = UserProfile(user_id, db)

        # 기본 통계 정보
        stats = {
            "user_id": user_id,
            "profile_completeness": _calculate_profile_completeness(
                user_profile.profile_data
            ),
            "total_travel_plans": user_profile.profile_data.get(
                "travel_history", {}
            ).get("total_trips", 0),
            "total_reviews": user_profile.profile_data.get("review_patterns", {}).get(
                "total_reviews", 0
            ),
            "avg_rating": user_profile.profile_data.get("review_patterns", {}).get(
                "avg_rating", 0
            ),
            "behavioral_scores": user_profile.profile_data.get("behavioral_score", {}),
            "preferred_regions": user_profile.profile_data.get("preferences", {}).get(
                "preferred_regions", []
            ),
            "preferred_themes": user_profile.profile_data.get("preferences", {}).get(
                "preferred_themes", []
            ),
            "analysis_timestamp": datetime.now().isoformat(),
        }

        return stats

    except Exception as e:
        logger.error(f"Error getting recommendation stats: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get recommendation stats"
        )


def _calculate_profile_completeness(profile_data: dict[str, Any]) -> float:
    """프로필 완성도 계산"""
    try:
        total_fields = 5
        completed_fields = 0

        # 기본 정보
        if profile_data.get("basic_info"):
            completed_fields += 1

        # 선호도 정보
        preferences = profile_data.get("preferences", {})
        if preferences.get("preferred_regions") or preferences.get("preferred_themes"):
            completed_fields += 1

        # 여행 이력
        if profile_data.get("travel_history", {}).get("total_trips", 0) > 0:
            completed_fields += 1

        # 리뷰 패턴
        if profile_data.get("review_patterns", {}).get("total_reviews", 0) > 0:
            completed_fields += 1

        # 행동 점수
        if profile_data.get("behavioral_score"):
            completed_fields += 1

        return completed_fields / total_fields

    except Exception:
        return 0.0


logger.info("AI recommendations router initialized")
