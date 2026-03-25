"""
Computer Vision service router.
Provides endpoints for CV model training and inference.
Communicates with the unified CV microservice.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import os
import boto3
from botocore.exceptions import ClientError

from app.auth.utils import get_current_user
from app.models import User
from app.services.secrets_router import get_secret_value

router = APIRouter(prefix="/api/cv", tags=["Computer Vision"])

# Single CV service URL (unified service)
CV_SERVICE_URL = os.getenv("CV_SERVICE_URL", "http://localhost:8080")


# ─── Schemas ────────────────────────────────────────────────────────────────

class CVTrainRequest(BaseModel):
    task: str  # classification, detection, segmentation
    model: str  # resnet, vgg, yolov8, unet, etc.
    optimizer: str = "adam"
    dataset_path: str
    dataset_format: str = "imagefolder"
    epochs: int = 10
    image_size: int = 224
    batch_size: int = 32
    learning_rate: float = 0.001
    train_pct: float = 0.7
    val_pct: float = 0.15
    test_pct: float = 0.15
    save_local: bool = True
    upload_to_s3: bool = False
    s3_model_path: Optional[str] = None
    custom_model_name: Optional[str] = None


class CVTrainResponse(BaseModel):
    status: str
    model_saved_at: str
    s3_path: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class CVLoadModelRequest(BaseModel):
    task_type: str
    model_name: str
    model_path: Optional[str] = None
    dataset_path: Optional[str] = None
    num_classes: Optional[int] = None


class CVInferRequest(BaseModel):
    input_type: str = "file"  # file, url, webcam
    image_path: Optional[str] = None
    image_url: Optional[str] = None
    confidence_threshold: float = 0.5


class CVInferResponse(BaseModel):
    status: str
    predictions: Any
    annotated_image: Optional[str] = None


class S3DownloadRequest(BaseModel):
    s3_path: str


# ─── Helper Functions ────────────────────────────────────────────────────────

async def get_s3_client(user_id: int):
    """Get an S3 client with user's credentials."""
    access_key = await get_secret_value(user_id, "s3_access_key")
    secret_key = await get_secret_value(user_id, "s3_secret_key")
    endpoint_url = await get_secret_value(user_id, "s3_endpoint_url")
    region = await get_secret_value(user_id, "s3_region")

    if not access_key or not secret_key:
        raise HTTPException(status_code=400, detail="S3 credentials not configured")

    return boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint_url if endpoint_url else None,
        region_name=region if region else "us-east-1"
    )


async def upload_to_s3(user_id: int, local_path: str, s3_path: str) -> str:
    """Upload a file to S3."""
    bucket_name = await get_secret_value(user_id, "s3_bucket_name")
    if not bucket_name:
        raise HTTPException(status_code=400, detail="S3 bucket not configured")

    s3_client = await get_s3_client(user_id)
    try:
        s3_client.upload_file(local_path, bucket_name, s3_path)
        return f"s3://{bucket_name}/{s3_path}"
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")


