"""ML Model training and inference logic."""

import io
import logging
from typing import Any, Literal

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    mean_squared_error,
    mean_absolute_error,
    r2_score,
    silhouette_score,
)

from app.services.ml.algorithms import (
    ALGORITHMS,
    get_algorithm_info,
    is_supervised,
    is_unsupervised,
    SUPERVISED_TYPES,
    UNSUPERVISED_TYPES,
)
from app.services.ml.preprocessing import (
    analyze_dataset as analyze_df,
    preprocess_dataframe,
    get_data_preview,
    handle_missing_values,
    encode_categorical_columns,
    apply_normalization,
    create_train_test_val_split,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Dataset Loading and Analysis
# ============================================================================

def load_dataset(content: bytes, file_type: str) -> pd.DataFrame:
    """Load a dataset from bytes content."""
    if file_type == "csv":
        return pd.read_csv(io.BytesIO(content))
    elif file_type == "json":
        return pd.read_json(io.BytesIO(content))
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def get_dataset_info(df: pd.DataFrame) -> dict:
    """Extract metadata from a DataFrame (legacy function for compatibility)."""
    columns = []
    for col in df.columns:
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "non_null_count": int(df[col].notna().sum()),
            "unique_count": int(df[col].nunique()),
        }
        if df[col].dtype in ["int64", "float64"]:
            col_info["min"] = float(df[col].min()) if not pd.isna(df[col].min()) else None
            col_info["max"] = float(df[col].max()) if not pd.isna(df[col].max()) else None
        columns.append(col_info)

    return {
        "row_count": len(df),
        "columns": columns,
        "preview": df.head(5).to_dict(orient="records"),
    }


def analyze_dataset(df: pd.DataFrame) -> dict:
    """
    Analyze a dataset and return comprehensive information.
    This is the main entry point for dataset analysis.
    """
    return analyze_df(df)


def preview_dataset(df: pd.DataFrame, n_rows: int = 10) -> dict:
    """Get a preview of the dataset."""
    return get_data_preview(df, n_rows)


# ============================================================================
# Supervised Training
# ============================================================================

