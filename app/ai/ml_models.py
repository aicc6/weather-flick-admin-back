"""
머신러닝 모델 통합 시스템
"""

import pickle
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
try:
    import pandas as pd
except ImportError:
    pd = None
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from app.logging_config import get_logger

logger = get_logger("ml_models")


class ModelType(Enum):
    """모델 유형"""

    RECOMMENDATION = "recommendation"
    CLASSIFICATION = "classification"
    CLUSTERING = "clustering"
    DEEP_LEARNING = "deep_learning"
    NLP = "nlp"


@dataclass
class ModelMetrics:
    """모델 성능 메트릭"""

    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_time: float
    model_size: int
    timestamp: datetime


@dataclass
class ModelConfig:
    """모델 설정"""

    model_type: ModelType
    name: str
    version: str
    hyperparameters: dict[str, Any]
    feature_columns: list[str]
    target_column: str
    preprocessing_steps: list[str]


class ModelManager:
    """모델 관리자"""

    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        self.loaded_models = {}
        self.model_configs = {}
        self.scalers = {}
        self.encoders = {}

    def save_model(
        self,
        model: Any,
        model_name: str,
        config: ModelConfig,
        metrics: ModelMetrics | None = None,
    ) -> str:
        """모델 저장"""
        try:
            # 모델 파일 경로
            model_path = self.model_dir / f"{model_name}.pkl"
            config_path = self.model_dir / f"{model_name}_config.pkl"
            metrics_path = self.model_dir / f"{model_name}_metrics.pkl"

            # 모델 저장
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            # 설정 저장
            with open(config_path, "wb") as f:
                pickle.dump(config, f)

            # 메트릭 저장
            if metrics:
                with open(metrics_path, "wb") as f:
                    pickle.dump(metrics, f)

            logger.info(f"Model saved: {model_name}")
            return str(model_path)

        except Exception as e:
            logger.error(f"Error saving model {model_name}: {e}")
            raise

    def load_model(self, model_name: str) -> tuple[Any, ModelConfig]:
        """모델 로드"""
        try:
            if model_name in self.loaded_models:
                return self.loaded_models[model_name], self.model_configs[model_name]

            # 모델 파일 경로
            model_path = self.model_dir / f"{model_name}.pkl"
            config_path = self.model_dir / f"{model_name}_config.pkl"

            if not model_path.exists():
                raise FileNotFoundError(f"Model not found: {model_name}")

            # 모델 로드
            with open(model_path, "rb") as f:
                model = pickle.load(f)

            # 설정 로드
            with open(config_path, "rb") as f:
                config = pickle.load(f)

            # 캐시에 저장
            self.loaded_models[model_name] = model
            self.model_configs[model_name] = config

            logger.info(f"Model loaded: {model_name}")
            return model, config

        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            raise

    def get_model_metrics(self, model_name: str) -> ModelMetrics | None:
        """모델 메트릭 조회"""
        try:
            metrics_path = self.model_dir / f"{model_name}_metrics.pkl"

            if not metrics_path.exists():
                return None

            with open(metrics_path, "rb") as f:
                metrics = pickle.load(f)

            return metrics

        except Exception as e:
            logger.error(f"Error loading metrics for {model_name}: {e}")
            return None

    def list_models(self) -> list[dict[str, Any]]:
        """모델 목록 조회"""
        try:
            models = []

            for model_file in self.model_dir.glob("*.pkl"):
                if "_config" in model_file.name or "_metrics" in model_file.name:
                    continue

                model_name = model_file.stem
                config = None
                metrics = None

                try:
                    _, config = self.load_model(model_name)
                    metrics = self.get_model_metrics(model_name)
                except:
                    pass

                models.append(
                    {
                        "name": model_name,
                        "path": str(model_file),
                        "size": model_file.stat().st_size,
                        "created": datetime.fromtimestamp(model_file.stat().st_ctime),
                        "config": asdict(config) if config else None,
                        "metrics": asdict(metrics) if metrics else None,
                    }
                )

            return models

        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    def delete_model(self, model_name: str) -> bool:
        """모델 삭제"""
        try:
            model_path = self.model_dir / f"{model_name}.pkl"
            config_path = self.model_dir / f"{model_name}_config.pkl"
            metrics_path = self.model_dir / f"{model_name}_metrics.pkl"

            # 파일 삭제
            for path in [model_path, config_path, metrics_path]:
                if path.exists():
                    path.unlink()

            # 캐시에서 제거
            if model_name in self.loaded_models:
                del self.loaded_models[model_name]
            if model_name in self.model_configs:
                del self.model_configs[model_name]

            logger.info(f"Model deleted: {model_name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting model {model_name}: {e}")
            return False


