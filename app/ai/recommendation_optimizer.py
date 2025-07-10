"""
개인화 추천 알고리즘 최적화 시스템
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np
try:
    import pandas as pd
except ImportError:
    pd = None
from sklearn.decomposition import NMF, TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import (
    Destination,
    Review,
    SearchHistory,
    TravelPlan,
    UserPreference,
)
from app.utils.async_processing import AsyncBatch

logger = get_logger("recommendation_optimizer")


class OptimizationStrategy(Enum):
    """최적화 전략"""

    COLLABORATIVE_FILTERING = "collaborative_filtering"
    CONTENT_BASED = "content_based"
    MATRIX_FACTORIZATION = "matrix_factorization"
    DEEP_LEARNING = "deep_learning"
    HYBRID_ENSEMBLE = "hybrid_ensemble"
    REAL_TIME_LEARNING = "real_time_learning"


@dataclass
class OptimizationMetrics:
    """최적화 메트릭"""

    precision: float
    recall: float
    f1_score: float
    map_score: float  # Mean Average Precision
    ndcg_score: float  # Normalized Discounted Cumulative Gain
    diversity_score: float
    novelty_score: float
    coverage_score: float
    timestamp: datetime


@dataclass
class UserEmbedding:
    """사용자 임베딩"""

    user_id: str
    embedding: np.ndarray
    preferences: dict[str, float]
    behavior_patterns: dict[str, Any]
    last_updated: datetime


@dataclass
class DestinationEmbedding:
    """목적지 임베딩"""

    destination_id: str
    embedding: np.ndarray
    features: dict[str, float]
    category_weights: dict[str, float]
    seasonal_factors: dict[str, float]
    last_updated: datetime


class AdvancedCollaborativeFiltering:
    """고급 협업 필터링"""

    def __init__(self, db: Session):
        self.db = db
        self.user_similarity_matrix = None
        self.item_similarity_matrix = None
        self.user_embeddings = {}
        self.item_embeddings = {}
        self.svd_model = TruncatedSVD(n_components=50, random_state=42)
        self.nmf_model = NMF(n_components=50, random_state=42)

    async def build_similarity_matrices(self):
        """유사도 행렬 구축"""
        try:
            # 사용자-아이템 상호작용 매트릭스 생성
            interaction_matrix = await self._build_interaction_matrix()

            if interaction_matrix.empty:
                return

            # 매트릭스 팩토라이제이션
            user_factors = self.svd_model.fit_transform(interaction_matrix)
            item_factors = self.svd_model.components_.T

            # 사용자 유사도 계산
            self.user_similarity_matrix = cosine_similarity(user_factors)

            # 아이템 유사도 계산
            self.item_similarity_matrix = cosine_similarity(item_factors)

            # 임베딩 저장
            user_ids = interaction_matrix.index.tolist()
            destination_ids = interaction_matrix.columns.tolist()

            for i, user_id in enumerate(user_ids):
                self.user_embeddings[user_id] = UserEmbedding(
                    user_id=user_id,
                    embedding=user_factors[i],
                    preferences=await self._extract_user_preferences(user_id),
                    behavior_patterns=await self._analyze_user_behavior(user_id),
                    last_updated=datetime.now(),
                )

            for i, dest_id in enumerate(destination_ids):
                self.item_embeddings[dest_id] = DestinationEmbedding(
                    destination_id=dest_id,
                    embedding=item_factors[i],
                    features=await self._extract_destination_features(dest_id),
                    category_weights=await self._analyze_category_weights(dest_id),
                    seasonal_factors=await self._analyze_seasonal_factors(dest_id),
                    last_updated=datetime.now(),
                )

            logger.info("Similarity matrices built successfully")

        except Exception as e:
            logger.error(f"Error building similarity matrices: {e}")

    async def _build_interaction_matrix(self) -> pd.DataFrame:
        """상호작용 매트릭스 구축"""
        try:
            # 리뷰 데이터에서 상호작용 추출
            reviews = (
                self.db.query(Review)
                .filter(
                    and_(
                        Review.rating.isnot(None),
                        Review.created_at >= datetime.now() - timedelta(days=365),
                    )
                )
                .all()
            )

            # 여행 계획 데이터 추가
            plans = (
                self.db.query(TravelPlan)
                .filter(TravelPlan.created_at >= datetime.now() - timedelta(days=365))
                .all()
            )

            interactions = []

            # 리뷰 기반 상호작용
            for review in reviews:
                interactions.append(
                    {
                        "user_id": review.user_id,
                        "destination_id": review.destination_id,
                        "rating": review.rating,
                        "weight": 1.0,
                    }
                )

            # 여행 계획 기반 상호작용 (암시적 피드백)
            for plan in plans:
                # 실제로는 travel_day_destinations 테이블 조인 필요
                # 여기서는 간소화
                interactions.append(
                    {
                        "user_id": plan.user_id,
                        "destination_id": "implicit_destination",  # 실제 구현에서는 실제 목적지
                        "rating": 3.5,  # 암시적 선호도
                        "weight": 0.5,
                    }
                )

            if not interactions:
                return pd.DataFrame()

            df = pd.DataFrame(interactions)

            # 가중 평균 계산
            interaction_matrix = df.pivot_table(
                values="rating",
                index="user_id",
                columns="destination_id",
                aggfunc="mean",
                fill_value=0,
            )

            return interaction_matrix

        except Exception as e:
            logger.error(f"Error building interaction matrix: {e}")
            return pd.DataFrame()

    async def _extract_user_preferences(self, user_id: str) -> dict[str, float]:
        """사용자 선호도 추출"""
        try:
            user_prefs = (
                self.db.query(UserPreference)
                .filter(UserPreference.user_id == user_id)
                .first()
            )

            if user_prefs:
                return {
                    "preferred_region": 1.0 if user_prefs.preferred_region else 0.0,
                    "preferred_season": 1.0 if user_prefs.preferred_season else 0.0,
                    "budget_range": getattr(user_prefs, "budget_range", 50000) / 100000,
                    "travel_style": getattr(user_prefs, "travel_style", "leisure"),
                }

            return {}

        except Exception as e:
            logger.error(f"Error extracting user preferences: {e}")
            return {}

    async def _analyze_user_behavior(self, user_id: str) -> dict[str, Any]:
        """사용자 행동 분석"""
        try:
            # 검색 이력 분석
            search_history = (
                self.db.query(SearchHistory)
                .filter(
                    and_(
                        SearchHistory.user_id == user_id,
                        SearchHistory.created_at >= datetime.now() - timedelta(days=90),
                    )
                )
                .limit(100)
                .all()
            )

            # 여행 계획 패턴 분석
            travel_plans = (
                self.db.query(TravelPlan)
                .filter(TravelPlan.user_id == user_id)
                .limit(50)
                .all()
            )

            behavior = {
                "search_frequency": len(search_history) / 90,
                "planning_frequency": len(travel_plans) / 365,
                "avg_trip_duration": 0,
                "preferred_months": [],
                "activity_pattern": "regular",
            }

            if travel_plans:
                durations = []
                months = []

                for plan in travel_plans:
                    if plan.end_date and plan.start_date:
                        duration = (plan.end_date - plan.start_date).days
                        durations.append(duration)
                        months.append(plan.start_date.month)

                if durations:
                    behavior["avg_trip_duration"] = sum(durations) / len(durations)

                if months:
                    # 가장 자주 여행하는 월들
                    from collections import Counter

                    month_counts = Counter(months)
                    behavior["preferred_months"] = [
                        month for month, count in month_counts.most_common(3)
                    ]

            return behavior

        except Exception as e:
            logger.error(f"Error analyzing user behavior: {e}")
            return {}

    async def _extract_destination_features(
        self, destination_id: str
    ) -> dict[str, float]:
        """목적지 특성 추출"""
        try:
            destination = (
                self.db.query(Destination)
                .filter(Destination.destination_id == destination_id)
                .first()
            )

            if not destination:
                return {}

            # 리뷰 통계
            reviews = (
                self.db.query(Review)
                .filter(Review.destination_id == destination_id)
                .all()
            )

            features = {
                "latitude": destination.latitude or 0.0,
                "longitude": destination.longitude or 0.0,
                "avg_rating": 0.0,
                "review_count": len(reviews),
                "popularity_score": 0.0,
                "category_encoded": self._encode_category(destination.category),
                "region_encoded": self._encode_region(destination.region),
            }

            if reviews:
                ratings = [r.rating for r in reviews if r.rating]
                if ratings:
                    features["avg_rating"] = sum(ratings) / len(ratings)
                    features["popularity_score"] = (
                        len(ratings) * features["avg_rating"] / 5.0
                    )

            return features

        except Exception as e:
            logger.error(f"Error extracting destination features: {e}")
            return {}

    async def _analyze_category_weights(self, destination_id: str) -> dict[str, float]:
        """카테고리 가중치 분석"""
        try:
            destination = (
                self.db.query(Destination)
                .filter(Destination.destination_id == destination_id)
                .first()
            )

            if not destination:
                return {}

            # 카테고리별 가중치 (실제로는 더 복잡한 분석)
            category_weights = {
                "관광지": 1.0,
                "음식점": 0.8,
                "숙박": 0.9,
                "쇼핑": 0.7,
                "문화시설": 0.85,
                "레저": 0.75,
            }

            return {
                destination.category: category_weights.get(destination.category, 0.5)
            }

        except Exception as e:
            logger.error(f"Error analyzing category weights: {e}")
            return {}

    async def _analyze_seasonal_factors(self, destination_id: str) -> dict[str, float]:
        """계절적 요인 분석"""
        try:
            # 월별 방문 패턴 분석
            monthly_visits = (
                self.db.query(
                    func.extract("month", TravelPlan.start_date).label("month"),
                    func.count(TravelPlan.plan_id).label("visit_count"),
                )
                .join(
                    # 실제로는 travel_day_destinations 테이블과 조인
                    # 여기서는 간소화
                )
                .group_by(func.extract("month", TravelPlan.start_date))
                .all()
            )

            seasonal_factors = {}
            max_visits = (
                max([v.visit_count for v in monthly_visits]) if monthly_visits else 1
            )

            for visit in monthly_visits:
                month = int(visit.month)
                factor = visit.visit_count / max_visits
                seasonal_factors[f"month_{month}"] = factor

            return seasonal_factors

        except Exception as e:
            logger.error(f"Error analyzing seasonal factors: {e}")
            return {}

    def _encode_category(self, category: str) -> float:
        """카테고리 인코딩"""
        category_map = {
            "관광지": 0.1,
            "음식점": 0.2,
            "숙박": 0.3,
            "쇼핑": 0.4,
            "문화시설": 0.5,
            "레저": 0.6,
        }
        return category_map.get(category, 0.0)

    def _encode_region(self, region: str) -> float:
        """지역 인코딩"""
        region_map = {
            "서울": 0.1,
            "부산": 0.2,
            "대구": 0.3,
            "인천": 0.4,
            "광주": 0.5,
            "대전": 0.6,
            "울산": 0.7,
            "세종": 0.8,
            "경기": 0.9,
            "강원": 1.0,
            "충북": 1.1,
            "충남": 1.2,
            "전북": 1.3,
            "전남": 1.4,
            "경북": 1.5,
            "경남": 1.6,
            "제주": 1.7,
        }
        return region_map.get(region, 0.0)


class RealTimeLearningSystem:
    """실시간 학습 시스템"""

    def __init__(self, db: Session):
        self.db = db
        self.learning_rate = 0.01
        self.batch_size = 32
        self.update_threshold = 10
        self.pending_updates = []

    async def process_user_interaction(
        self,
        user_id: str,
        destination_id: str,
        interaction_type: str,
        rating: float | None = None,
    ):
        """사용자 상호작용 처리"""
        try:
            interaction = {
                "user_id": user_id,
                "destination_id": destination_id,
                "interaction_type": interaction_type,
                "rating": rating,
                "timestamp": datetime.now(),
            }

            self.pending_updates.append(interaction)

            # 배치 크기에 도달하면 업데이트 수행
            if len(self.pending_updates) >= self.batch_size:
                await self._update_models()

        except Exception as e:
            logger.error(f"Error processing user interaction: {e}")

    async def _update_models(self):
        """모델 업데이트"""
        try:
            if not self.pending_updates:
                return

            # 임베딩 업데이트
            await self._update_embeddings()

            # 유사도 매트릭스 증분 업데이트
            await self._incremental_similarity_update()

            # 업데이트 완료 후 초기화
            self.pending_updates.clear()

            logger.info("Real-time model update completed")

        except Exception as e:
            logger.error(f"Error updating models: {e}")

    async def _update_embeddings(self):
        """임베딩 업데이트"""
        # 실제 구현에서는 더 정교한 임베딩 업데이트 로직
        pass

    async def _incremental_similarity_update(self):
        """증분 유사도 업데이트"""
        # 실제 구현에서는 효율적인 증분 업데이트
        pass


class RecommendationOptimizer:
    """추천 알고리즘 최적화 메인 클래스"""

    def __init__(self, db: Session):
        self.db = db
        self.collaborative_filter = AdvancedCollaborativeFiltering(db)
        self.real_time_learner = RealTimeLearningSystem(db)
        self.batch_processor = AsyncBatch(batch_size=50, max_concurrent=5)
        self.scaler = MinMaxScaler()

    async def optimize_recommendations(
        self,
        user_id: str,
        strategy: OptimizationStrategy = OptimizationStrategy.HYBRID_ENSEMBLE,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """최적화된 추천 생성"""
        try:
            if strategy == OptimizationStrategy.COLLABORATIVE_FILTERING:
                return await self._collaborative_filtering_recommendations(
                    user_id, limit
                )
            elif strategy == OptimizationStrategy.CONTENT_BASED:
                return await self._content_based_recommendations(user_id, limit)
            elif strategy == OptimizationStrategy.MATRIX_FACTORIZATION:
                return await self._matrix_factorization_recommendations(user_id, limit)
            elif strategy == OptimizationStrategy.HYBRID_ENSEMBLE:
                return await self._hybrid_ensemble_recommendations(user_id, limit)
            elif strategy == OptimizationStrategy.REAL_TIME_LEARNING:
                return await self._real_time_learning_recommendations(user_id, limit)
            else:
                return await self._hybrid_ensemble_recommendations(user_id, limit)

        except Exception as e:
            logger.error(f"Error optimizing recommendations: {e}")
            return []

    async def _collaborative_filtering_recommendations(
        self, user_id: str, limit: int
    ) -> list[dict[str, Any]]:
        """협업 필터링 기반 추천"""
        try:
            # 유사한 사용자 찾기
            similar_users = await self._find_similar_users(user_id, top_k=50)

            # 유사 사용자들의 선호 아이템 수집
            recommendations = []

            for similar_user_id, similarity in similar_users:
                user_preferences = await self._get_user_preferences(similar_user_id)

                for dest_id, rating in user_preferences.items():
                    # 이미 사용자가 평가한 아이템은 제외
                    if not await self._user_has_rated(user_id, dest_id):
                        score = rating * similarity
                        recommendations.append(
                            {
                                "destination_id": dest_id,
                                "score": score,
                                "reason": "유사한 사용자들이 선호하는 여행지",
                                "algorithm": "collaborative_filtering",
                            }
                        )

            # 점수 기준 정렬 및 중복 제거
            recommendations = self._aggregate_and_rank(recommendations, limit)

            return recommendations

        except Exception as e:
            logger.error(f"Error in collaborative filtering: {e}")
            return []

    async def _content_based_recommendations(
        self, user_id: str, limit: int
    ) -> list[dict[str, Any]]:
        """콘텐츠 기반 추천"""
        try:
            # 사용자 프로파일 구축
            user_profile = await self._build_user_profile(user_id)

            # 모든 목적지와 유사도 계산
            all_destinations = self.db.query(Destination).limit(1000).all()

            recommendations = []

            for destination in all_destinations:
                # 이미 방문했거나 평가한 목적지는 제외
                if await self._user_has_rated(user_id, destination.destination_id):
                    continue

                # 콘텐츠 유사도 계산
                similarity = await self._calculate_content_similarity(
                    user_profile, destination
                )

                if similarity > 0.1:  # 임계값
                    recommendations.append(
                        {
                            "destination_id": destination.destination_id,
                            "score": similarity,
                            "reason": f"당신의 취향과 {similarity:.2f} 유사",
                            "algorithm": "content_based",
                        }
                    )

            # 점수 기준 정렬
            recommendations.sort(key=lambda x: x["score"], reverse=True)

            return recommendations[:limit]

        except Exception as e:
            logger.error(f"Error in content-based recommendations: {e}")
            return []

    async def _matrix_factorization_recommendations(
        self, user_id: str, limit: int
    ) -> list[dict[str, Any]]:
        """매트릭스 팩토라이제이션 기반 추천"""
        try:
            # 사용자 임베딩 조회
            user_embedding = self.collaborative_filter.user_embeddings.get(user_id)

            if not user_embedding:
                return []

            recommendations = []

            # 모든 아이템 임베딩과 유사도 계산
            for (
                dest_id,
                dest_embedding,
            ) in self.collaborative_filter.item_embeddings.items():
                # 이미 평가한 아이템 제외
                if await self._user_has_rated(user_id, dest_id):
                    continue

                # 코사인 유사도 계산
                similarity = cosine_similarity(
                    user_embedding.embedding.reshape(1, -1),
                    dest_embedding.embedding.reshape(1, -1),
                )[0][0]

                recommendations.append(
                    {
                        "destination_id": dest_id,
                        "score": similarity,
                        "reason": "잠재 선호도 기반 추천",
                        "algorithm": "matrix_factorization",
                    }
                )

            # 점수 기준 정렬
            recommendations.sort(key=lambda x: x["score"], reverse=True)

            return recommendations[:limit]

        except Exception as e:
            logger.error(f"Error in matrix factorization: {e}")
            return []

    async def _hybrid_ensemble_recommendations(
        self, user_id: str, limit: int
    ) -> list[dict[str, Any]]:
        """하이브리드 앙상블 추천"""
        try:
            # 여러 알고리즘 동시 실행
            tasks = [
                self._collaborative_filtering_recommendations(user_id, limit * 2),
                self._content_based_recommendations(user_id, limit * 2),
                self._matrix_factorization_recommendations(user_id, limit * 2),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 통합
            all_recommendations = []

            for i, result in enumerate(results):
                if isinstance(result, list):
                    # 알고리즘별 가중치 적용
                    weights = [0.4, 0.3, 0.3]  # CF, Content, MF

                    for rec in result:
                        rec["score"] *= weights[i]
                        all_recommendations.append(rec)

            # 점수 집계 및 순위 결정
            final_recommendations = self._aggregate_and_rank(all_recommendations, limit)

            return final_recommendations

        except Exception as e:
            logger.error(f"Error in hybrid ensemble: {e}")
            return []

    async def _real_time_learning_recommendations(
        self, user_id: str, limit: int
    ) -> list[dict[str, Any]]:
        """실시간 학습 기반 추천"""
        try:
            # 최근 사용자 행동 분석
            recent_interactions = await self._get_recent_interactions(user_id)

            # 실시간 선호도 업데이트
            await self._update_real_time_preferences(user_id, recent_interactions)

            # 업데이트된 모델로 추천 생성
            return await self._hybrid_ensemble_recommendations(user_id, limit)

        except Exception as e:
            logger.error(f"Error in real-time learning: {e}")
            return []

    async def _find_similar_users(
        self, user_id: str, top_k: int = 50
    ) -> list[tuple[str, float]]:
        """유사한 사용자 찾기"""
        try:
            if (
                self.collaborative_filter.user_similarity_matrix is None
                or user_id not in self.collaborative_filter.user_embeddings
            ):
                return []

            user_embedding = self.collaborative_filter.user_embeddings[user_id]
            similar_users = []

            for (
                other_user_id,
                other_embedding,
            ) in self.collaborative_filter.user_embeddings.items():
                if other_user_id == user_id:
                    continue

                similarity = cosine_similarity(
                    user_embedding.embedding.reshape(1, -1),
                    other_embedding.embedding.reshape(1, -1),
                )[0][0]

                similar_users.append((other_user_id, similarity))

            # 유사도 기준 정렬
            similar_users.sort(key=lambda x: x[1], reverse=True)

            return similar_users[:top_k]

        except Exception as e:
            logger.error(f"Error finding similar users: {e}")
            return []

    async def _get_user_preferences(self, user_id: str) -> dict[str, float]:
        """사용자 선호도 조회"""
        try:
            reviews = (
                self.db.query(Review)
                .filter(and_(Review.user_id == user_id, Review.rating.isnot(None)))
                .all()
            )

            preferences = {}
            for review in reviews:
                preferences[review.destination_id] = review.rating

            return preferences

        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {}

    async def _user_has_rated(self, user_id: str, destination_id: str) -> bool:
        """사용자가 이미 평가했는지 확인"""
        try:
            existing_review = (
                self.db.query(Review)
                .filter(
                    and_(
                        Review.user_id == user_id,
                        Review.destination_id == destination_id,
                    )
                )
                .first()
            )

            return existing_review is not None

        except Exception as e:
            logger.error(f"Error checking user rating: {e}")
            return False

    async def _build_user_profile(self, user_id: str) -> dict[str, Any]:
        """사용자 프로파일 구축"""
        try:
            # 사용자의 과거 평가 및 행동 분석
            reviews = self.db.query(Review).filter(Review.user_id == user_id).all()
            travel_plans = (
                self.db.query(TravelPlan).filter(TravelPlan.user_id == user_id).all()
            )

            profile = {
                "preferred_categories": {},
                "preferred_regions": {},
                "avg_rating": 0.0,
                "rating_count": len(reviews),
                "travel_frequency": len(travel_plans),
            }

            if reviews:
                # 카테고리 선호도 분석
                category_ratings = {}
                region_ratings = {}
                total_rating = 0

                for review in reviews:
                    if review.rating:
                        total_rating += review.rating

                        # 목적지 정보 조회
                        destination = (
                            self.db.query(Destination)
                            .filter(Destination.destination_id == review.destination_id)
                            .first()
                        )

                        if destination:
                            category = destination.category
                            region = destination.region

                            if category not in category_ratings:
                                category_ratings[category] = []
                            category_ratings[category].append(review.rating)

                            if region not in region_ratings:
                                region_ratings[region] = []
                            region_ratings[region].append(review.rating)

                profile["avg_rating"] = total_rating / len(reviews)

                # 평균 평점 계산
                for category, ratings in category_ratings.items():
                    profile["preferred_categories"][category] = sum(ratings) / len(
                        ratings
                    )

                for region, ratings in region_ratings.items():
                    profile["preferred_regions"][region] = sum(ratings) / len(ratings)

            return profile

        except Exception as e:
            logger.error(f"Error building user profile: {e}")
            return {}

    async def _calculate_content_similarity(
        self, user_profile: dict[str, Any], destination: Destination
    ) -> float:
        """콘텐츠 유사도 계산"""
        try:
            similarity = 0.0

            # 카테고리 선호도 매칭
            category_prefs = user_profile.get("preferred_categories", {})
            if destination.category in category_prefs:
                category_score = category_prefs[destination.category] / 5.0
                similarity += category_score * 0.4

            # 지역 선호도 매칭
            region_prefs = user_profile.get("preferred_regions", {})
            if destination.region in region_prefs:
                region_score = region_prefs[destination.region] / 5.0
                similarity += region_score * 0.3

            # 목적지 평균 평점 고려
            dest_reviews = (
                self.db.query(Review)
                .filter(Review.destination_id == destination.destination_id)
                .all()
            )

            if dest_reviews:
                ratings = [r.rating for r in dest_reviews if r.rating]
                if ratings:
                    avg_rating = sum(ratings) / len(ratings)
                    rating_score = avg_rating / 5.0
                    similarity += rating_score * 0.3

            return min(similarity, 1.0)

        except Exception as e:
            logger.error(f"Error calculating content similarity: {e}")
            return 0.0

    def _aggregate_and_rank(
        self, recommendations: list[dict[str, Any]], limit: int
    ) -> list[dict[str, Any]]:
        """추천 결과 집계 및 순위 결정"""
        try:
            # 목적지별로 점수 집계
            dest_scores = {}

            for rec in recommendations:
                dest_id = rec["destination_id"]
                score = rec["score"]

                if dest_id not in dest_scores:
                    dest_scores[dest_id] = {
                        "total_score": 0.0,
                        "count": 0,
                        "algorithms": [],
                        "reasons": [],
                    }

                dest_scores[dest_id]["total_score"] += score
                dest_scores[dest_id]["count"] += 1
                dest_scores[dest_id]["algorithms"].append(
                    rec.get("algorithm", "unknown")
                )
                dest_scores[dest_id]["reasons"].append(rec.get("reason", ""))

            # 최종 추천 목록 생성
            final_recommendations = []

            for dest_id, scores in dest_scores.items():
                avg_score = scores["total_score"] / scores["count"]

                final_recommendations.append(
                    {
                        "destination_id": dest_id,
                        "score": avg_score,
                        "confidence": scores["count"] / len(set(scores["algorithms"])),
                        "algorithms": list(set(scores["algorithms"])),
                        "reasons": scores["reasons"][:3],  # 상위 3개 이유
                    }
                )

            # 점수 기준 정렬
            final_recommendations.sort(key=lambda x: x["score"], reverse=True)

            return final_recommendations[:limit]

        except Exception as e:
            logger.error(f"Error aggregating recommendations: {e}")
            return []

    async def _get_recent_interactions(self, user_id: str) -> list[dict[str, Any]]:
        """최근 상호작용 조회"""
        try:
            # 최근 검색 이력
            recent_searches = (
                self.db.query(SearchHistory)
                .filter(
                    and_(
                        SearchHistory.user_id == user_id,
                        SearchHistory.created_at >= datetime.now() - timedelta(days=7),
                    )
                )
                .order_by(desc(SearchHistory.created_at))
                .limit(50)
                .all()
            )

            # 최근 리뷰
            recent_reviews = (
                self.db.query(Review)
                .filter(
                    and_(
                        Review.user_id == user_id,
                        Review.created_at >= datetime.now() - timedelta(days=30),
                    )
                )
                .order_by(desc(Review.created_at))
                .limit(20)
                .all()
            )

            interactions = []

            for search in recent_searches:
                interactions.append(
                    {
                        "type": "search",
                        "destination_id": getattr(search, "destination_id", None),
                        "query": getattr(search, "query", ""),
                        "timestamp": search.created_at,
                    }
                )

            for review in recent_reviews:
                interactions.append(
                    {
                        "type": "review",
                        "destination_id": review.destination_id,
                        "rating": review.rating,
                        "timestamp": review.created_at,
                    }
                )

            return interactions

        except Exception as e:
            logger.error(f"Error getting recent interactions: {e}")
            return []

    async def _update_real_time_preferences(
        self, user_id: str, interactions: list[dict[str, Any]]
    ):
        """실시간 선호도 업데이트"""
        try:
            # 상호작용 기반 선호도 조정
            for interaction in interactions:
                await self.real_time_learner.process_user_interaction(
                    user_id=user_id,
                    destination_id=interaction.get("destination_id"),
                    interaction_type=interaction["type"],
                    rating=interaction.get("rating"),
                )

        except Exception as e:
            logger.error(f"Error updating real-time preferences: {e}")

    async def evaluate_recommendations(
        self, test_data: list[dict[str, Any]]
    ) -> OptimizationMetrics:
        """추천 성능 평가"""
        try:
            precision_scores = []
            recall_scores = []
            f1_scores = []
            map_scores = []
            ndcg_scores = []

            for test_case in test_data:
                user_id = test_case["user_id"]
                true_items = set(test_case["relevant_items"])

                # 추천 생성
                recommendations = await self.optimize_recommendations(user_id, limit=20)
                recommended_items = set([r["destination_id"] for r in recommendations])

                # 메트릭 계산
                if recommended_items:
                    intersection = true_items.intersection(recommended_items)

                    precision = len(intersection) / len(recommended_items)
                    recall = len(intersection) / len(true_items) if true_items else 0
                    f1 = (
                        2 * precision * recall / (precision + recall)
                        if (precision + recall) > 0
                        else 0
                    )

                    precision_scores.append(precision)
                    recall_scores.append(recall)
                    f1_scores.append(f1)

            # 전체 메트릭 계산
            metrics = OptimizationMetrics(
                precision=(
                    sum(precision_scores) / len(precision_scores)
                    if precision_scores
                    else 0
                ),
                recall=sum(recall_scores) / len(recall_scores) if recall_scores else 0,
                f1_score=sum(f1_scores) / len(f1_scores) if f1_scores else 0,
                map_score=0.0,  # 실제 구현에서는 MAP 계산
                ndcg_score=0.0,  # 실제 구현에서는 NDCG 계산
                diversity_score=0.0,  # 다양성 점수
                novelty_score=0.0,  # 참신성 점수
                coverage_score=0.0,  # 커버리지 점수
                timestamp=datetime.now(),
            )

            return metrics

        except Exception as e:
            logger.error(f"Error evaluating recommendations: {e}")
            return OptimizationMetrics(
                precision=0,
                recall=0,
                f1_score=0,
                map_score=0,
                ndcg_score=0,
                diversity_score=0,
                novelty_score=0,
                coverage_score=0,
                timestamp=datetime.now(),
            )


# 추천 최적화 시스템 싱글톤
recommendation_optimizer = None


def get_recommendation_optimizer(db: Session) -> RecommendationOptimizer:
    """추천 최적화 시스템 인스턴스 반환"""
    global recommendation_optimizer
    if recommendation_optimizer is None:
        recommendation_optimizer = RecommendationOptimizer(db)
    return recommendation_optimizer


logger.info("Recommendation optimization system initialized")