def train_supervised_model(
    df: pd.DataFrame,
    algorithm: str,
    target_column: str,
    feature_columns: list[str] | None = None,
    hyperparameters: dict | None = None,
    normalization: Literal["standard", "minmax", "robust", "none"] = "standard",
    handle_missing: Literal["drop", "mean", "median", "mode", "zero"] = "zero",
    train_size: float = 0.7,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
) -> tuple[Any, dict, list[str], Any | None]:
    """
    Train a supervised learning model (classification or regression).

    Args:
        df: Input DataFrame
        algorithm: Algorithm name (e.g., 'random_forest_classifier')
        target_column: Target column for prediction
        feature_columns: Feature columns (None = auto-select)
        hyperparameters: Algorithm-specific parameters
        normalization: Normalization method
        handle_missing: Missing value handling strategy
        train_size, val_size, test_size: Split proportions
        random_state: Random seed

    Returns:
        Tuple of (trained_model, metrics_dict, feature_names, scaler)
    """
    algo_info = get_algorithm_info(algorithm)
    if not algo_info:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    if not is_supervised(algorithm):
        raise ValueError(f"Algorithm {algorithm} is not a supervised algorithm")

    model_type = algo_info["type"]

    # Preprocess the data
    preprocessed = preprocess_dataframe(
        df=df,
        target_column=target_column,
        feature_columns=feature_columns,
        normalization=normalization,
        handle_missing=handle_missing,
        train_size=train_size,
        val_size=val_size,
        test_size=test_size,
        random_state=random_state,
    )

    X_train = preprocessed["X_train"]
    X_val = preprocessed["X_val"]
    X_test = preprocessed["X_test"]
    y_train = preprocessed["y_train"]
    y_val = preprocessed["y_val"]
    y_test = preprocessed["y_test"]
    feature_names = preprocessed["feature_columns"]
    scaler = preprocessed["scaler"]
    target_encoder = preprocessed["target_encoder"]

    # Build hyperparameters
    params = {}
    for param_name, param_info in algo_info["params"].items():
        if hyperparameters and param_name in hyperparameters:
            params[param_name] = hyperparameters[param_name]
        else:
            params[param_name] = param_info["default"]

    # Create and train model
    model_class = algo_info["class"]
    model = model_class(**params)
    model.fit(X_train, y_train)

    # Compute metrics
    y_pred_train = model.predict(X_train)
    y_pred_val = model.predict(X_val)
    y_pred_test = model.predict(X_test)

    metrics = {
        "split_info": preprocessed["split_info"],
        "normalization_method": normalization,
    }

    if model_type == "classification":
        # Training metrics
        metrics["train_accuracy"] = float(accuracy_score(y_train, y_pred_train))

        # Validation metrics
        metrics["val_accuracy"] = float(accuracy_score(y_val, y_pred_val))
        metrics["val_f1_score"] = float(f1_score(y_val, y_pred_val, average="weighted", zero_division=0))
        metrics["val_precision"] = float(precision_score(y_val, y_pred_val, average="weighted", zero_division=0))
        metrics["val_recall"] = float(recall_score(y_val, y_pred_val, average="weighted", zero_division=0))

        # Test metrics
        metrics["test_accuracy"] = float(accuracy_score(y_test, y_pred_test))
        metrics["test_f1_score"] = float(f1_score(y_test, y_pred_test, average="weighted", zero_division=0))
        metrics["test_precision"] = float(precision_score(y_test, y_pred_test, average="weighted", zero_division=0))
        metrics["test_recall"] = float(recall_score(y_test, y_pred_test, average="weighted", zero_division=0))

        # Main metrics (use test set)
        metrics["accuracy"] = metrics["test_accuracy"]
        metrics["f1_score"] = metrics["test_f1_score"]
        metrics["precision"] = metrics["test_precision"]
        metrics["recall"] = metrics["test_recall"]

        # Feature importances if available
        if hasattr(model, "feature_importances_"):
            metrics["feature_importances"] = {
                name: float(imp)
                for name, imp in zip(feature_names, model.feature_importances_)
            }

        # Class labels
        if target_encoder:
            metrics["classes"] = list(target_encoder.classes_)

    else:  # regression
        # Training metrics
        metrics["train_mse"] = float(mean_squared_error(y_train, y_pred_train))
        metrics["train_r2"] = float(r2_score(y_train, y_pred_train))

        # Validation metrics
        metrics["val_mse"] = float(mean_squared_error(y_val, y_pred_val))
        metrics["val_rmse"] = float(np.sqrt(metrics["val_mse"]))
        metrics["val_mae"] = float(mean_absolute_error(y_val, y_pred_val))
        metrics["val_r2"] = float(r2_score(y_val, y_pred_val))

        # Test metrics
        metrics["test_mse"] = float(mean_squared_error(y_test, y_pred_test))
        metrics["test_rmse"] = float(np.sqrt(metrics["test_mse"]))
        metrics["test_mae"] = float(mean_absolute_error(y_test, y_pred_test))
        metrics["test_r2"] = float(r2_score(y_test, y_pred_test))

        # Main metrics (use test set)
        metrics["mse"] = metrics["test_mse"]
        metrics["rmse"] = metrics["test_rmse"]
        metrics["mae"] = metrics["test_mae"]
        metrics["r2"] = metrics["test_r2"]

        if hasattr(model, "feature_importances_"):
            metrics["feature_importances"] = {
                name: float(imp)
                for name, imp in zip(feature_names, model.feature_importances_)
            }

    return model, metrics, feature_names, scaler


# ============================================================================
# Unsupervised Training
# ============================================================================

