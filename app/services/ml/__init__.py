"""ML Trainer service for model training and inference."""

from app.services.ml.router import router
from app.services.ml.algorithms import ALGORITHMS
from app.services.ml.trainer import train_model as train_model_core, predict as predict_core

__all__ = ["router", "ALGORITHMS", "train_model_core", "predict_core"]