class TravelRecommendationModel:
    """여행 추천 모델"""

    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.model_name = "travel_recommendation"
        self.model = None
        self.config = None
        self.scaler = StandardScaler()
        self.user_encoder = LabelEncoder()
        self.destination_encoder = LabelEncoder()
        self.tfidf_vectorizer = TfidfVectorizer(max_features=100)

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """특성 준비"""
        features = df.copy()

        # 사용자 특성
        features["user_encoded"] = self.user_encoder.fit_transform(features["user_id"])
        features["destination_encoded"] = self.destination_encoder.fit_transform(
            features["destination_id"]
        )

        # 시간 특성
        features["month"] = pd.to_datetime(features["created_at"]).dt.month
        features["day_of_week"] = pd.to_datetime(features["created_at"]).dt.dayofweek
        features["hour"] = pd.to_datetime(features["created_at"]).dt.hour

        # 선호도 특성
        features["avg_rating"] = features.groupby("user_id")["rating"].transform("mean")
        features["rating_count"] = features.groupby("user_id")["rating"].transform(
            "count"
        )

        return features

    def train(self, training_data: pd.DataFrame) -> ModelMetrics:
        """모델 학습"""
        try:
            start_time = datetime.now()

            # 특성 준비
            features = self.prepare_features(training_data)

            # 특성 선택
            feature_columns = [
                "user_encoded",
                "destination_encoded",
                "month",
                "day_of_week",
                "hour",
                "avg_rating",
                "rating_count",
            ]

            X = features[feature_columns]
            y = features["rating"] >= 4.0  # 4점 이상을 긍정으로 분류

            # 데이터 분할
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # 특성 스케일링
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # 모델 학습
            self.model = RandomForestClassifier(
                n_estimators=100, max_depth=10, random_state=42
            )
            self.model.fit(X_train_scaled, y_train)

            # 성능 평가
            y_pred = self.model.predict(X_test_scaled)

            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, average="weighted")
            recall = recall_score(y_test, y_pred, average="weighted")
            f1 = f1_score(y_test, y_pred, average="weighted")

            training_time = (datetime.now() - start_time).total_seconds()

            # 모델 설정
            self.config = ModelConfig(
                model_type=ModelType.RECOMMENDATION,
                name=self.model_name,
                version="1.0",
                hyperparameters={
                    "n_estimators": 100,
                    "max_depth": 10,
                    "random_state": 42,
                },
                feature_columns=feature_columns,
                target_column="rating",
                preprocessing_steps=["scaling", "encoding"],
            )

            # 메트릭 생성
            metrics = ModelMetrics(
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                training_time=training_time,
                model_size=len(pickle.dumps(self.model)),
                timestamp=datetime.now(),
            )

            # 모델 저장
            self.model_manager.save_model(
                self.model, self.model_name, self.config, metrics
            )

            logger.info(f"Model trained successfully: {self.model_name}")
            return metrics

        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise

    def predict(self, user_id: str, destination_ids: list[str]) -> list[dict[str, Any]]:
        """추천 예측"""
        try:
            if not self.model:
                self.model, self.config = self.model_manager.load_model(self.model_name)

            predictions = []

            for dest_id in destination_ids:
                # 가상 특성 생성 (실제로는 사용자 데이터에서 추출)
                feature_data = {
                    "user_id": user_id,
                    "destination_id": dest_id,
                    "created_at": datetime.now(),
                    "rating": 3.0,  # 기본값
                }

                # 특성 변환
                features_df = pd.DataFrame([feature_data])
                prepared_features = self.prepare_features(features_df)

                X = prepared_features[self.config.feature_columns]
                X_scaled = self.scaler.transform(X)

                # 예측
                prediction_proba = self.model.predict_proba(X_scaled)[0]
                prediction = self.model.predict(X_scaled)[0]

                predictions.append(
                    {
                        "destination_id": dest_id,
                        "recommendation_score": float(prediction_proba[1]),
                        "is_recommended": bool(prediction),
                        "confidence": float(max(prediction_proba)),
                    }
                )

            # 점수순 정렬
            predictions.sort(key=lambda x: x["recommendation_score"], reverse=True)

            return predictions

        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            return []


