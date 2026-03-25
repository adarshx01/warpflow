import torch
import cv2
import os
import asyncio
import numpy as np
from fastapi import FastAPI, Query, HTTPException, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from typing import Optional, Dict, Any, List
import argparse
from inference_engine import InferenceEngine, TASKS
import json
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

inference_engine = None
model_registry = {}  
connected_clients: List[WebSocket] = []
latest_detection_results = []  
last_detection_timestamp = 0  

DEFAULT_MODEL_BASE_PATH = "/home/adarsh/WorkSpace/VisionFlow/saved_models"
DEFAULT_DATASET_PATH = "/home/adarsh/WorkSpace/VisionFlow/facialemotion"

async def generate_frames():
    """Generator for webcam frames with model inference."""
    global latest_detection_results, last_detection_timestamp

    video_sources = [0, 1, '/dev/video0', '/dev/video1']
    cap = None
    
    for source in video_sources:
        try:
            print(f"Attempting to open video source: {source}")
            cap = cv2.VideoCapture(source)
            if cap.isOpened():
                print(f"Successfully opened video source: {source}")
                break
        except Exception as e:
            print(f"Failed to open video source {source}: {e}")
    
    if cap is None or not cap.isOpened():
        print("Error: Could not open any webcam. Using placeholder image.")
        while True:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.rectangle(frame, (100, 100), (300, 300), (0, 0, 255), -1)
            cv2.circle(frame, (450, 200), 80, (0, 255, 0), -1)
            cv2.putText(frame, "Test Image - No Camera", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            if inference_engine:
                processed_frame, results = inference_engine.process_frame(frame)
                if results:
                    latest_detection_results = results
                    last_detection_timestamp = time.time()
            else:
                processed_frame = frame.copy()
                cv2.putText(processed_frame, "No model loaded", (50, 400), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            ret, buffer = cv2.imencode(".jpg", processed_frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            await asyncio.sleep(0.1)
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame.")
                break

            if inference_engine:
                processed_frame, results = inference_engine.process_frame(frame)
                if results:
                    latest_detection_results = results
                    last_detection_timestamp = time.time()
            else:
                processed_frame = frame.copy()
                cv2.putText(processed_frame, "No model loaded", (50, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            ret, buffer = cv2.imencode(".jpg", processed_frame)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            await asyncio.sleep(0.03)

    finally:
        cap.release()

@app.get("/video_feed")
async def video_feed():
    """Endpoint for video streaming with inference results."""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/models/available")
async def get_available_models():
    """Get all available models grouped by task type."""
    return {"tasks": TASKS}

@app.get("/api/models/current")
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

@app.post("/api/models/load")
async def load_model(
    task_type: str = Body(..., description="Task type (classification, detection, segmentation)"),
    model_name: str = Body(..., description="Model name"),
    model_path: str = Body(None, description="Path to model weights (.pt file)"),
    dataset_path: str = Body(None, description="Path to dataset (for class names)"),
    num_classes: int = Body(None, description="Number of classes")
):
    """Load a model for inference via API."""
    global inference_engine
    
    print(f"\n=== Loading model with parameters: ===")
    print(f"  Task Type: {task_type}")
    print(f"  Model Name: {model_name}")
    print(f"  Model Path: {model_path}")
    print(f"  Dataset Path: {dataset_path}")
    print(f"  Num Classes: {num_classes}")
    
    if task_type not in TASKS:
        return {"status": "error", "message": f"Invalid task type: {task_type}"}
    
    if model_name not in TASKS[task_type]:
        return {"status": "error", "message": f"Invalid model name: {model_name} for task: {task_type}"}
    
    if not model_path:
        if task_type == "segmentation":
            return {"status": "error", "message": "Model path is required for segmentation tasks"}
        else:
            model_path = f"{DEFAULT_MODEL_BASE_PATH}/{task_type}/{model_name}_sgd_20250419_141127.pt"
    
    if not os.path.exists(model_path):
        return {"status": "error", "message": f"Model file not found at: {model_path}"}
    
    if task_type == "segmentation" and not num_classes:
        return {"status": "error", "message": "Number of classes must be specified for segmentation tasks"}
    
    try:
        model_key = f"{task_type}_{model_name}_{model_path}_{dataset_path}_{num_classes}"
        
        if model_key in model_registry:
            inference_engine = model_registry[model_key]
            print(f"Using cached model: {model_name}")
        else:
            inference_engine = InferenceEngine(
                task_type=task_type,
                model_name=model_name,
                model_path=model_path,
                dataset_path=dataset_path,
                num_classes=num_classes
            )
            model_registry[model_key] = inference_engine
            print(f"Loaded new model: {model_name}")
        
        return {
            "status": "success",
            "message": f"Model loaded successfully: {model_name}",
            "details": {
                "task_type": task_type,
                "model_name": model_name,
                "model_path": model_path,
                "dataset_path": dataset_path,
                "num_classes": num_classes
            }
        }
        
    except Exception as e:
        import traceback
        print(f"\n❌ Error loading model: {str(e)}")
        print("\nDetailed error traceback:")
        traceback.print_exc()
        
        return {
            "status": "error",
            "message": f"Error loading model: {str(e)}"
        }

@app.get("/api/models/saved")
async def get_saved_models():
    """Get list of saved model files in the default directory."""
    saved_models = {}
    
    try:
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

@app.get("/")
async def get_index():
    """Home page with video stream display."""
    task_type = "unknown"
    model_name = "unknown"
    
    if inference_engine:
        task_type = inference_engine.task_type
        model_name = inference_engine.model_name
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Unified Model Streaming</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            .stream {{ margin-top: 20px; }}
            .stream img {{ max-width: 100%; border: 1px solid #ddd; }}
            .info {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>Live Stream with {model_name.upper()} Inference</h1>
        <div class="info">
            <p><strong>Task:</strong> {task_type}</p>
            <p><strong>Model:</strong> {model_name}</p>
        </div>
        <div class="stream">
            <img src="/video_feed" alt="Video Stream">
        </div>
    </body>
    </html>
    """
    return StreamingResponse(content=iter([html_content]), media_type="text/html")

@app.get("/api/detection/latest")
async def get_latest_detection():
    """Get the latest detection results as JSON with simplified structure."""
    global latest_detection_results, last_detection_timestamp
    
    try:
        if not latest_detection_results or (time.time() - last_detection_timestamp > 5):
            t = time.time()
            return {
                "status": "simulated",
                "regions": {
                    "topLeft": 0,
                    "top": 0,
                    "topRight": 0,
                    "left": 0,
                    "center": 1, 
                    "right": 0,
                    "bottomLeft": 0,
                    "bottom": 0,
                    "bottomRight": 0
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
        

        simplified_detections = []
        regions = {
            "topLeft": 0, "top": 0, "topRight": 0,
            "left": 0, "center": 0, "right": 0,
            "bottomLeft": 0, "bottom": 0, "bottomRight": 0
        }
        
        primary_detection = None
        max_confidence = -1
        
        if isinstance(latest_detection_results, list):
            for idx, detection in enumerate(latest_detection_results):
                if not isinstance(detection, dict) or 'bbox' not in detection:
                    continue
                
                bbox = detection['bbox']
                if isinstance(bbox, np.ndarray):
                    bbox = bbox.tolist()
                
                if not (isinstance(bbox, list) and len(bbox) >= 4):
                    continue
                
                x1, y1, x2, y2 = [int(val) if isinstance(val, (np.integer, np.floating)) else int(val) for val in bbox[:4]]
                
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                width = x2 - x1
                height = y2 - y1
                
                confidence = 0.0
                if 'confidence' in detection:
                    confidence = float(detection['confidence']) if isinstance(detection['confidence'], (np.floating, float)) else 0.0
                
                class_id = 0
                if 'class' in detection:
                    class_id = int(detection['class']) if isinstance(detection['class'], (np.integer, int)) else 0
                
                clean_detection = {
                    "x": center_x,
                    "y": center_y,
                    "width": width,
                    "height": height,
                    "confidence": confidence,
                    "class": class_id
                }
                
                simplified_detections.append(clean_detection)
                
                if confidence > max_confidence:
                    max_confidence = confidence
                    primary_detection = clean_detection
                
                region_name = "center" 
                
                if center_x < 213:
                    if center_y < 160: 
                        region_name = "topLeft"
                    elif center_y < 320:
                        region_name = "left"
                    else:
                        region_name = "bottomLeft"
                elif center_x < 427:
                    if center_y < 160:
                        region_name = "top"
                    elif center_y < 320:
                        region_name = "center"
                    else:
                        region_name = "bottom"
                else:
                    if center_y < 160:
                        region_name = "topRight"
                    elif center_y < 320:
                        region_name = "right"
                    else:
                        region_name = "bottomRight"
                
                regions[region_name] += 1
                
        elif isinstance(latest_detection_results, dict):
            regions["center"] = 1
            primary_detection = {
                "x": 320,
                "y": 240,
                "width": 100,
                "height": 100,
                "confidence": 0.9,
                "class": 0
            }
        
        if primary_detection is None:
            primary_detection = {
                "x": 320,
                "y": 240,
                "width": 0,
                "height": 0,
                "confidence": 0.0,
                "class": 0
            }
        
        return {
            "status": "success",
            "regions": regions,
            "detections": simplified_detections,
            "primaryDetection": primary_detection
        }
    
    except Exception as e:
        import traceback
        print(f"Error in get_latest_detection: {e}")
        traceback.print_exc()
        
        return {
            "status": "error",
            "message": str(e),
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

@app.websocket("/api/detection/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            
            if inference_engine and hasattr(inference_engine, 'latest_results'):
                await websocket.send_json({
                    "detection_results": inference_engine.latest_results
                })
            else:
                await websocket.send_json({
                    "status": "no_data"
                })
            
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print("Client disconnected from WebSocket")
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)

def init_inference_engine(task_type, model_name, model_path, dataset_path=None, num_classes=None):
    """Initialize the inference engine with the specified model."""
    global inference_engine
    try:
        inference_engine = InferenceEngine(
            task_type=task_type,
            model_name=model_name,
            model_path=model_path,
            dataset_path=dataset_path,
            num_classes=num_classes
        )
        print(f"Initialized {model_name} model for {task_type}")
        
        model_key = f"{task_type}_{model_name}_{model_path}_{dataset_path}_{num_classes}"
        model_registry[model_key] = inference_engine
    except Exception as e:
        print(f"Error initializing inference engine: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    import traceback
    
    parser = argparse.ArgumentParser(description="Unified Vision Model Streaming")
    parser.add_argument("--task", type=str, 
                        choices=["classification", "detection", "segmentation"],
                        help="Task type (classification, detection, segmentation)")
    parser.add_argument("--model", type=str,
                        help="Model name (e.g., resnet, yolov5, deeplabv3)")
    parser.add_argument("--model-path", type=str,
                        help="Path to model weights (.pt file)")
    parser.add_argument("--dataset", type=str, default=None, 
                        help="Path to dataset (for class names)")
    parser.add_argument("--num-classes", type=int, default=None, 
                        help="Number of classes")
    parser.add_argument("--port", type=int, default=8001, 
                        help="Port for the FastAPI server")
    parser.add_argument("--urdfJoints",type=str,default=0,
                        help="URDF joints for the model")
    parser.add_argument("--urdfJointsPath",type=str,default=0,
                        help="URDF joints path for the model")
    
    args = parser.parse_args()
    
    if args.task and args.model and args.model_path:
        try:
            print(f"\nInitializing model with the following configuration:")
            print(f"  Task: {args.task}")
            print(f"  Model: {args.model}")
            print(f"  Model Path: {args.model_path}")
            print(f"  Dataset Path: {args.dataset}")
            print(f"  Number of Classes: {args.num_classes}\n")
            print(f"  URDF Joints: {args.urdfJoints}")
            print(f"  URDF Joints Path: {args.urdfJointsPath}")
            print("Initializing inference engine...")
            
            init_inference_engine(
                task_type=args.task,
                model_name=args.model,
                model_path=args.model_path,
                dataset_path=args.dataset,
                num_classes=args.num_classes
            )
            
            print(f"\n✅ Model initialized successfully: {args.model} for {args.task}")
            
            if inference_engine is None:
                print("⚠️ Warning: Model initialization function completed but inference_engine is still None")
            else:
                print(f"Model details:")
                print(f"  - Task type: {inference_engine.task_type}")
                print(f"  - Model name: {inference_engine.model_name}")
                print(f"  - Device: {inference_engine.device}")
                if hasattr(inference_engine, 'class_names') and inference_engine.class_names:
                    print(f"  - Classes: {len(inference_engine.class_names)}")
                
        except Exception as e:
            print(f"\n❌ Error initializing inference engine: {e}")
            print("\nDetailed error traceback:")
            traceback.print_exc()
            print("\nStarting server without a model - you can load one via the API")
    else:
        missing = []
        if not args.task: missing.append("--task")
        if not args.model: missing.append("--model")
        if not args.model_path: missing.append("--model-path")
        
        if missing:
            print(f"\nℹ️ No model specified via command line. Missing parameters: {', '.join(missing)}")
        print("You can load a model through the web interface or API.")
    
    # Start the server
    print(f"\nStarting server on port {args.port}")
    print(f"Access the web interface at http://localhost:{args.port}")
    uvicorn.run(app, host="0.0.0.0", port=args.port)