async def download_from_s3(user_id: int, s3_path: str, local_path: str) -> str:
    """Download a file from S3."""
    bucket_name = await get_secret_value(user_id, "s3_bucket_name")
    if not bucket_name:
        raise HTTPException(status_code=400, detail="S3 bucket not configured")

    # Parse s3_path to get the key
    if s3_path.startswith("s3://"):
        s3_path = s3_path.split("/", 3)[-1]

    s3_client = await get_s3_client(user_id)
    try:
        s3_client.download_file(bucket_name, s3_path, local_path)
        return local_path
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 download failed: {str(e)}")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/alive")
async def check_alive():
    """Check if the CV service is alive."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{CV_SERVICE_URL}/health")
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass

    raise HTTPException(status_code=503, detail="CV service not available")


@router.post("/train", response_model=CVTrainResponse)
async def train_cv_model(
    request: CVTrainRequest,
    user: User = Depends(get_current_user)
):
    """Train a computer vision model."""
    # Validate dataset path exists
    if not os.path.exists(request.dataset_path):
        raise HTTPException(status_code=400, detail=f"Dataset path does not exist: {request.dataset_path}")

    # Send training request to CV service
    try:
        async with httpx.AsyncClient(timeout=None) as client:  # No timeout for training
            response = await client.post(
                f"{CV_SERVICE_URL}/training/train",
                json={
                    "task": request.task,
                    "model": request.model,
                    "optimizer": request.optimizer,
                    "train_pct": request.train_pct,
                    "val_pct": request.val_pct,
                    "test_pct": request.test_pct,
                    "dataset_path": request.dataset_path,
                    "epochs": request.epochs,
                }
            )
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"CV service error: {str(e)}")

    model_path = result.get("model_saved_at", "")
    s3_path = None

    # Upload to S3 if requested
    if request.upload_to_s3 and model_path and os.path.exists(model_path):
        s3_key = request.s3_model_path or f"cv_models/{os.path.basename(model_path)}"
        s3_path = await upload_to_s3(user.id, model_path, s3_key)

    return CVTrainResponse(
        status=result.get("status", "completed"),
        model_saved_at=model_path,
        s3_path=s3_path,
    )


@router.get("/models/saved")
async def get_saved_models():
    """Get list of saved CV models from the CV service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CV_SERVICE_URL}/inference/models/saved")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        # Return empty if service not available
        return {"saved_models": {}}


@router.get("/models/available")
async def get_available_models():
    """Get available model architectures for each task type."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CV_SERVICE_URL}/inference/models/available")
            response.raise_for_status()
            return response.json()
    except Exception:
        # Return default if service not available
        return {
            "tasks": {
                "classification": [
                    "resnet", "efficientnet", "vgg", "inception", "mobilenet",
                    "densenet", "vit", "convnext"
                ],
                "detection": [
                    "yolov3", "yolov4", "yolov5", "yolov8", "fasterrcnn", "ssd",
                    "retinanet", "efficientdet", "detr", "maskrcnn"
                ],
                "segmentation": [
                    "unet", "deeplabv3", "pspnet", "segnet", "fcn", "maskrcnn",
                    "yolact", "segformer", "mask2former"
                ]
            }
        }


@router.post("/models/load")
async def load_model(request: CVLoadModelRequest):
    """Load a model into the inference engine."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{CV_SERVICE_URL}/inference/models/load",
                json={
                    "task_type": request.task_type,
                    "model_name": request.model_name,
                    "model_path": request.model_path,
                    "dataset_path": request.dataset_path,
                    "num_classes": request.num_classes,
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"CV service error: {str(e)}")


@router.post("/models/download-s3")
async def download_model_from_s3(
    request: S3DownloadRequest,
    user: User = Depends(get_current_user)
):
    """Download a model from S3 to local storage."""
    # Create local directory for models
    local_dir = os.path.join(os.path.dirname(__file__), "..", "..", "cv_models")
    os.makedirs(local_dir, exist_ok=True)

    # Generate local path
    filename = os.path.basename(request.s3_path)
    local_path = os.path.join(local_dir, filename)

    await download_from_s3(user.id, request.s3_path, local_path)

    return {"local_path": local_path, "status": "downloaded"}