def train_unsupervised_model(
    df: pd.DataFrame,
    algorithm: str,
    feature_columns: list[str] | None = None,
    hyperparameters: dict | None = None,
    normalization: Literal["standard", "minmax", "robust", "none"] = "standard",
    handle_missing: Literal["drop", "mean", "median", "mode", "zero"] = "zero",
    random_state: int = 42,
) -> tuple[Any, dict, list[str], Any | None]:
    """
    Train an unsupervised learning model (clustering or dimensionality reduction).

    Args:
        df: Input DataFrame
        algorithm: Algorithm name (e.g., 'kmeans', 'pca')
        feature_columns: Feature columns (None = auto-select all)
        hyperparameters: Algorithm-specific parameters
        normalization: Normalization method
        handle_missing: Missing value handling strategy
        random_state: Random seed

    Returns:
        Tuple of (trained_model, metrics_dict, feature_names, scaler)
    """
    algo_info = get_algorithm_info(algorithm)
    if not algo_info:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    if not is_unsupervised(algorithm):
        raise ValueError(f"Algorithm {algorithm} is not an unsupervised algorithm")

    model_type = algo_info["type"]

    # Preprocess the data (no target for unsupervised)
    preprocessed = preprocess_dataframe(
        df=df,
        target_column=None,  # No target for unsupervised
        feature_columns=feature_columns,
        normalization=normalization,
        handle_missing=handle_missing,
        train_size=1.0,  # Use all data for unsupervised
        val_size=0.0,
        test_size=0.0,
        random_state=random_state,
    )

    # For unsupervised, we use all data (X_train contains everything when val/test = 0)
    X = preprocessed["X_train"]
    feature_names = preprocessed["feature_columns"]
    scaler = preprocessed["scaler"]

    # Build hyperparameters
    params = {}
    for param_name, param_info in algo_info["params"].items():
        if hyperparameters and param_name in hyperparameters:
            params[param_name] = hyperparameters[param_name]
        else:
            params[param_name] = param_info["default"]

    # Create and train model
    model_class = algo_info["class"]
    model = model_class(**params)

    metrics = {
        "normalization_method": normalization,
        "n_samples": len(X),
    }

    if model_type == "clustering":
        # Clustering
        model.fit(X)
        labels = model.labels_ if hasattr(model, "labels_") else model.predict(X)

        n_clusters = int(len(set(labels)) - (1 if -1 in labels else 0))
        metrics["n_clusters"] = n_clusters

        # Cluster sizes
        unique_labels, counts = np.unique(labels, return_counts=True)
        metrics["cluster_sizes"] = {
            int(label): int(count) for label, count in zip(unique_labels, counts)
        }

        # Silhouette score (only if we have more than 1 cluster)
        if n_clusters > 1 and len(X) > n_clusters:
            try:
                metrics["silhouette_score"] = float(silhouette_score(X, labels))
            except Exception:
                pass

        if hasattr(model, "inertia_"):
            metrics["inertia"] = float(model.inertia_)

        if hasattr(model, "cluster_centers_"):
            metrics["cluster_centers"] = model.cluster_centers_.tolist()

    elif model_type == "dimensionality_reduction":
        # PCA and similar
        X_transformed = model.fit_transform(X)

        metrics["n_components"] = int(model.n_components_)
        metrics["explained_variance_ratio"] = [
            float(v) for v in model.explained_variance_ratio_
        ]
        metrics["total_explained_variance"] = float(
            sum(model.explained_variance_ratio_)
        )
        metrics["transformed_shape"] = list(X_transformed.shape)

    return model, metrics, feature_names, scaler


# ============================================================================
# Legacy Training Function (backward compatibility)
# ============================================================================

