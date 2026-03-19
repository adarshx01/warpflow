"""ML Algorithm registry with supported algorithms and their configurations."""

from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    AdaBoostClassifier,
    AdaBoostRegressor,
)
from sklearn.svm import SVC, SVR
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from catboost import CatBoostClassifier, CatBoostRegressor

# Algorithm registry with class references, types, and default hyperparameters
ALGORITHMS = {
    # Supervised - Classification
    "logistic_regression": {
        "class": LogisticRegression,
        "type": "classification",
        "params": {
            "C": {"type": "float", "default": 1.0, "min": 0.001, "max": 100},
            "max_iter": {"type": "int", "default": 1000, "min": 100, "max": 10000},
        },
    },
    "random_forest_classifier": {
        "class": RandomForestClassifier,
        "type": "classification",
        "params": {
            "n_estimators": {"type": "int", "default": 100, "min": 10, "max": 500},
            "max_depth": {"type": "int", "default": 10, "min": 1, "max": 50},
            "min_samples_split": {"type": "int", "default": 2, "min": 2, "max": 20},
        },
    },
    "svm_classifier": {
        "class": SVC,
        "type": "classification",
        "params": {
            "C": {"type": "float", "default": 1.0, "min": 0.001, "max": 100},
            "kernel": {"type": "str", "default": "rbf", "options": ["linear", "poly", "rbf", "sigmoid"]},
            "probability": {"type": "bool", "default": True},
        },
    },
    "gradient_boosting_classifier": {
        "class": GradientBoostingClassifier,
        "type": "classification",
        "params": {
            "n_estimators": {"type": "int", "default": 100, "min": 10, "max": 500},
            "learning_rate": {"type": "float", "default": 0.1, "min": 0.01, "max": 1.0},
            "max_depth": {"type": "int", "default": 3, "min": 1, "max": 20},
        },
    },
    "adaboost_classifier": {
        "class": AdaBoostClassifier,
        "type": "classification",
        "params": {
            "n_estimators": {"type": "int", "default": 50, "min": 10, "max": 500},
            "learning_rate": {"type": "float", "default": 1.0, "min": 0.01, "max": 2.0},
        },
    },
    "catboost_classifier": {
        "class": CatBoostClassifier,
        "type": "classification",
        "params": {
            "iterations": {"type": "int", "default": 100, "min": 10, "max": 1000},
            "learning_rate": {"type": "float", "default": 0.1, "min": 0.01, "max": 1.0},
            "depth": {"type": "int", "default": 6, "min": 1, "max": 16},
            "verbose": {"type": "bool", "default": False},
        },
    },
    # Supervised - Regression
    "linear_regression": {
        "class": LinearRegression,
        "type": "regression",
        "params": {},
    },
    "random_forest_regressor": {
        "class": RandomForestRegressor,
        "type": "regression",
        "params": {
            "n_estimators": {"type": "int", "default": 100, "min": 10, "max": 500},
            "max_depth": {"type": "int", "default": 10, "min": 1, "max": 50},
            "min_samples_split": {"type": "int", "default": 2, "min": 2, "max": 20},
        },
    },
    "svm_regressor": {
        "class": SVR,
        "type": "regression",
        "params": {
            "C": {"type": "float", "default": 1.0, "min": 0.001, "max": 100},
            "kernel": {"type": "str", "default": "rbf", "options": ["linear", "poly", "rbf", "sigmoid"]},
        },
    },
    "gradient_boosting_regressor": {
        "class": GradientBoostingRegressor,
        "type": "regression",
        "params": {
            "n_estimators": {"type": "int", "default": 100, "min": 10, "max": 500},
            "learning_rate": {"type": "float", "default": 0.1, "min": 0.01, "max": 1.0},
            "max_depth": {"type": "int", "default": 3, "min": 1, "max": 20},
        },
    },
    "adaboost_regressor": {
        "class": AdaBoostRegressor,
        "type": "regression",
        "params": {
            "n_estimators": {"type": "int", "default": 50, "min": 10, "max": 500},
            "learning_rate": {"type": "float", "default": 1.0, "min": 0.01, "max": 2.0},
        },
    },
    "catboost_regressor": {
        "class": CatBoostRegressor,
        "type": "regression",
        "params": {
            "iterations": {"type": "int", "default": 100, "min": 10, "max": 1000},
            "learning_rate": {"type": "float", "default": 0.1, "min": 0.01, "max": 1.0},
            "depth": {"type": "int", "default": 6, "min": 1, "max": 16},
            "verbose": {"type": "bool", "default": False},
        },
    },
    # Unsupervised - Clustering
    "kmeans": {
        "class": KMeans,
        "type": "clustering",
        "params": {
            "n_clusters": {"type": "int", "default": 3, "min": 2, "max": 20},
            "max_iter": {"type": "int", "default": 300, "min": 100, "max": 1000},
            "n_init": {"type": "int", "default": 10, "min": 1, "max": 50},
        },
    },
    "dbscan": {
        "class": DBSCAN,
        "type": "clustering",
        "params": {
            "eps": {"type": "float", "default": 0.5, "min": 0.01, "max": 10.0},
            "min_samples": {"type": "int", "default": 5, "min": 1, "max": 50},
        },
    },
    # Unsupervised - Dimensionality Reduction
    "pca": {
        "class": PCA,
        "type": "dimensionality_reduction",
        "params": {
            "n_components": {"type": "int", "default": 2, "min": 1, "max": 100},
        },
    },
}


def get_algorithm_info(algorithm: str) -> dict | None:
    """Get algorithm information by name."""
    return ALGORITHMS.get(algorithm)


def get_algorithms_by_type(model_type: str) -> list[str]:
    """Get list of algorithm names for a given model type."""
    return [name for name, info in ALGORITHMS.items() if info["type"] == model_type]


def list_all_algorithms() -> list[dict]:
    """List all algorithms with their metadata."""
    return [
        {"name": name, "type": info["type"], "params": info["params"]}
        for name, info in ALGORITHMS.items()
    ]


# Supervised types are classification and regression
SUPERVISED_TYPES = {"classification", "regression"}
# Unsupervised types are clustering and dimensionality reduction
UNSUPERVISED_TYPES = {"clustering", "dimensionality_reduction"}


def get_supervised_algorithms() -> list[dict]:
    """Get all supervised learning algorithms (classification + regression)."""
    return [
        {"name": name, "type": info["type"], "params": info["params"]}
        for name, info in ALGORITHMS.items()
        if info["type"] in SUPERVISED_TYPES
    ]


def get_unsupervised_algorithms() -> list[dict]:
    """Get all unsupervised learning algorithms (clustering + dimensionality reduction)."""
    return [
        {"name": name, "type": info["type"], "params": info["params"]}
        for name, info in ALGORITHMS.items()
        if info["type"] in UNSUPERVISED_TYPES
    ]


def is_supervised(algorithm: str) -> bool:
    """Check if an algorithm is supervised."""
    info = ALGORITHMS.get(algorithm)
    return info is not None and info["type"] in SUPERVISED_TYPES


def is_unsupervised(algorithm: str) -> bool:
    """Check if an algorithm is unsupervised."""
    info = ALGORITHMS.get(algorithm)
    return info is not None and info["type"] in UNSUPERVISED_TYPES
