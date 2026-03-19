"""Pydantic schemas for ML Trainer service."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Column and Dataset Analysis Schemas
# ============================================================================

class ColumnStats(BaseModel):
    """Statistics for a numeric column."""
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None


class TopValue(BaseModel):
    """Top value for a categorical column."""
    value: str
    count: int


class ColumnInfo(BaseModel):
    """Information about a single column."""
    name: str
    dtype: str
    column_type: Literal["numeric", "categorical"]
    null_count: int
    null_percentage: float
    unique_count: int
    stats: ColumnStats | None = None
    top_values: list[TopValue] | None = None


class DatasetAnalysisResponse(BaseModel):
    """Response for dataset analysis."""
    row_count: int
    column_count: int
    columns: list[ColumnInfo]
    numeric_columns: list[str]
    categorical_columns: list[str]
    memory_usage_mb: float


# ============================================================================
# Preprocessing Configuration Schemas
# ============================================================================

class PreprocessingConfig(BaseModel):
    """Configuration for data preprocessing."""
    normalization: Literal["standard", "minmax", "robust", "none"] = Field(
        default="standard", description="Normalization method"
    )
    handle_missing: Literal["drop", "mean", "median", "mode", "zero"] = Field(
        default="zero", description="Missing value handling strategy"
    )
    train_size: float = Field(default=0.7, ge=0.1, le=0.9, description="Training set proportion")
    val_size: float = Field(default=0.15, ge=0.0, le=0.5, description="Validation set proportion")
    test_size: float = Field(default=0.15, ge=0.05, le=0.5, description="Test set proportion")


class SplitInfo(BaseModel):
    """Information about data splits."""
    train_samples: int
    val_samples: int
    test_samples: int


class PreprocessingResponse(BaseModel):
    """Response from preprocessing operation."""
    dataset_id: UUID
    split_info: SplitInfo
    normalization_method: str
    missing_value_strategy: str
    feature_columns: list[str]
    target_column: str | None = None


# ============================================================================
# Dataset Upload and Retrieval Schemas
# ============================================================================

class UploadDatasetRequest(BaseModel):
    """Request to upload a dataset."""
    file_content: str = Field(..., description="Base64-encoded file content")
    filename: str = Field(..., description="Original filename")
    file_type: Literal["csv", "json"] = Field(..., description="File format")


class DatasetPreviewResponse(BaseModel):
    """Response with dataset preview."""
    columns: list[str]
    dtypes: dict[str, str]
    data: list[dict[str, Any]]
    total_rows: int
    preview_rows: int


class DatasetResponse(BaseModel):
    """Response for a single dataset."""
    id: UUID
    name: str
    file_type: str
    row_count: int
    columns: list[ColumnInfo] | None = None
    analysis: DatasetAnalysisResponse | None = None
    preview: DatasetPreviewResponse | None = None
    created_at: str


class DatasetListResponse(BaseModel):
    """Response for dataset list."""
    datasets: list[DatasetResponse]


# ============================================================================
# Training Request Schemas
# ============================================================================

class SupervisedTrainRequest(BaseModel):
    """Request to train a supervised model."""
    dataset_id: UUID = Field(..., description="ID of the dataset to train on")
    algorithm: str = Field(..., description="Algorithm name (e.g., 'random_forest_classifier')")
    target_column: str = Field(..., description="Target column for prediction")
    model_name: str = Field(default="", description="Optional model name")
    feature_columns: list[str] | None = Field(
        None, description="Feature columns (None = auto-select all except target)"
    )
    preprocessing: PreprocessingConfig = Field(
        default_factory=PreprocessingConfig, description="Preprocessing configuration"
    )
    hyperparameters: dict[str, Any] | None = Field(
        None, description="Algorithm hyperparameters"
    )


class UnsupervisedTrainRequest(BaseModel):
    """Request to train an unsupervised model."""
    dataset_id: UUID = Field(..., description="ID of the dataset to train on")
    algorithm: str = Field(..., description="Algorithm name (e.g., 'kmeans', 'pca')")
    model_name: str = Field(default="", description="Optional model name")
    feature_columns: list[str] | None = Field(
        None, description="Feature columns (None = auto-select all)"
    )
    preprocessing: PreprocessingConfig = Field(
        default_factory=PreprocessingConfig, description="Preprocessing configuration"
    )
    hyperparameters: dict[str, Any] | None = Field(
        None, description="Algorithm hyperparameters"
    )


# Legacy support for old API
class TrainModelRequest(BaseModel):
    """Legacy request for training (backward compatibility)."""
    dataset_id: UUID = Field(..., description="ID of the dataset to train on")
    algorithm: str = Field(..., description="Algorithm name")
    model_type: Literal["classification", "regression", "clustering", "dimensionality_reduction"] = Field(
        ..., description="Type of ML task"
    )
    name: str = Field(default="", description="Optional model name")
    target_column: str | None = Field(
        None, description="Target column for supervised learning"
    )
    feature_columns: list[str] | None = Field(
        None, description="Feature columns to use (optional)"
    )
    hyperparameters: dict[str, Any] | None = Field(
        None, description="Algorithm hyperparameters"
    )
    test_size: float = Field(default=0.2, description="Test split ratio")


# ============================================================================
# Training Response Schemas
# ============================================================================

class TrainingMetrics(BaseModel):
    """Metrics from model training."""
    # Classification metrics
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None

    # Regression metrics
    mse: float | None = None
    rmse: float | None = None
    mae: float | None = None
    r2: float | None = None

    # Clustering metrics
    silhouette_score: float | None = None
    n_clusters: int | None = None
    cluster_sizes: list[int] | None = None

    # Dimensionality reduction
    explained_variance_ratio: list[float] | None = None
    total_explained_variance: float | None = None
    n_components: int | None = None


class TrainModelResponse(BaseModel):
    """Response from model training."""
    model_id: UUID
    name: str
    algorithm: str
    model_type: str
    model_category: Literal["supervised", "unsupervised"]
    metrics: TrainingMetrics
    feature_names: list[str]
    split_info: SplitInfo | None = None
    created_at: str


class ModelResponse(BaseModel):
    """Response for a single model."""
    id: UUID
    name: str
    algorithm: str
    model_type: str
    model_category: str | None = None
    metrics: dict[str, Any] | None
    feature_names: list[str] | None
    hyperparameters: dict[str, Any] | None
    dataset_id: UUID | None
    created_at: str


class ModelListResponse(BaseModel):
    """Response for model list."""
    models: list[ModelResponse]


# ============================================================================
# Prediction/Inference Schemas
# ============================================================================

class PredictRequest(BaseModel):
    """Request to run model prediction."""
    model_id: UUID = Field(..., description="ID of the trained model")
    input_data: list[dict[str, Any]] = Field(..., description="Input data as list of objects")


class PredictResponse(BaseModel):
    """Response from model prediction."""
    predictions: list[Any]
    probabilities: list[list[float]] | None = None
    transformed: list[list[float]] | None = None
    cluster_labels: list[int] | None = None


# ============================================================================
# Algorithm Information Schemas
# ============================================================================

class AlgorithmParam(BaseModel):
    """Information about an algorithm parameter."""
    type: str
    default: Any
    min: float | None = None
    max: float | None = None
    options: list[str] | None = None


class AlgorithmInfo(BaseModel):
    """Information about an algorithm."""
    name: str
    type: str
    params: dict[str, AlgorithmParam]


class AlgorithmListResponse(BaseModel):
    """Response for algorithm list."""
    algorithms: list[AlgorithmInfo]


class SupervisedAlgorithmsResponse(BaseModel):
    """Response for supervised algorithms."""
    classification: list[AlgorithmInfo]
    regression: list[AlgorithmInfo]


class UnsupervisedAlgorithmsResponse(BaseModel):
    """Response for unsupervised algorithms."""
    clustering: list[AlgorithmInfo]
    dimensionality_reduction: list[AlgorithmInfo]


# ============================================================================
# Execute Request (for node execution)
# ============================================================================

class ExecuteRequest(BaseModel):
    """Request to execute an ML operation."""
    operation: Literal[
        "upload_dataset",
        "analyze_dataset",
        "preprocess_dataset",
        "get_dataset_preview",
        "train_supervised",
        "train_unsupervised",
        "predict",
        "get_model_info",
        "list_models",
        "list_datasets",
    ]
    params: dict[str, Any]
