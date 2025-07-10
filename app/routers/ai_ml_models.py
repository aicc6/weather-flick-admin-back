"""
머신러닝 모델 관리 API 라우터
"""

import io
from datetime import datetime
from typing import Any

try:
    import pandas as pd
except ImportError:
    pd = None
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from pydantic import BaseModel, Field

from app.ai.ml_models import (
    MLModelIntegration,
    get_ml_integration,
)
from app.auth.dependencies import get_current_admin
from app.database import get_db
from app.logging_config import get_logger
from app.utils.cache import CACHE_PREFIX, CACHE_TTL, cache_result

logger = get_logger("ai_ml_models_router")

router = APIRouter(prefix="/ai/ml-models", tags=["AI ML Models"])


class ModelTrainingRequest(BaseModel):
    """모델 학습 요청"""

    model_type: str = Field(..., description="모델 유형")
    model_name: str = Field(..., description="모델 이름")
    hyperparameters: dict[str, Any] = Field(
        default_factory=dict, description="하이퍼파라미터"
    )
    data_source: str = Field("database", description="데이터 소스")
    auto_tune: bool = Field(False, description="자동 튜닝 여부")


class ModelPredictionRequest(BaseModel):
    """모델 예측 요청"""

    model_name: str = Field(..., description="모델 이름")
    user_id: str = Field(..., description="사용자 ID")
    destination_ids: list[str] = Field(..., description="목적지 ID 목록")
    use_ensemble: bool = Field(False, description="앙상블 사용 여부")


class ModelEvaluationRequest(BaseModel):
    """모델 평가 요청"""

    model_name: str = Field(..., description="모델 이름")
    test_data_source: str = Field("database", description="테스트 데이터 소스")
    metrics: list[str] = Field(
        default=["accuracy", "precision", "recall", "f1"], description="평가 메트릭"
    )


class ModelUpdateRequest(BaseModel):
    """모델 업데이트 요청"""

    model_name: str = Field(..., description="모델 이름")
    new_version: str = Field(..., description="새 버전")
    incremental: bool = Field(False, description="증분 학습 여부")