class UserClusteringModel:
    """사용자 클러스터링 모델"""

    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.model_name = "user_clustering"
        self.model = None
        self.config = None
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=10)

    def prepare_user_features(self, users_data: pd.DataFrame) -> pd.DataFrame:
        """사용자 특성 준비"""
        features = users_data.copy()

        # 활동 특성
        features["days_since_signup"] = (
            datetime.now() - pd.to_datetime(features["created_at"])
        ).dt.days
        features["days_since_last_login"] = (
            datetime.now() - pd.to_datetime(features["last_login"])
        ).dt.days

        # 여행 패턴 특성
        features["travel_frequency"] = features.groupby("user_id")[
            "plan_count"
        ].transform("mean")
        features["avg_rating"] = features.groupby("user_id")["avg_rating"].transform(
            "mean"
        )
        features["preferred_season"] = (
            features["preferred_season"].astype("category").cat.codes
        )

        # 지역 선호도 (원핫 인코딩)
        region_encoded = pd.get_dummies(features["preferred_region"], prefix="region")
        features = pd.concat([features, region_encoded], axis=1)

        return features

    def train(self, users_data: pd.DataFrame, n_clusters: int = 5) -> ModelMetrics:
        """클러스터링 모델 학습"""
        try:
            start_time = datetime.now()

            # 특성 준비
            features = self.prepare_user_features(users_data)

            # 수치형 특성 선택
            numeric_features = features.select_dtypes(include=[np.number]).columns
            X = features[numeric_features]

            # 결측값 처리
            X = X.fillna(0)

            # 특성 스케일링
            X_scaled = self.scaler.fit_transform(X)

            # 차원 축소
            X_pca = self.pca.fit_transform(X_scaled)

            # K-means 클러스터링
            self.model = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = self.model.fit_predict(X_pca)

            # 성능 평가 (실루엣 스코어)
            from sklearn.metrics import silhouette_score

            silhouette_avg = silhouette_score(X_pca, cluster_labels)

            training_time = (datetime.now() - start_time).total_seconds()

            # 모델 설정
            self.config = ModelConfig(
                model_type=ModelType.CLUSTERING,
                name=self.model_name,
                version="1.0",
                hyperparameters={"n_clusters": n_clusters, "random_state": 42},
                feature_columns=list(numeric_features),
                target_column="cluster",
                preprocessing_steps=["scaling", "pca"],
            )

            # 메트릭 생성
            metrics = ModelMetrics(
                accuracy=silhouette_avg,  # 클러스터링에서는 실루엣 스코어 사용
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                training_time=training_time,
                model_size=len(pickle.dumps(self.model)),
                timestamp=datetime.now(),
            )

            # 모델 저장
            self.model_manager.save_model(
                self.model, self.model_name, self.config, metrics
            )

            logger.info(f"Clustering model trained successfully: {self.model_name}")
            return metrics

        except Exception as e:
            logger.error(f"Error training clustering model: {e}")
            raise

    def predict_cluster(self, user_features: dict[str, Any]) -> dict[str, Any]:
        """사용자 클러스터 예측"""
        try:
            if not self.model:
                self.model, self.config = self.model_manager.load_model(self.model_name)

            # 특성 변환
            features_df = pd.DataFrame([user_features])
            prepared_features = self.prepare_user_features(features_df)

            X = prepared_features[self.config.feature_columns]
            X = X.fillna(0)

            # 스케일링 및 차원 축소
            X_scaled = self.scaler.transform(X)
            X_pca = self.pca.transform(X_scaled)

            # 클러스터 예측
            cluster_label = self.model.predict(X_pca)[0]

            # 클러스터 중심점과의 거리
            distances = self.model.transform(X_pca)[0]
            confidence = 1.0 / (1.0 + distances[cluster_label])

            return {
                "cluster_id": int(cluster_label),
                "confidence": float(confidence),
                "cluster_center_distance": float(distances[cluster_label]),
            }

        except Exception as e:
            logger.error(f"Error predicting cluster: {e}")
            return {}


