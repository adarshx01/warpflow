"""Computer Vision service router."""
from .router import router, cv_train_model, cv_load_model, cv_infer, cv_list_models

__all__ = ["router", "cv_train_model", "cv_load_model", "cv_infer", "cv_list_models"]
