"""
Unified CV Service - Computer Vision Training and Inference Microservice
Runs on a single port (default 8080) with proper routing for both services.
"""
import os
import sys
import asyncio
import argparse
import time
from typing import Optional, List, Dict, Any

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
import numpy as np
import cv2
from PIL import Image

from fastapi import FastAPI, HTTPException, Body, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

import uvicorn

# ─── Constants ────────────────────────────────────────────────────────────────

TASKS = {
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

OPTIMIZERS = ["sgd", "adam", "rmsprop", "adagrad", "adamw"]

DEFAULT_MODEL_BASE_PATH = os.environ.get(
    "CV_MODEL_BASE_PATH",
    os.path.join(os.path.dirname(__file__), "saved_models")
)

# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="CV Service",
    description="Unified Computer Vision Training and Inference Microservice",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global State ─────────────────────────────────────────────────────────────

inference_engine = None
model_registry: Dict[str, Any] = {}
connected_clients: List[WebSocket] = []
latest_detection_results = []
last_detection_timestamp = 0
active_training_jobs: Dict[str, Dict] = {}

# ─── Request/Response Schemas ─────────────────────────────────────────────────

class TrainRequest(BaseModel):
    task: str
    model: str
    optimizer: str = "adam"
    train_pct: float = 0.7
    val_pct: float = 0.15
    test_pct: float = 0.15
    dataset_path: str
    epochs: int = 10


class TrainResponse(BaseModel):
    status: str
    model_saved_at: Optional[str] = None
    message: Optional[str] = None


class LoadModelRequest(BaseModel):
    task_type: str
    model_name: str
    model_path: Optional[str] = None
    dataset_path: Optional[str] = None
    num_classes: Optional[int] = None


# ─── Health & Status Endpoints ────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "cv",
        "gpu_available": torch.cuda.is_available(),
        "device": "cuda" if torch.cuda.is_available() else "cpu"
    }


@app.get("/alive")
async def alive():
    """Legacy alive check for backwards compatibility."""
    return {"status": "alive"}


# ─── Training Endpoints ───────────────────────────────────────────────────────

@app.get("/training/tasks")
async def get_tasks():
    """Get available tasks and models."""
    return {"tasks": TASKS, "optimizers": OPTIMIZERS}