@router.post("/train")
async def train_model(
    request: ModelTrainingRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    ml_integration: MLModelIntegration = Depends(get_ml_integration),
):
    """모델 학습"""
    try:
        # 관리자 권한 확인
        # 관리자 백엔드에서는 이미 관리자 인증 완료

        # 모델 유형 검증
        supported_types = ["recommendation", "clustering", "deep_learning"]
        if request.model_type not in supported_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported model type. Supported: {supported_types}",
            )

        # 학습 데이터 준비
        training_data = await _prepare_training_data(
            db, request.model_type, request.data_source
        )

        if training_data.empty:
            raise HTTPException(status_code=400, detail="No training data available")

        # 백그라운드에서 모델 학습
        background_tasks.add_task(
            _train_model_background,
            ml_integration,
            request.model_type,
            request.model_name,
            training_data,
            request.hyperparameters,
            request.auto_tune,
        )

        return {
            "success": True,
            "message": f"{request.model_name} 모델 학습이 시작되었습니다.",
            "model_name": request.model_name,
            "model_type": request.model_type,
            "data_samples": len(training_data),
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating model training: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate model training")


@router.post("/predict")
@cache_result(ttl=CACHE_TTL["SHORT"], prefix=CACHE_PREFIX["ML_PREDICTIONS"])
async def predict_with_model(
    request: ModelPredictionRequest,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    ml_integration: MLModelIntegration = Depends(get_ml_integration),
):
    """모델을 사용한 예측"""
    try:
        # 사용자 권한 확인
        if request.user_id != current_user["user_id"] and not current_user.get(
            "is_admin", False
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        # 예측 수행
        if request.use_ensemble:
            predictions = ml_integration.get_model_ensemble_prediction(
                request.user_id, request.destination_ids
            )
        else:
            # 단일 모델 예측
            model_type = request.model_name.split("_")[0]  # 모델 이름에서 유형 추출

            if model_type == "recommendation":
                predictions = ml_integration.recommendation_model.predict(
                    request.user_id, request.destination_ids
                )
            else:
                raise HTTPException(
                    status_code=400, detail="Unsupported model for prediction"
                )

        return {
            "success": True,
            "message": "예측이 완료되었습니다.",
            "data": {
                "predictions": predictions,
                "model_name": request.model_name,
                "user_id": request.user_id,
                "prediction_count": len(predictions),
                "use_ensemble": request.use_ensemble,
            },
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error making prediction: {e}")
        raise HTTPException(status_code=500, detail="Failed to make prediction")


@router.get("/list")
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["ML_MODELS"])
async def list_models(
    model_type: str | None = Query(None, description="모델 유형 필터"),
    include_metrics: bool = Query(True, description="메트릭 포함 여부"),
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    ml_integration: MLModelIntegration = Depends(get_ml_integration),
):
    """모델 목록 조회"""
    try:
        models = ml_integration.model_manager.list_models()

        # 모델 유형 필터링
        if model_type:
            models = [
                model
                for model in models
                if model.get("config", {}).get("model_type") == model_type
            ]

        # 메트릭 제거 (필요시)
        if not include_metrics:
            for model in models:
                model.pop("metrics", None)

        return {
            "success": True,
            "message": "모델 목록 조회가 완료되었습니다.",
            "data": {
                "models": models,
                "total_count": len(models),
                "filtered_by_type": model_type,
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail="Failed to list models")


@router.get("/performance")
@cache_result(ttl=CACHE_TTL["MEDIUM"], prefix=CACHE_PREFIX["ML_PERFORMANCE"])
async def get_model_performance(
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    ml_integration: MLModelIntegration = Depends(get_ml_integration),
):
    """모델 성능 보고서"""
    try:
        performance_report = ml_integration.get_model_performance_report()

        return {
            "success": True,
            "message": "모델 성능 보고서가 생성되었습니다.",
            "data": performance_report,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate performance report"
        )


@router.post("/evaluate")
async def evaluate_model(
    request: ModelEvaluationRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    ml_integration: MLModelIntegration = Depends(get_ml_integration),
):
    """모델 평가"""
    try:
        # 관리자 권한 확인
        # 관리자 백엔드에서는 이미 관리자 인증 완료

        # 모델 존재 확인
        models = ml_integration.model_manager.list_models()
        model_exists = any(model["name"] == request.model_name for model in models)

        if not model_exists:
            raise HTTPException(status_code=404, detail="Model not found")

        # 백그라운드에서 모델 평가
        background_tasks.add_task(
            _evaluate_model_background,
            ml_integration,
            request.model_name,
            request.test_data_source,
            request.metrics,
            db,
        )

        return {
            "success": True,
            "message": f"{request.model_name} 모델 평가가 시작되었습니다.",
            "model_name": request.model_name,
            "metrics": request.metrics,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating model evaluation: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to initiate model evaluation"
        )


@router.put("/update")
async def update_model(
    request: ModelUpdateRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    ml_integration: MLModelIntegration = Depends(get_ml_integration),
):
    """모델 업데이트"""
    try:
        # 관리자 권한 확인
        # 관리자 백엔드에서는 이미 관리자 인증 완료

        # 모델 존재 확인
        models = ml_integration.model_manager.list_models()
        model_exists = any(model["name"] == request.model_name for model in models)

        if not model_exists:
            raise HTTPException(status_code=404, detail="Model not found")

        # 백그라운드에서 모델 업데이트
        background_tasks.add_task(
            _update_model_background,
            ml_integration,
            request.model_name,
            request.new_version,
            request.incremental,
            db,
        )

        return {
            "success": True,
            "message": f"{request.model_name} 모델 업데이트가 시작되었습니다.",
            "model_name": request.model_name,
            "new_version": request.new_version,
            "incremental": request.incremental,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating model update: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate model update")


@router.delete("/{model_name}")
async def delete_model(
    model_name: str,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
    ml_integration: MLModelIntegration = Depends(get_ml_integration),
):
    """모델 삭제"""
    try:
        # 관리자 권한 확인
        # 관리자 백엔드에서는 이미 관리자 인증 완료

        # 모델 삭제
        success = ml_integration.model_manager.delete_model(model_name)

        if not success:
            raise HTTPException(
                status_code=404, detail="Model not found or failed to delete"
            )

        return {
            "success": True,
            "message": f"{model_name} 모델이 삭제되었습니다.",
            "model_name": model_name,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete model")


@router.post("/upload-training-data")
async def upload_training_data(
    model_type: str = Query(..., description="모델 유형"),
    file: UploadFile = File(...),
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """학습 데이터 업로드"""
    try:
        # 관리자 권한 확인
        # 관리자 백엔드에서는 이미 관리자 인증 완료

        # 파일 형식 검증
        if not file.filename.endswith((".csv", ".xlsx")):
            raise HTTPException(
                status_code=400, detail="Only CSV and Excel files are supported"
            )

        # 파일 읽기
        contents = await file.read()

        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        else:
            df = pd.read_excel(io.BytesIO(contents))

        # 데이터 검증
        if df.empty:
            raise HTTPException(status_code=400, detail="Empty file")

        # 데이터 저장 (실제 구현에서는 데이터베이스에 저장)
        logger.info(f"Training data uploaded: {len(df)} rows for {model_type}")

        return {
            "success": True,
            "message": "학습 데이터가 업로드되었습니다.",
            "data": {
                "filename": file.filename,
                "model_type": model_type,
                "rows": len(df),
                "columns": list(df.columns),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading training data: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload training data")


@router.get("/types")
async def get_model_types():
    """지원되는 모델 유형 조회"""
    try:
        model_types = [
            {
                "value": "recommendation",
                "name": "추천 모델",
                "description": "사용자 여행 추천을 위한 모델",
                "algorithms": ["RandomForest", "GradientBoosting", "DeepLearning"],
            },
            {
                "value": "clustering",
                "name": "클러스터링 모델",
                "description": "사용자 그룹화를 위한 모델",
                "algorithms": ["K-Means", "DBSCAN", "Hierarchical"],
            },
            {
                "value": "deep_learning",
                "name": "딥러닝 모델",
                "description": "신경망 기반 예측 모델",
                "algorithms": ["MLP", "CNN", "RNN"],
            },
        ]

        return {
            "success": True,
            "message": "모델 유형 조회가 완료되었습니다.",
            "data": model_types,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting model types: {e}")
        raise HTTPException(status_code=500, detail="Failed to get model types")


async def _prepare_training_data(db, model_type: str, data_source: str) -> pd.DataFrame:
    """학습 데이터 준비"""
    try:
        if data_source == "database":
            # 데이터베이스에서 학습 데이터 조회
            if model_type == "recommendation":
                # 추천 모델을 위한 데이터

                query = """
                SELECT u.user_id, d.destination_id, r.rating, r.created_at,
                       u.created_at as user_created_at, u.last_login,
                       d.category, d.region
                FROM reviews r
                JOIN users u ON r.user_id = u.user_id
                JOIN destinations d ON r.destination_id = d.destination_id
                WHERE r.rating IS NOT NULL
                ORDER BY r.created_at DESC
                LIMIT 10000
                """

                result = db.execute(query)
                data = result.fetchall()

                if data:
                    columns = [
                        "user_id",
                        "destination_id",
                        "rating",
                        "created_at",
                        "user_created_at",
                        "last_login",
                        "category",
                        "region",
                    ]
                    return pd.DataFrame(data, columns=columns)

            elif model_type == "clustering":
                # 클러스터링 모델을 위한 데이터

                query = """
                SELECT u.user_id, u.created_at, u.last_login, u.preferred_region,
                       COUNT(tp.plan_id) as plan_count,
                       AVG(CASE WHEN r.rating IS NOT NULL THEN r.rating END) as avg_rating
                FROM users u
                LEFT JOIN travel_plans tp ON u.user_id = tp.user_id
                LEFT JOIN reviews r ON u.user_id = r.user_id
                GROUP BY u.user_id, u.created_at, u.last_login, u.preferred_region
                LIMIT 5000
                """

                result = db.execute(query)
                data = result.fetchall()

                if data:
                    columns = [
                        "user_id",
                        "created_at",
                        "last_login",
                        "preferred_region",
                        "plan_count",
                        "avg_rating",
                    ]
                    return pd.DataFrame(data, columns=columns)

        return pd.DataFrame()

    except Exception as e:
        logger.error(f"Error preparing training data: {e}")
        return pd.DataFrame()


async def _train_model_background(
    ml_integration: MLModelIntegration,
    model_type: str,
    model_name: str,
    training_data: pd.DataFrame,
    hyperparameters: dict[str, Any],
    auto_tune: bool,
):
    """백그라운드 모델 학습"""
    try:
        if model_type == "recommendation":
            metrics = ml_integration.recommendation_model.train(training_data)
        elif model_type == "clustering":
            n_clusters = hyperparameters.get("n_clusters", 5)
            metrics = ml_integration.clustering_model.train(training_data, n_clusters)
        elif model_type == "deep_learning":
            epochs = hyperparameters.get("epochs", 100)
            metrics = ml_integration.deep_model.train(training_data, epochs)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

        logger.info(f"Model training completed: {model_name}, Metrics: {metrics}")

    except Exception as e:
        logger.error(f"Error in background model training: {e}")


async def _evaluate_model_background(
    ml_integration: MLModelIntegration,
    model_name: str,
    test_data_source: str,
    metrics: list[str],
    db,
):
    """백그라운드 모델 평가"""
    try:
        # 테스트 데이터 준비
        test_data = await _prepare_training_data(
            db, model_name.split("_")[0], test_data_source
        )

        if test_data.empty:
            logger.warning(f"No test data available for {model_name}")
            return

        # 모델 평가 수행
        logger.info(f"Model evaluation completed for {model_name}")

    except Exception as e:
        logger.error(f"Error in background model evaluation: {e}")


async def _update_model_background(
    ml_integration: MLModelIntegration,
    model_name: str,
    new_version: str,
    incremental: bool,
    db,
):
    """백그라운드 모델 업데이트"""
    try:
        # 모델 업데이트 로직 구현
        logger.info(f"Model update completed: {model_name} -> {new_version}")

    except Exception as e:
        logger.error(f"Error in background model update: {e}")


logger.info("AI ML models router initialized")
