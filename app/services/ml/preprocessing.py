"""Data preprocessing module for ML operations."""

from typing import Literal
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, LabelEncoder
from sklearn.model_selection import train_test_split


# Normalization methods
NORMALIZATION_METHODS = {
    "standard": StandardScaler,
    "minmax": MinMaxScaler,
    "robust": RobustScaler,
    "none": None,
}

# Missing value handling strategies
MISSING_VALUE_STRATEGIES = ["drop", "mean", "median", "mode", "zero"]


def analyze_column(series: pd.Series) -> dict:
    """Analyze a single column and return its statistics."""
    col_info = {
        "name": series.name,
        "dtype": str(series.dtype),
        "null_count": int(series.isnull().sum()),
        "null_percentage": round(series.isnull().sum() / len(series) * 100, 2) if len(series) > 0 else 0,
        "unique_count": int(series.nunique()),
    }

    # Determine if column is numeric or categorical
    if pd.api.types.is_numeric_dtype(series):
        col_info["column_type"] = "numeric"
        col_info["stats"] = {
            "min": float(series.min()) if not series.isnull().all() else None,
            "max": float(series.max()) if not series.isnull().all() else None,
            "mean": float(series.mean()) if not series.isnull().all() else None,
            "median": float(series.median()) if not series.isnull().all() else None,
            "std": float(series.std()) if not series.isnull().all() else None,
        }
    else:
        col_info["column_type"] = "categorical"
        # Get top 10 most frequent values
        value_counts = series.value_counts().head(10)
        col_info["top_values"] = [
            {"value": str(idx), "count": int(count)}
            for idx, count in value_counts.items()
        ]

    return col_info


def analyze_dataset(df: pd.DataFrame) -> dict:
    """
    Analyze a dataset and return comprehensive information.

    Returns:
        dict with columns info, row_count, numeric_columns, categorical_columns
    """
    columns = [analyze_column(df[col]) for col in df.columns]

    numeric_columns = [col["name"] for col in columns if col["column_type"] == "numeric"]
    categorical_columns = [col["name"] for col in columns if col["column_type"] == "categorical"]

    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "memory_usage_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
    }