@app.post("/training/train", response_model=TrainResponse)
async def train_model(request: TrainRequest, background_tasks: BackgroundTasks):
    """Start model training."""
    # Validate request
    if request.task.lower() not in TASKS:
        raise HTTPException(status_code=400, detail=f"Invalid task: {request.task}")
    if request.model.lower() not in TASKS[request.task.lower()]:
        raise HTTPException(status_code=400, detail=f"Invalid model: {request.model} for task {request.task}")
    if request.optimizer.lower() not in OPTIMIZERS:
        raise HTTPException(status_code=400, detail=f"Invalid optimizer: {request.optimizer}")

    total = request.train_pct + request.val_pct + request.test_pct
    if not (0.99 <= total <= 1.01):
        raise HTTPException(status_code=400, detail="Train, validation, and test percentages must sum to 1.0")

    if not os.path.exists(request.dataset_path):
        raise HTTPException(status_code=400, detail=f"Dataset path does not exist: {request.dataset_path}")

    if request.epochs <= 0:
        raise HTTPException(status_code=400, detail="Number of epochs must be greater than 0")

    try:
        # Import training module
        from training.visiontrain import get_task

        task = get_task(
            request.task, request.model, request.optimizer,
            request.train_pct, request.val_pct, request.test_pct,
            request.dataset_path, request.epochs
        )
        model_path = task.train()

        return TrainResponse(
            status="Training completed successfully",
            model_saved_at=model_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during training: {str(e)}")


# ─── Inference Endpoints ──────────────────────────────────────────────────────

@app.get("/inference/models/available")
async def get_available_models():
    """Get all available models grouped by task type."""
    return {"tasks": TASKS}


@app.get("/inference/models/current")
async def get_current_model():
    """Get information about the currently active model."""
    if inference_engine is None:
        return {"status": "no_model", "message": "No model is currently loaded"}

    return {
        "status": "active",
        "task_type": inference_engine.task_type,
        "model_name": inference_engine.model_name,
        "model_path": inference_engine.model_path,
        "dataset_path": inference_engine.dataset_path,
        "num_classes": inference_engine.num_classes
    }


@app.post("/inference/models/load")
async def load_model(request: LoadModelRequest):
    """Load a model for inference."""
    global inference_engine

    if request.task_type not in TASKS:
        return {"status": "error", "message": f"Invalid task type: {request.task_type}"}

    if request.model_name not in TASKS[request.task_type]:
        return {"status": "error", "message": f"Invalid model name: {request.model_name}"}

    if not request.model_path:
        if request.task_type == "segmentation":
            return {"status": "error", "message": "Model path is required for segmentation tasks"}
        else:
            request.model_path = f"{DEFAULT_MODEL_BASE_PATH}/{request.task_type}/{request.model_name}_sgd.pt"

    if not os.path.exists(request.model_path):
        return {"status": "error", "message": f"Model file not found at: {request.model_path}"}

    if request.task_type == "segmentation" and not request.num_classes:
        return {"status": "error", "message": "Number of classes must be specified for segmentation tasks"}

    try:
        from inference.inference_engine import InferenceEngine

        model_key = f"{request.task_type}_{request.model_name}_{request.model_path}_{request.dataset_path}_{request.num_classes}"

        if model_key in model_registry:
            inference_engine = model_registry[model_key]
            print(f"Using cached model: {request.model_name}")
        else:
            inference_engine = InferenceEngine(
                task_type=request.task_type,
                model_name=request.model_name,
                model_path=request.model_path,
                dataset_path=request.dataset_path,
                num_classes=request.num_classes
            )
            model_registry[model_key] = inference_engine
            print(f"Loaded new model: {request.model_name}")

        return {
            "status": "success",
            "message": f"Model loaded successfully: {request.model_name}",
            "details": {
                "task_type": request.task_type,
                "model_name": request.model_name,
                "model_path": request.model_path,
                "dataset_path": request.dataset_path,
                "num_classes": request.num_classes
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Error loading model: {str(e)}"}


@app.get("/inference/models/saved")
async def get_saved_models():
    """Get list of saved model files."""
    saved_models = {}

    try:
        if os.path.exists(DEFAULT_MODEL_BASE_PATH):
            for task in os.listdir(DEFAULT_MODEL_BASE_PATH):
                task_dir = os.path.join(DEFAULT_MODEL_BASE_PATH, task)
                if os.path.isdir(task_dir):
                    saved_models[task] = []
                    for model_file in os.listdir(task_dir):
                        if model_file.endswith('.pt'):
                            model_name = model_file.split('_')[0]
                            saved_models[task].append({
                                "name": model_name,
                                "file": model_file,
                                "path": os.path.join(task_dir, model_file)
                            })
    except Exception as e:
        print(f"Error scanning saved models: {e}")

    return {"saved_models": saved_models}


@app.get("/inference/video_feed")
async def video_feed():
    """MJPEG video stream with inference results."""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.post("/inference/process_image")
async def process_image(
    image_path: Optional[str] = Body(None),
    image_url: Optional[str] = Body(None),
    confidence_threshold: float = Body(0.5)
):
    """Process a single image and return annotated results."""
    global inference_engine

    if inference_engine is None:
        return {
            "status": "error",
            "message": "No model loaded. Please load a model first."
        }

    try:
        import base64
        import httpx
        import tempfile

        # Load image from path or URL
        if image_url:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url)
                response.raise_for_status()

                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                    f.write(response.content)
                    image_path = f.name

        if not image_path or not os.path.exists(image_path):
            return {
                "status": "error",
                "message": f"Image not found: {image_path}"
            }

        # Read and process the image
        frame = cv2.imread(image_path)
        if frame is None:
            return {
                "status": "error",
                "message": "Failed to read image file"
            }

        # Process with the model
        inference_engine.detection_threshold = confidence_threshold
        processed_frame, results = inference_engine.process_frame(frame)

        # Encode the processed frame to base64
        _, buffer = cv2.imencode('.jpg', processed_frame)
        annotated_image_base64 = base64.b64encode(buffer).decode('utf-8')

        return {
            "status": "success",
            "annotated_image": f"data:image/jpeg;base64,{annotated_image_base64}",
            "predictions": results,
            "task_type": inference_engine.task_type,
            "model_name": inference_engine.model_name
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/inference/detection/latest")
async def get_latest_detection():
    """Get the latest detection results."""
    global latest_detection_results, last_detection_timestamp

    try:
        if not latest_detection_results or (time.time() - last_detection_timestamp > 5):
            t = time.time()
            return {
                "status": "simulated",
                "regions": {
                    "topLeft": 0, "top": 0, "topRight": 0,
                    "left": 0, "center": 1, "right": 0,
                    "bottomLeft": 0, "bottom": 0, "bottomRight": 0
                },
                "primaryDetection": {
                    "x": int(320 + 200 * np.sin(t * 0.5)),
                    "y": int(240 + 150 * np.cos(t * 0.7)),
                    "width": 100,
                    "height": 100,
                    "confidence": float(0.85 + 0.1 * np.sin(t)),
                    "class": 0
                }
            }

        # Process real detection results
        simplified_detections = []
        regions = {
            "topLeft": 0, "top": 0, "topRight": 0,
            "left": 0, "center": 0, "right": 0,
            "bottomLeft": 0, "bottom": 0, "bottomRight": 0
        }

        primary_detection = None
        max_confidence = -1

        if isinstance(latest_detection_results, list):
            for detection in latest_detection_results:
                if not isinstance(detection, dict) or 'bbox' not in detection:
                    continue

                bbox = detection['bbox']
                if isinstance(bbox, np.ndarray):
                    bbox = bbox.tolist()

                if not (isinstance(bbox, list) and len(bbox) >= 4):
                    continue

                x1, y1, x2, y2 = [int(val) for val in bbox[:4]]
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                width = x2 - x1
                height = y2 - y1

                confidence = float(detection.get('confidence', 0.0))
                class_id = int(detection.get('class', 0))

                clean_detection = {
                    "x": center_x, "y": center_y,
                    "width": width, "height": height,
                    "confidence": confidence, "class": class_id
                }
                simplified_detections.append(clean_detection)

                if confidence > max_confidence:
                    max_confidence = confidence
                    primary_detection = clean_detection

        if primary_detection is None:
            primary_detection = {
                "x": 320, "y": 240, "width": 0, "height": 0,
                "confidence": 0.0, "class": 0
            }

        return {
            "status": "success",
            "regions": regions,
            "detections": simplified_detections,
            "primaryDetection": primary_detection
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error", "message": str(e),
            "regions": {
                "topLeft": 0, "top": 0, "topRight": 0,
                "left": 0, "center": 1, "right": 0,
                "bottomLeft": 0, "bottom": 0, "bottomRight": 0
            },
            "primaryDetection": {
                "x": 320, "y": 240, "width": 50, "height": 50,
                "confidence": 0.5, "class": 0
            }
        }


@app.websocket("/inference/detection/stream")
async def websocket_detection_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time detection stream."""
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
            if inference_engine and hasattr(inference_engine, 'latest_results'):
                await websocket.send_json({"detection_results": inference_engine.latest_results})
            else:
                await websocket.send_json({"status": "no_data"})
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)


# ─── Legacy Routes (for backwards compatibility) ──────────────────────────────

@app.post("/train")
async def legacy_train(request: TrainRequest, background_tasks: BackgroundTasks):
    """Legacy training endpoint."""
    return await train_model(request, background_tasks)


@app.get("/api/models/available")
async def legacy_available_models():
    """Legacy endpoint."""
    return await get_available_models()


@app.get("/api/models/current")
async def legacy_current_model():
    """Legacy endpoint."""
    return await get_current_model()


@app.post("/api/models/load")
async def legacy_load_model(request: LoadModelRequest):
    """Legacy endpoint."""
    return await load_model(request)


@app.get("/api/models/saved")
async def legacy_saved_models():
    """Legacy endpoint."""
    return await get_saved_models()


@app.get("/video_feed")
async def legacy_video_feed():
    """Legacy endpoint."""
    return await video_feed()


@app.get("/api/detection/latest")
async def legacy_latest_detection():
    """Legacy endpoint."""
    return await get_latest_detection()


# ─── Video Frame Generator ────────────────────────────────────────────────────

async def generate_frames():
    """Generator for webcam frames with model inference."""
    global latest_detection_results, last_detection_timestamp

    video_sources = [0, 1, '/dev/video0', '/dev/video1']
    cap = None

    for source in video_sources:
        try:
            cap = cv2.VideoCapture(source)
            if cap.isOpened():
                print(f"Opened video source: {source}")
                break
        except Exception:
            pass

    if cap is None or not cap.isOpened():
        # Fallback to placeholder
        while True:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "No Camera - Test Mode", (50, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            ret, buffer = cv2.imencode(".jpg", frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            await asyncio.sleep(0.1)
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if inference_engine:
                processed_frame, results = inference_engine.process_frame(frame)
                if results:
                    latest_detection_results = results
                    last_detection_timestamp = time.time()
            else:
                processed_frame = frame
                cv2.putText(processed_frame, "No model loaded", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            ret, buffer = cv2.imencode(".jpg", processed_frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            await asyncio.sleep(0.03)
    finally:
        cap.release()


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CV Service - Training and Inference Microservice")
    parser.add_argument("--port", type=int, default=8080, help="Port to run the service on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    # Optional: preload a model for inference
    parser.add_argument("--task", type=str, choices=["classification", "detection", "segmentation"],
                        help="Preload model task type")
    parser.add_argument("--model", type=str, help="Preload model name")
    parser.add_argument("--model-path", type=str, help="Preload model path")
    parser.add_argument("--dataset", type=str, help="Dataset path for class names")
    parser.add_argument("--num-classes", type=int, help="Number of classes")

    args = parser.parse_args()

    # Preload model if specified
    if args.task and args.model and args.model_path:
        print(f"Preloading model: {args.model} for {args.task}")
        try:
            from inference.inference_engine import InferenceEngine
            global inference_engine
            inference_engine = InferenceEngine(
                task_type=args.task,
                model_name=args.model,
                model_path=args.model_path,
                dataset_path=args.dataset,
                num_classes=args.num_classes
            )
            print(f"Model preloaded successfully")
        except Exception as e:
            print(f"Failed to preload model: {e}")

    print(f"\n{'='*60}")
    print(f"  CV Service starting on http://{args.host}:{args.port}")
    print(f"  GPU Available: {torch.cuda.is_available()}")
    print(f"{'='*60}\n")

    uvicorn.run(
        "main:app" if args.reload else app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
