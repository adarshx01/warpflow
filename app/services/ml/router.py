"""FastAPI router and tool functions for ML Trainer service."""

import logging
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, MLDataset, MLModel
from app.auth.utils import get_current_user
from app.services.storage import upload_file, download_file, delete_file
from app.services.storage.s3_storage import (
    decode_base64_content,
    upload_file_for_user,
    download_file_for_user,
)
from app.services.ml.schemas import (
    UploadDatasetRequest,
    TrainModelRequest,
    SupervisedTrainRequest,
    UnsupervisedTrainRequest,
    PredictRequest,
    PreprocessingConfig,
    ExecuteRequest,
    DatasetResponse,
    DatasetListResponse,
    DatasetAnalysisResponse,
    DatasetPreviewResponse,
    ModelResponse,
    ModelListResponse,
    TrainModelResponse,
    PredictResponse,
    AlgorithmListResponse,
    SupervisedAlgorithmsResponse,
    UnsupervisedAlgorithmsResponse,
)
from app.services.ml.trainer import (
    load_dataset,
    get_dataset_info,
    analyze_dataset,
    preview_dataset,
    train_model as train_model_core,
    train_supervised_model,
    train_unsupervised_model,
    serialize_model,
    deserialize_model,
    predict as predict_core,
)
from app.services.ml.algorithms import (
    list_all_algorithms,
    get_supervised_algorithms,
    get_unsupervised_algorithms,
    get_algorithms_by_type,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ml", tags=["ML"])


# ─────────────────────────────────────────────────────────────────────────────
# Algorithm Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/algorithms", response_model=AlgorithmListResponse)
async def get_algorithms():
    """List all available ML algorithms."""
    return {"algorithms": list_all_algorithms()}


@router.get("/algorithms/supervised", response_model=SupervisedAlgorithmsResponse)
async def get_supervised_algorithms_endpoint():
    """List supervised learning algorithms (classification + regression)."""
    classification = [
        alg for alg in get_supervised_algorithms() if alg["type"] == "classification"
    ]
    regression = [
        alg for alg in get_supervised_algorithms() if alg["type"] == "regression"
    ]
    return {"classification": classification, "regression": regression}


@router.get("/algorithms/unsupervised", response_model=UnsupervisedAlgorithmsResponse)
async def get_unsupervised_algorithms_endpoint():
    """List unsupervised learning algorithms (clustering + dimensionality reduction)."""
    clustering = [
        alg for alg in get_unsupervised_algorithms() if alg["type"] == "clustering"
    ]
    dim_reduction = [
        alg for alg in get_unsupervised_algorithms() if alg["type"] == "dimensionality_reduction"
    ]
    return {"clustering": clustering, "dimensionality_reduction": dim_reduction}


# ─────────────────────────────────────────────────────────────────────────────
# Dataset Endpoints (Data Preparation Node)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/datasets/upload", response_model=DatasetResponse)
async def upload_dataset_endpoint(
    request: UploadDatasetRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a dataset file."""
    result = await ml_upload_dataset(str(user.id), request.model_dump(), db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/datasets", response_model=DatasetListResponse)
async def list_datasets_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List user's datasets."""
    result = await ml_list_datasets(str(user.id), {}, db)
    return result


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset_endpoint(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get dataset details."""
    result = await _get_dataset(db, dataset_id, user.id)
    return result


@router.get("/datasets/{dataset_id}/analyze", response_model=DatasetAnalysisResponse)
async def analyze_dataset_endpoint(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Analyze a dataset - auto-categorize columns, compute statistics."""
    result = await ml_analyze_dataset(str(user.id), {"dataset_id": str(dataset_id)}, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/datasets/{dataset_id}/preview", response_model=DatasetPreviewResponse)
async def preview_dataset_endpoint(
    dataset_id: UUID,
    n_rows: int = 10,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a preview of the dataset."""
    result = await ml_preview_dataset(
        str(user.id), {"dataset_id": str(dataset_id), "n_rows": n_rows}, db
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/datasets/{dataset_id}")
async def delete_dataset_endpoint(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a dataset."""
    dataset = await _get_dataset_model(db, dataset_id, user.id)
    delete_file(dataset.s3_path)
    await db.delete(dataset)
    await db.commit()
    return {"success": True, "dataset_id": str(dataset_id)}


# ─────────────────────────────────────────────────────────────────────────────
# Supervised Training Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/supervised/train", response_model=TrainModelResponse)
async def train_supervised_endpoint(
    request: SupervisedTrainRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Train a supervised learning model (classification or regression)."""
    result = await ml_train_supervised(str(user.id), request.model_dump(), db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Unsupervised Training Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/unsupervised/train", response_model=TrainModelResponse)
async def train_unsupervised_endpoint(
    request: UnsupervisedTrainRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Train an unsupervised learning model (clustering or dimensionality reduction)."""
    result = await ml_train_unsupervised(str(user.id), request.model_dump(), db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Model Inference Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/models", response_model=ModelListResponse)
async def list_models_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List user's trained models."""
    result = await ml_list_models(str(user.id), {}, db)
    return result


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model_endpoint(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get model details."""
    result = await ml_get_model_info(str(user.id), {"model_id": str(model_id)}, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/models/{model_id}")
async def delete_model_endpoint(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a model."""
    model = await _get_model_model(db, model_id, user.id)
    delete_file(model.s3_path)
    await db.delete(model)
    await db.commit()
    return {"success": True, "model_id": str(model_id)}


@router.post("/models/{model_id}/predict", response_model=PredictResponse)
async def predict_endpoint(
    model_id: UUID,
    request: PredictRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run predictions using a trained model."""
    params = request.model_dump()
    params["model_id"] = str(model_id)
    result = await ml_predict(str(user.id), params, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Legacy Endpoints (backward compatibility)
# ─────────────────────────────────────────────────────────────────────────────


# Legacy router for old /api/ml-trainer paths
legacy_router = APIRouter(prefix="/api/ml-trainer", tags=["ML Trainer (Legacy)"])


@legacy_router.get("/algorithms", response_model=AlgorithmListResponse)
async def legacy_get_algorithms():
    """List all available ML algorithms (legacy)."""
    return {"algorithms": list_all_algorithms()}


@legacy_router.post("/datasets/upload", response_model=DatasetResponse)
async def legacy_upload_dataset(
    request: UploadDatasetRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a dataset file (legacy)."""
    result = await ml_upload_dataset(str(user.id), request.model_dump(), db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@legacy_router.get("/datasets", response_model=DatasetListResponse)
async def legacy_list_datasets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List user's datasets (legacy)."""
    result = await ml_list_datasets(str(user.id), {}, db)
    return result


@legacy_router.post("/train", response_model=TrainModelResponse)
async def legacy_train_model(
    request: TrainModelRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Train a model (legacy)."""
    result = await ml_train_model(str(user.id), request.model_dump(), db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@legacy_router.get("/models", response_model=ModelListResponse)
async def legacy_list_models(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List user's trained models (legacy)."""
    result = await ml_list_models(str(user.id), {}, db)
    return result


@legacy_router.post("/predict", response_model=PredictResponse)
async def legacy_predict(
    request: PredictRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run predictions (legacy)."""
    result = await ml_predict(str(user.id), request.model_dump(), db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@legacy_router.post("/execute")
async def legacy_execute(
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Execute an ML operation (legacy)."""
    operations = {
        "upload_dataset": ml_upload_dataset,
        "analyze_dataset": ml_analyze_dataset,
        "preprocess_dataset": ml_preview_dataset,
        "get_dataset_preview": ml_preview_dataset,
        "train_model": ml_train_model,
        "train_supervised": ml_train_supervised,
        "train_unsupervised": ml_train_unsupervised,
        "predict": ml_predict,
        "get_model_info": ml_get_model_info,
        "list_models": ml_list_models,
        "list_datasets": ml_list_datasets,
    }

    op_fn = operations.get(request.operation)
    if not op_fn:
        raise HTTPException(status_code=400, detail=f"Unknown operation: {request.operation}")

    result = await op_fn(str(user.id), request.params, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Tool Functions (for AI Agent integration)
# Signature: async def fn(user_id: str, params: dict, db: AsyncSession = None) -> dict
# ─────────────────────────────────────────────────────────────────────────────


async def ml_upload_dataset(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """Upload a CSV or JSON dataset for ML training."""
    try:
        file_content = decode_base64_content(params["file_content"])
        filename = params["filename"]
        file_type = params["file_type"]

        # Load and validate dataset
        df = load_dataset(file_content, file_type)
        info = get_dataset_info(df)

        # Also perform analysis
        analysis = analyze_dataset(df)

        # Upload to S3 using user's credentials if available
        dataset_id = uuid4()
        s3_path = await upload_file_for_user(
            db=db,
            user_id=UUID(user_id),
            category="datasets",
            file_id=dataset_id,
            content=file_content,
            extension=file_type,
            content_type="text/csv" if file_type == "csv" else "application/json",
        )

        # Save metadata to database
        dataset = MLDataset(
            id=dataset_id,
            owner_id=UUID(user_id),
            name=filename,
            s3_path=s3_path,
            file_type=file_type,
            row_count=info["row_count"],
            columns=info["columns"],
        )
        db.add(dataset)
        await db.commit()
        await db.refresh(dataset)

        return {
            "id": str(dataset.id),
            "name": dataset.name,
            "file_type": dataset.file_type,
            "row_count": dataset.row_count,
            "columns": dataset.columns,
            "analysis": analysis,
            "created_at": dataset.created_at.isoformat(),
            "preview": info["preview"],
        }

    except Exception as e:
        logger.error("Failed to upload dataset: %s", e)
        return {"error": str(e)}


async def ml_analyze_dataset(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """Analyze a dataset - auto-categorize columns, compute statistics."""
    try:
        dataset_id = UUID(str(params["dataset_id"]))

        # Load dataset
        dataset = await _get_dataset_model(db, dataset_id, UUID(user_id))
        content = await download_file_for_user(db, UUID(user_id), dataset.s3_path)
        df = load_dataset(content, dataset.file_type)

        # Analyze
        analysis = analyze_dataset(df)
        return analysis

    except Exception as e:
        logger.error("Failed to analyze dataset: %s", e)
        return {"error": str(e)}


async def ml_preview_dataset(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """Get a preview of the dataset."""
    try:
        dataset_id = UUID(str(params["dataset_id"]))
        n_rows = params.get("n_rows", 10)

        # Load dataset
        dataset = await _get_dataset_model(db, dataset_id, UUID(user_id))
        content = await download_file_for_user(db, UUID(user_id), dataset.s3_path)
        df = load_dataset(content, dataset.file_type)

        # Preview
        preview = preview_dataset(df, n_rows)
        return preview

    except Exception as e:
        logger.error("Failed to preview dataset: %s", e)
        return {"error": str(e)}


async def ml_train_supervised(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """Train a supervised learning model (classification or regression)."""
    try:
        dataset_id = UUID(str(params["dataset_id"]))
        algorithm = params["algorithm"]
        target_column = params["target_column"]
        model_name = params.get("model_name", f"{algorithm}_model")
        feature_columns = params.get("feature_columns")
        hyperparameters = params.get("hyperparameters")

        # Get preprocessing config
        preproc = params.get("preprocessing", {})
        normalization = preproc.get("normalization", "standard")
        handle_missing = preproc.get("handle_missing", "zero")
        train_size = preproc.get("train_size", 0.7)
        val_size = preproc.get("val_size", 0.15)
        test_size = preproc.get("test_size", 0.15)

        # Load dataset
        dataset = await _get_dataset_model(db, dataset_id, UUID(user_id))
        content = await download_file_for_user(db, UUID(user_id), dataset.s3_path)
        df = load_dataset(content, dataset.file_type)

        # Train model
        model, metrics, feature_names, scaler = train_supervised_model(
            df=df,
            algorithm=algorithm,
            target_column=target_column,
            feature_columns=feature_columns,
            hyperparameters=hyperparameters,
            normalization=normalization,
            handle_missing=handle_missing,
            train_size=train_size,
            val_size=val_size,
            test_size=test_size,
        )

        # Determine model type from algorithm
        from app.services.ml.algorithms import get_algorithm_info
        algo_info = get_algorithm_info(algorithm)
        model_type = algo_info["type"]

        # Serialize and upload model
        model_id = uuid4()
        model_bytes = serialize_model(model, scaler)
        s3_path = await upload_file_for_user(
            db=db,
            user_id=UUID(user_id),
            category="models",
            file_id=model_id,
            content=model_bytes,
            extension="joblib",
            content_type="application/octet-stream",
        )

        # Save metadata
        ml_model = MLModel(
            id=model_id,
            owner_id=UUID(user_id),
            dataset_id=dataset_id,
            name=model_name,
            algorithm=algorithm,
            model_type=model_type,
            model_category="supervised",
            s3_path=s3_path,
            metrics=metrics,
            feature_names=feature_names,
            hyperparameters=hyperparameters,
        )
        db.add(ml_model)
        await db.commit()
        await db.refresh(ml_model)

        return {
            "model_id": str(ml_model.id),
            "name": ml_model.name,
            "algorithm": ml_model.algorithm,
            "model_type": ml_model.model_type,
            "model_category": "supervised",
            "metrics": metrics,
            "feature_names": feature_names,
            "split_info": metrics.get("split_info"),
            "created_at": ml_model.created_at.isoformat(),
        }

    except Exception as e:
        logger.error("Failed to train supervised model: %s", e)
        return {"error": str(e)}


async def ml_train_unsupervised(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """Train an unsupervised learning model (clustering or dimensionality reduction)."""
    try:
        dataset_id = UUID(str(params["dataset_id"]))
        algorithm = params["algorithm"]
        model_name = params.get("model_name", f"{algorithm}_model")
        feature_columns = params.get("feature_columns")
        hyperparameters = params.get("hyperparameters")

        # Get preprocessing config
        preproc = params.get("preprocessing", {})
        normalization = preproc.get("normalization", "standard")
        handle_missing = preproc.get("handle_missing", "zero")

        # Load dataset
        dataset = await _get_dataset_model(db, dataset_id, UUID(user_id))
        content = await download_file_for_user(db, UUID(user_id), dataset.s3_path)
        df = load_dataset(content, dataset.file_type)

        # Train model
        model, metrics, feature_names, scaler = train_unsupervised_model(
            df=df,
            algorithm=algorithm,
            feature_columns=feature_columns,
            hyperparameters=hyperparameters,
            normalization=normalization,
            handle_missing=handle_missing,
        )

        # Determine model type from algorithm
        from app.services.ml.algorithms import get_algorithm_info
        algo_info = get_algorithm_info(algorithm)
        model_type = algo_info["type"]

        # Serialize and upload model
        model_id = uuid4()
        model_bytes = serialize_model(model, scaler)
        s3_path = await upload_file_for_user(
            db=db,
            user_id=UUID(user_id),
            category="models",
            file_id=model_id,
            content=model_bytes,
            extension="joblib",
            content_type="application/octet-stream",
        )

        # Save metadata
        ml_model = MLModel(
            id=model_id,
            owner_id=UUID(user_id),
            dataset_id=dataset_id,
            name=model_name,
            algorithm=algorithm,
            model_type=model_type,
            model_category="unsupervised",
            s3_path=s3_path,
            metrics=metrics,
            feature_names=feature_names,
            hyperparameters=hyperparameters,
        )
        db.add(ml_model)
        await db.commit()
        await db.refresh(ml_model)

        return {
            "model_id": str(ml_model.id),
            "name": ml_model.name,
            "algorithm": ml_model.algorithm,
            "model_type": ml_model.model_type,
            "model_category": "unsupervised",
            "metrics": metrics,
            "feature_names": feature_names,
            "created_at": ml_model.created_at.isoformat(),
        }

    except Exception as e:
        logger.error("Failed to train unsupervised model: %s", e)
        return {"error": str(e)}


async def ml_train_model(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """Train a machine learning model on a dataset (legacy function)."""
    try:
        dataset_id = UUID(str(params["dataset_id"]))
        algorithm = params["algorithm"]
        model_type = params["model_type"]
        model_name = params.get("name", f"{algorithm}_{model_type}")
        target_column = params.get("target_column")
        feature_columns = params.get("feature_columns")
        hyperparameters = params.get("hyperparameters")
        test_size = params.get("test_size", 0.2)

        # Validate supervised learning has target
        if model_type in ["classification", "regression"] and not target_column:
            return {"error": f"target_column is required for {model_type}"}

        # Load dataset
        dataset = await _get_dataset_model(db, dataset_id, UUID(user_id))
        content = await download_file_for_user(db, UUID(user_id), dataset.s3_path)
        df = load_dataset(content, dataset.file_type)

        # Train model
        model, metrics, feature_names = train_model_core(
            df=df,
            algorithm=algorithm,
            model_type=model_type,
            target_column=target_column,
            feature_columns=feature_columns,
            hyperparameters=hyperparameters,
            test_size=test_size,
        )

        # Serialize and upload model
        model_id = uuid4()
        model_bytes = serialize_model(model)
        s3_path = await upload_file_for_user(
            db=db,
            user_id=UUID(user_id),
            category="models",
            file_id=model_id,
            content=model_bytes,
            extension="joblib",
            content_type="application/octet-stream",
        )

        # Determine category
        model_category = "supervised" if model_type in ["classification", "regression"] else "unsupervised"

        # Save metadata
        ml_model = MLModel(
            id=model_id,
            owner_id=UUID(user_id),
            dataset_id=dataset_id,
            name=model_name,
            algorithm=algorithm,
            model_type=model_type,
            model_category=model_category,
            s3_path=s3_path,
            metrics=metrics,
            feature_names=feature_names,
            hyperparameters=hyperparameters,
        )
        db.add(ml_model)
        await db.commit()
        await db.refresh(ml_model)

        return {
            "model_id": str(ml_model.id),
            "name": ml_model.name,
            "algorithm": ml_model.algorithm,
            "model_type": ml_model.model_type,
            "model_category": model_category,
            "metrics": ml_model.metrics,
            "created_at": ml_model.created_at.isoformat(),
        }

    except Exception as e:
        logger.error("Failed to train model: %s", e)
        return {"error": str(e)}


async def ml_predict(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """Run predictions using a trained model."""
    try:
        model_id = UUID(str(params["model_id"]))
        input_data = params["input_data"]

        # Load model metadata and file
        ml_model = await _get_model_model(db, model_id, UUID(user_id))
        model_bytes = await download_file_for_user(db, UUID(user_id), ml_model.s3_path)
        model, scaler = deserialize_model(model_bytes)

        # Run prediction
        result = predict_core(model, input_data, ml_model.feature_names or [], scaler)
        return result

    except Exception as e:
        logger.error("Failed to predict: %s", e)
        return {"error": str(e)}


async def ml_get_model_info(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """Get information and metrics about a trained model."""
    try:
        model_id = UUID(str(params["model_id"]))
        ml_model = await _get_model_model(db, model_id, UUID(user_id))

        return {
            "id": str(ml_model.id),
            "name": ml_model.name,
            "algorithm": ml_model.algorithm,
            "model_type": ml_model.model_type,
            "model_category": getattr(ml_model, "model_category", None),
            "metrics": ml_model.metrics,
            "feature_names": ml_model.feature_names,
            "hyperparameters": ml_model.hyperparameters,
            "dataset_id": str(ml_model.dataset_id) if ml_model.dataset_id else None,
            "created_at": ml_model.created_at.isoformat(),
        }

    except Exception as e:
        logger.error("Failed to get model info: %s", e)
        return {"error": str(e)}


async def ml_list_models(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """List user's trained models."""
    try:
        stmt = select(MLModel).where(MLModel.owner_id == UUID(user_id)).order_by(MLModel.created_at.desc())
        result = await db.execute(stmt)
        models = result.scalars().all()

        return {
            "models": [
                {
                    "id": str(m.id),
                    "name": m.name,
                    "algorithm": m.algorithm,
                    "model_type": m.model_type,
                    "model_category": getattr(m, "model_category", None),
                    "metrics": m.metrics,
                    "feature_names": m.feature_names,
                    "hyperparameters": m.hyperparameters,
                    "dataset_id": str(m.dataset_id) if m.dataset_id else None,
                    "created_at": m.created_at.isoformat(),
                }
                for m in models
            ]
        }

    except Exception as e:
        logger.error("Failed to list models: %s", e)
        return {"error": str(e)}


async def ml_list_datasets(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """List user's uploaded datasets."""
    try:
        stmt = select(MLDataset).where(MLDataset.owner_id == UUID(user_id)).order_by(MLDataset.created_at.desc())
        result = await db.execute(stmt)
        datasets = result.scalars().all()

        return {
            "datasets": [
                {
                    "id": str(d.id),
                    "name": d.name,
                    "file_type": d.file_type,
                    "row_count": d.row_count,
                    "columns": d.columns,
                    "created_at": d.created_at.isoformat(),
                }
                for d in datasets
            ]
        }

    except Exception as e:
        logger.error("Failed to list datasets: %s", e)
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────


async def _get_dataset_model(db: AsyncSession, dataset_id: UUID, user_id: UUID) -> MLDataset:
    """Get dataset model, raising 404 if not found or not owned by user."""
    stmt = select(MLDataset).where(
        MLDataset.id == dataset_id,
        MLDataset.owner_id == user_id,
    )
    result = await db.execute(stmt)
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


async def _get_model_model(db: AsyncSession, model_id: UUID, user_id: UUID) -> MLModel:
    """Get model, raising 404 if not found or not owned by user."""
    stmt = select(MLModel).where(
        MLModel.id == model_id,
        MLModel.owner_id == user_id,
    )
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


async def _get_dataset(db: AsyncSession, dataset_id: UUID, user_id: UUID) -> dict:
    """Get dataset as response dict."""
    dataset = await _get_dataset_model(db, dataset_id, user_id)
    return {
        "id": str(dataset.id),
        "name": dataset.name,
        "file_type": dataset.file_type,
        "row_count": dataset.row_count,
        "columns": dataset.columns,
        "created_at": dataset.created_at.isoformat(),
    }