def handle_missing_values(
    df: pd.DataFrame,
    strategy: Literal["drop", "mean", "median", "mode", "zero"] = "zero",
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Handle missing values in the dataset.

    Args:
        df: Input DataFrame
        strategy: How to handle missing values
        columns: Specific columns to apply strategy (None = all columns)

    Returns:
        DataFrame with missing values handled
    """
    df = df.copy()
    target_cols = columns if columns else df.columns.tolist()

    if strategy == "drop":
        df = df.dropna(subset=target_cols)
    elif strategy == "zero":
        for col in target_cols:
            if col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(0)
                else:
                    df[col] = df[col].fillna("")
    elif strategy == "mean":
        for col in target_cols:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(df[col].mean())
    elif strategy == "median":
        for col in target_cols:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(df[col].median())
    elif strategy == "mode":
        for col in target_cols:
            if col in df.columns:
                mode_val = df[col].mode()
                if len(mode_val) > 0:
                    df[col] = df[col].fillna(mode_val.iloc[0])

    return df


def encode_categorical_columns(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, LabelEncoder]]:
    """
    Encode categorical columns using LabelEncoder.

    Returns:
        Tuple of (encoded DataFrame, dict of encoders for each column)
    """
    df = df.copy()
    encoders = {}

    target_cols = columns if columns else df.columns.tolist()

    for col in target_cols:
        if col in df.columns and df[col].dtype == "object":
            encoder = LabelEncoder()
            df[col] = encoder.fit_transform(df[col].astype(str))
            encoders[col] = encoder

    return df, encoders


def apply_normalization(
    X: np.ndarray,
    method: Literal["standard", "minmax", "robust", "none"] = "standard",
) -> tuple[np.ndarray, object | None]:
    """
    Apply normalization/scaling to features.

    Args:
        X: Feature array
        method: Normalization method to use

    Returns:
        Tuple of (normalized array, fitted scaler or None)
    """
    if method == "none" or method not in NORMALIZATION_METHODS:
        return X, None

    scaler_class = NORMALIZATION_METHODS[method]
    if scaler_class is None:
        return X, None

    scaler = scaler_class()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, scaler


def create_train_test_val_split(
    X: np.ndarray,
    y: np.ndarray | None = None,
    train_size: float = 0.7,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
) -> dict:
    """
    Create train/validation/test split.

    Args:
        X: Feature array
        y: Target array (optional, for supervised learning)
        train_size: Proportion for training (default 0.7)
        val_size: Proportion for validation (default 0.15)
        test_size: Proportion for testing (default 0.15)
        random_state: Random seed for reproducibility

    Returns:
        Dict with X_train, X_val, X_test, and optionally y_train, y_val, y_test
    """
    # Normalize proportions
    total = train_size + val_size + test_size
    train_size = train_size / total
    val_size = val_size / total
    test_size = test_size / total

    # First split: train+val vs test
    val_test_size = val_size + test_size

    if y is not None:
        X_train_val, X_test, y_train_val, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

        # Second split: train vs val (from the remaining data)
        val_ratio = val_size / (train_size + val_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_train_val, y_train_val, test_size=val_ratio, random_state=random_state
        )

        return {
            "X_train": X_train,
            "X_val": X_val,
            "X_test": X_test,
            "y_train": y_train,
            "y_val": y_val,
            "y_test": y_test,
            "split_info": {
                "train_samples": len(X_train),
                "val_samples": len(X_val),
                "test_samples": len(X_test),
            },
        }
    else:
        # Unsupervised: no y values
        X_train_val, X_test = train_test_split(
            X, test_size=test_size, random_state=random_state
        )

        val_ratio = val_size / (train_size + val_size)
        X_train, X_val = train_test_split(
            X_train_val, test_size=val_ratio, random_state=random_state
        )

        return {
            "X_train": X_train,
            "X_val": X_val,
            "X_test": X_test,
            "split_info": {
                "train_samples": len(X_train),
                "val_samples": len(X_val),
                "test_samples": len(X_test),
            },
        }


def preprocess_dataframe(
    df: pd.DataFrame,
    target_column: str | None = None,
    feature_columns: list[str] | None = None,
    normalization: Literal["standard", "minmax", "robust", "none"] = "standard",
    handle_missing: Literal["drop", "mean", "median", "mode", "zero"] = "zero",
    train_size: float = 0.7,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
) -> dict:
    """
    Full preprocessing pipeline for a DataFrame.

    Args:
        df: Input DataFrame
        target_column: Target column for supervised learning (None for unsupervised)
        feature_columns: List of feature columns (None = all except target)
        normalization: Normalization method
        handle_missing: Missing value strategy
        train_size, val_size, test_size: Split proportions
        random_state: Random seed

    Returns:
        Dict with preprocessed data, scalers, encoders, and metadata
    """
    df = df.copy()

    # Handle missing values
    df = handle_missing_values(df, strategy=handle_missing)

    # Determine feature columns
    if feature_columns is None:
        if target_column:
            feature_columns = [col for col in df.columns if col != target_column]
        else:
            feature_columns = df.columns.tolist()

    # Encode categorical features
    df_encoded, encoders = encode_categorical_columns(df, columns=feature_columns)

    # Extract features
    X = df_encoded[feature_columns].values.astype(np.float64)

    # Handle NaN in features
    X = np.nan_to_num(X, nan=0.0)

    # Apply normalization
    X_normalized, scaler = apply_normalization(X, method=normalization)

    # Extract target if supervised
    y = None
    target_encoder = None
    if target_column:
        if df[target_column].dtype == "object":
            target_encoder = LabelEncoder()
            y = target_encoder.fit_transform(df[target_column].astype(str))
        else:
            y = df[target_column].values.astype(np.float64)
        y = np.nan_to_num(y, nan=0.0)

    # Create splits
    split_data = create_train_test_val_split(
        X_normalized, y,
        train_size=train_size,
        val_size=val_size,
        test_size=test_size,
        random_state=random_state,
    )

    return {
        **split_data,
        "feature_columns": feature_columns,
        "target_column": target_column,
        "scaler": scaler,
        "feature_encoders": encoders,
        "target_encoder": target_encoder,
        "normalization_method": normalization,
        "missing_value_strategy": handle_missing,
    }


def get_data_preview(
    df: pd.DataFrame,
    n_rows: int = 10,
) -> dict:
    """
    Get a preview of the dataset.

    Args:
        df: Input DataFrame
        n_rows: Number of rows to preview

    Returns:
        Dict with preview data
    """
    preview_df = df.head(n_rows)

    return {
        "columns": df.columns.tolist(),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "data": preview_df.to_dict(orient="records"),
        "total_rows": len(df),
        "preview_rows": len(preview_df),
    }