def train_model(
    df: pd.DataFrame,
    algorithm: str,
    model_type: str,
    target_column: str | None = None,
    feature_columns: list[str] | None = None,
    hyperparameters: dict | None = None,
    test_size: float = 0.2,
) -> tuple[Any, dict, list[str]]:
    """
    Legacy training function for backward compatibility.
    Delegates to supervised or unsupervised training based on model_type.
    """
    if model_type in SUPERVISED_TYPES:
        if not target_column:
            raise ValueError("target_column is required for supervised learning")

        model, metrics, feature_names, _ = train_supervised_model(
            df=df,
            algorithm=algorithm,
            target_column=target_column,
            feature_columns=feature_columns,
            hyperparameters=hyperparameters,
            normalization="none",  # Legacy behavior
            handle_missing="zero",
            train_size=1.0 - test_size,
            val_size=0.0,
            test_size=test_size,
        )
        return model, metrics, feature_names

    elif model_type in UNSUPERVISED_TYPES:
        model, metrics, feature_names, _ = train_unsupervised_model(
            df=df,
            algorithm=algorithm,
            feature_columns=feature_columns,
            hyperparameters=hyperparameters,
            normalization="none",  # Legacy behavior
            handle_missing="zero",
        )
        return model, metrics, feature_names

    else:
        raise ValueError(f"Unknown model type: {model_type}")


# ============================================================================
# Model Serialization
# ============================================================================

def serialize_model(model: Any, scaler: Any | None = None) -> bytes:
    """Serialize a trained model (and optionally scaler) to bytes using joblib."""
    buffer = io.BytesIO()
    data = {"model": model, "scaler": scaler}
    joblib.dump(data, buffer)
    return buffer.getvalue()


def deserialize_model(content: bytes) -> tuple[Any, Any | None]:
    """
    Deserialize a model from bytes.

    Returns:
        Tuple of (model, scaler) - scaler may be None for older models
    """
    buffer = io.BytesIO(content)
    data = joblib.load(buffer)

    # Handle both old format (just model) and new format (dict with model and scaler)
    if isinstance(data, dict) and "model" in data:
        return data["model"], data.get("scaler")
    else:
        # Legacy format - just the model
        return data, None


# ============================================================================
# Prediction/Inference
# ============================================================================

def predict(
    model: Any,
    input_data: list[dict] | pd.DataFrame,
    feature_names: list[str],
    scaler: Any | None = None,
) -> dict:
    """
    Run predictions using a trained model.

    Args:
        model: Trained scikit-learn model
        input_data: Input data as list of dicts or DataFrame
        feature_names: List of feature names the model was trained on
        scaler: Optional scaler used during training

    Returns:
        Dictionary with predictions and optionally probabilities
    """
    if isinstance(input_data, list):
        df = pd.DataFrame(input_data)
    else:
        df = input_data.copy()

    # Ensure columns match training features
    for col in feature_names:
        if col not in df.columns:
            df[col] = 0

    X = df[feature_names].copy()

    # Handle categorical features
    for col in X.columns:
        if X[col].dtype == "object":
            from sklearn.preprocessing import LabelEncoder
            X[col] = LabelEncoder().fit_transform(X[col].astype(str))

    X = X.values.astype(np.float64)
    X = np.nan_to_num(X, nan=0.0)

    # Apply scaler if provided
    if scaler is not None:
        X = scaler.transform(X)

    result = {}

    # Check if model has predict method (classification/regression)
    if hasattr(model, "predict"):
        result["predictions"] = model.predict(X).tolist()

    # Add probabilities for classifiers
    if hasattr(model, "predict_proba"):
        try:
            result["probabilities"] = model.predict_proba(X).tolist()
        except Exception:
            pass

    # For dimensionality reduction, return transformed data
    if hasattr(model, "transform"):
        result["transformed"] = model.transform(X).tolist()

    # For clustering, include cluster labels
    if hasattr(model, "labels_"):
        # For fitted clustering models, use predict if available
        if hasattr(model, "predict"):
            result["cluster_labels"] = model.predict(X).tolist()

    return result


def run_inference(
    model: Any,
    scaler: Any | None,
    input_data: list[dict] | pd.DataFrame,
    feature_names: list[str],
) -> dict:
    """
    Run inference on new data using a trained model.
    This is the main entry point for model inference.
    """
    return predict(model, input_data, feature_names, scaler)