class DeepLearningModel:
    """딥러닝 모델 (PyTorch)"""

    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.model_name = "deep_recommendation"
        self.model = None
        self.config = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def create_model(
        self, input_size: int, hidden_sizes: list[int], output_size: int
    ) -> nn.Module:
        """신경망 모델 생성"""

        class RecommendationNet(nn.Module):
            def __init__(self, input_size, hidden_sizes, output_size):
                super().__init__()
                layers = []

                prev_size = input_size
                for hidden_size in hidden_sizes:
                    layers.extend(
                        [nn.Linear(prev_size, hidden_size), nn.ReLU(), nn.Dropout(0.2)]
                    )
                    prev_size = hidden_size

                layers.append(nn.Linear(prev_size, output_size))
                layers.append(nn.Sigmoid())

                self.network = nn.Sequential(*layers)

            def forward(self, x):
                return self.network(x)

        return RecommendationNet(input_size, hidden_sizes, output_size)

    def train(self, training_data: pd.DataFrame, epochs: int = 100) -> ModelMetrics:
        """딥러닝 모델 학습"""
        try:
            start_time = datetime.now()

            # 데이터 준비
            X = training_data.drop(["rating"], axis=1).values
            y = (training_data["rating"] >= 4.0).astype(float).values

            # 데이터 분할
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # 텐서 변환
            X_train_tensor = torch.FloatTensor(X_train).to(self.device)
            y_train_tensor = torch.FloatTensor(y_train).to(self.device)
            X_test_tensor = torch.FloatTensor(X_test).to(self.device)
            y_test_tensor = torch.FloatTensor(y_test).to(self.device)

            # 모델 생성
            input_size = X_train.shape[1]
            hidden_sizes = [64, 32, 16]
            output_size = 1

            self.model = self.create_model(input_size, hidden_sizes, output_size)
            self.model.to(self.device)

            # 옵티마이저 및 손실 함수
            optimizer = optim.Adam(self.model.parameters(), lr=0.001)
            criterion = nn.BCELoss()

            # 학습
            self.model.train()
            for epoch in range(epochs):
                optimizer.zero_grad()
                outputs = self.model(X_train_tensor)
                loss = criterion(outputs.squeeze(), y_train_tensor)
                loss.backward()
                optimizer.step()

            # 평가
            self.model.eval()
            with torch.no_grad():
                test_outputs = self.model(X_test_tensor)
                test_predictions = (test_outputs.squeeze() > 0.5).float()

                accuracy = (test_predictions == y_test_tensor).float().mean().item()

                # 더 자세한 메트릭 계산
                y_test_np = y_test_tensor.cpu().numpy()
                y_pred_np = test_predictions.cpu().numpy()

                precision = precision_score(y_test_np, y_pred_np, average="weighted")
                recall = recall_score(y_test_np, y_pred_np, average="weighted")
                f1 = f1_score(y_test_np, y_pred_np, average="weighted")

            training_time = (datetime.now() - start_time).total_seconds()

            # 모델 설정
            self.config = ModelConfig(
                model_type=ModelType.DEEP_LEARNING,
                name=self.model_name,
                version="1.0",
                hyperparameters={
                    "input_size": input_size,
                    "hidden_sizes": hidden_sizes,
                    "output_size": output_size,
                    "epochs": epochs,
                    "learning_rate": 0.001,
                },
                feature_columns=list(training_data.columns[:-1]),
                target_column="rating",
                preprocessing_steps=["tensor_conversion"],
            )

            # 메트릭 생성
            metrics = ModelMetrics(
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                training_time=training_time,
                model_size=len(pickle.dumps(self.model.state_dict())),
                timestamp=datetime.now(),
            )

            # 모델 저장
            self.model_manager.save_model(
                self.model.state_dict(), self.model_name, self.config, metrics
            )

            logger.info(f"Deep learning model trained successfully: {self.model_name}")
            return metrics

        except Exception as e:
            logger.error(f"Error training deep learning model: {e}")
            raise