@router.get("/models/current")
async def get_current_model():
    """Get information about the currently loaded model."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CV_SERVICE_URL}/inference/models/current")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"status": "no_model", "message": "No model loaded or service unavailable"}


@router.post("/infer", response_model=CVInferResponse)
async def run_inference(request: CVInferRequest):
    """Run inference on an image."""
    if request.input_type == "file" and request.image_path:
        if not os.path.exists(request.image_path):
            raise HTTPException(status_code=400, detail=f"Image file not found: {request.image_path}")

    if request.input_type == "webcam":
        # For webcam, return the video feed URL
        return CVInferResponse(
            status="streaming",
            predictions={"video_feed_url": f"{CV_SERVICE_URL}/inference/video_feed"},
        )

    # For file/URL inference, use the new process_image endpoint
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{CV_SERVICE_URL}/inference/process_image",
                json={
                    "image_path": request.image_path,
                    "image_url": request.image_url,
                    "confidence_threshold": request.confidence_threshold
                }
            )
            response.raise_for_status()
            result = response.json()

        if result.get("status") == "success":
            return CVInferResponse(
                status="success",
                predictions=result.get("predictions"),
                annotated_image=result.get("annotated_image")
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Inference failed")
            )

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"CV inference error: {str(e)}")


# ─── Agent Tool Functions ────────────────────────────────────────────────────

async def cv_train_model(user_id: int, params: Dict[str, Any]) -> Dict:
    """Agent tool: Train a CV model."""
    request = CVTrainRequest(**params)

    # Send training request to CV service
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{CV_SERVICE_URL}/training/train",
                json={
                    "task": request.task,
                    "model": request.model,
                    "optimizer": request.optimizer,
                    "train_pct": request.train_pct,
                    "val_pct": request.val_pct,
                    "test_pct": request.test_pct,
                    "dataset_path": request.dataset_path,
                    "epochs": request.epochs,
                }
            )
            response.raise_for_status()
            result = response.json()

            model_path = result.get("model_saved_at", "")
            s3_path = None

            # Upload to S3 if requested
            if params.get("upload_to_s3") and model_path and os.path.exists(model_path):
                s3_key = params.get("s3_model_path") or f"cv_models/{os.path.basename(model_path)}"
                s3_path = await upload_to_s3(user_id, model_path, s3_key)

            return {
                "status": "success",
                "model_saved_at": model_path,
                "s3_path": s3_path,
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def cv_load_model(user_id: int, params: Dict[str, Any]) -> Dict:
    """Agent tool: Load a CV model for inference."""
    try:
        # If loading from S3, download first
        if params.get("model_source") == "s3" and params.get("s3_model_path"):
            local_dir = os.path.join(os.path.dirname(__file__), "..", "..", "cv_models")
            os.makedirs(local_dir, exist_ok=True)
            filename = os.path.basename(params["s3_model_path"])
            local_path = os.path.join(local_dir, filename)
            await download_from_s3(user_id, params["s3_model_path"], local_path)
            params["model_path"] = local_path

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{CV_SERVICE_URL}/inference/models/load",
                json={
                    "task_type": params.get("task_type"),
                    "model_name": params.get("model_name"),
                    "model_path": params.get("model_path"),
                    "dataset_path": params.get("dataset_path"),
                    "num_classes": params.get("num_classes"),
                }
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def cv_infer(user_id: int, params: Dict[str, Any]) -> Dict:
    """Agent tool: Run CV inference on an image."""
    try:
        input_type = params.get("input_type", "file")
        image_path = params.get("image_path")
        image_url = params.get("image_url")
        confidence_threshold = params.get("confidence_threshold", 0.5)

        # For webcam, return the video feed URL
        if input_type == "webcam":
            return {
                "status": "streaming",
                "message": "Webcam inference active",
                "video_feed_url": f"{CV_SERVICE_URL}/inference/video_feed",
                "instructions": "Open the video_feed_url in a browser to see real-time inference"
            }

        # For single image inference (file or URL)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{CV_SERVICE_URL}/inference/process_image",
                json={
                    "image_path": image_path,
                    "image_url": image_url,
                    "confidence_threshold": confidence_threshold
                }
            )
            response.raise_for_status()
            result = response.json()

            if result.get("status") == "success":
                return {
                    "status": "success",
                    "message": "Inference completed successfully",
                    "annotated_image": result.get("annotated_image"),
                    "predictions": result.get("predictions"),
                    "task_type": result.get("task_type"),
                    "model_name": result.get("model_name")
                }
            else:
                return result

    except Exception as e:
        return {"status": "error", "message": str(e)}


async def cv_list_models(user_id: int, params: Dict[str, Any]) -> Dict:
    """Agent tool: List available CV models."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CV_SERVICE_URL}/inference/models/saved")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e), "saved_models": {}}