class MLModelIntegration:
    """ML 모델 통합 시스템"""

    def __init__(self, model_dir: str = "models"):
        self.model_manager = ModelManager(model_dir)
        self.recommendation_model = TravelRecommendationModel(self.model_manager)
        self.clustering_model = UserClusteringModel(self.model_manager)
        self.deep_model = DeepLearningModel(self.model_manager)

    def train_all_models(
        self, training_data: dict[str, pd.DataFrame]
    ) -> dict[str, ModelMetrics]:
        """모든 모델 학습"""
        results = {}

        try:
            # 추천 모델 학습
            if "recommendation" in training_data:
                results["recommendation"] = self.recommendation_model.train(
                    training_data["recommendation"]
                )

            # 클러스터링 모델 학습
            if "clustering" in training_data:
                results["clustering"] = self.clustering_model.train(
                    training_data["clustering"]
                )

            # 딥러닝 모델 학습
            if "deep_learning" in training_data:
                results["deep_learning"] = self.deep_model.train(
                    training_data["deep_learning"]
                )

            return results

        except Exception as e:
            logger.error(f"Error training models: {e}")
            return {}

    def get_model_ensemble_prediction(
        self, user_id: str, destination_ids: list[str]
    ) -> list[dict[str, Any]]:
        """앙상블 모델 예측"""
        try:
            # 각 모델의 예측 결과 수집
            predictions = []

            # 추천 모델 예측
            try:
                rec_predictions = self.recommendation_model.predict(
                    user_id, destination_ids
                )
                for pred in rec_predictions:
                    pred["source"] = "recommendation_model"
                predictions.extend(rec_predictions)
            except Exception as e:
                logger.warning(f"Recommendation model prediction failed: {e}")

            # 클러스터링 기반 예측
            try:
                user_features = self._get_user_features(user_id)
                cluster_result = self.clustering_model.predict_cluster(user_features)

                # 클러스터 정보를 활용한 가중치 적용
                cluster_weight = cluster_result.get("confidence", 0.5)

                for pred in predictions:
                    if pred["destination_id"] in destination_ids:
                        pred["cluster_weight"] = cluster_weight
                        pred["cluster_id"] = cluster_result.get("cluster_id", 0)
            except Exception as e:
                logger.warning(f"Clustering model prediction failed: {e}")

            # 앙상블 점수 계산
            final_predictions = []
            for dest_id in destination_ids:
                dest_predictions = [
                    p for p in predictions if p["destination_id"] == dest_id
                ]

                if dest_predictions:
                    # 가중 평균 계산
                    ensemble_score = sum(
                        p["recommendation_score"] * p.get("cluster_weight", 0.5)
                        for p in dest_predictions
                    ) / len(dest_predictions)

                    final_predictions.append(
                        {
                            "destination_id": dest_id,
                            "ensemble_score": ensemble_score,
                            "individual_scores": dest_predictions,
                            "model_count": len(dest_predictions),
                        }
                    )

            # 점수순 정렬
            final_predictions.sort(key=lambda x: x["ensemble_score"], reverse=True)

            return final_predictions

        except Exception as e:
            logger.error(f"Error in ensemble prediction: {e}")
            return []

    def _get_user_features(self, user_id: str) -> dict[str, Any]:
        """사용자 특성 추출"""
        # 실제 구현에서는 데이터베이스에서 사용자 정보 조회
        return {
            "user_id": user_id,
            "created_at": datetime.now() - timedelta(days=365),
            "last_login": datetime.now() - timedelta(days=1),
            "plan_count": 5,
            "avg_rating": 4.2,
            "preferred_season": "spring",
            "preferred_region": "seoul",
        }

    def get_model_performance_report(self) -> dict[str, Any]:
        """모델 성능 보고서"""
        try:
            models = self.model_manager.list_models()

            report = {
                "total_models": len(models),
                "models": [],
                "best_performing": None,
                "recommendations": [],
            }

            best_accuracy = 0
            best_model = None

            for model_info in models:
                if model_info["metrics"]:
                    metrics = model_info["metrics"]

                    model_report = {
                        "name": model_info["name"],
                        "type": (
                            model_info["config"]["model_type"]
                            if model_info["config"]
                            else "unknown"
                        ),
                        "accuracy": metrics["accuracy"],
                        "precision": metrics["precision"],
                        "recall": metrics["recall"],
                        "f1_score": metrics["f1_score"],
                        "training_time": metrics["training_time"],
                        "model_size": metrics["model_size"],
                        "last_updated": metrics["timestamp"],
                    }

                    if metrics["accuracy"] > best_accuracy:
                        best_accuracy = metrics["accuracy"]
                        best_model = model_report

                    report["models"].append(model_report)

            report["best_performing"] = best_model

            # 추천 사항 생성
            if best_model:
                if best_model["accuracy"] < 0.7:
                    report["recommendations"].append(
                        "모델 성능이 낮습니다. 재학습을 고려해주세요."
                    )

                if best_model["f1_score"] < 0.6:
                    report["recommendations"].append(
                        "F1 점수가 낮습니다. 데이터 불균형을 확인해주세요."
                    )

            return report

        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {}


# ML 모델 통합 시스템 싱글톤
ml_integration = None


def get_ml_integration() -> MLModelIntegration:
    """ML 모델 통합 시스템 인스턴스 반환"""
    global ml_integration
    if ml_integration is None:
        ml_integration = MLModelIntegration()
    return ml_integration


logger.info("ML models integration system initialized")
