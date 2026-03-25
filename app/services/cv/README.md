# CV Service - Computer Vision Microservice

**A unified microservice for computer vision training and inference, designed to run with GPU support.**

---

## Overview

The CV Service is a standalone microservice that provides:
- **Model Training**: Classification, detection, and segmentation
- **Real-time Inference**: Webcam streaming with model predictions
- **Model Management**: Load, save, and switch between trained models

Runs on a **single port (8080)** with proper routing for both training and inference.

---

## Quick Start

### Local Development (CPU)

```bash
cd warpcore/app/services/cv

# Install dependencies with UV
uv pip install -r requirements.txt

# Run the service
python main.py --port 8080
```

### Docker (CPU)

```bash
# Build and run
docker-compose up -d cv-service

# Check health
curl http://localhost:8080/health
```

### Docker (GPU - NVIDIA)

```bash
# Requires NVIDIA Docker runtime
docker-compose --profile gpu up -d

# Verify GPU access
curl http://localhost:8080/health
# Returns: {"status":"healthy","gpu_available":true,"device":"cuda"}
```

---

## API Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with GPU status |
| `/alive` | GET | Legacy alive check |

### Training

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/training/tasks` | GET | Get available tasks and models |
| `/training/train` | POST | Start model training |

### Inference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/inference/models/available` | GET | List available model architectures |
| `/inference/models/current` | GET | Get currently loaded model info |
| `/inference/models/load` | POST | Load a model for inference |
| `/inference/models/saved` | GET | List saved model files |
| `/inference/video_feed` | GET | MJPEG video stream |
| `/inference/detection/latest` | GET | Latest detection results |
| `/inference/detection/stream` | WebSocket | Real-time detection stream |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CV_MODEL_BASE_PATH` | `./saved_models` | Path for saved models |
| `PYTHONUNBUFFERED` | `1` | Unbuffered Python output |

### Command Line Arguments

```bash
python main.py \
    --port 8080 \           # Service port
    --host 0.0.0.0 \        # Bind address
    --reload \              # Auto-reload for development
    --task classification \ # Preload model task type
    --model resnet \        # Preload model name
    --model-path ./model.pt # Preload model path
```

---

## Integration with WarpCore

Set the `CV_SERVICE_URL` environment variable in your warpcore `.env`:

```env
CV_SERVICE_URL=http://localhost:8080
```

The warpcore backend will proxy requests through `/api/cv/*` to the CV service.

---

## AWS GPU Deployment

See [AWS_GPU_DEPLOYMENT.md](./AWS_GPU_DEPLOYMENT.md) for detailed instructions on:
- Selecting GPU instances (g4dn, g5, p3, p4d)
- Setting up NVIDIA Docker runtime
- Cost optimization with Spot instances
- Monitoring and troubleshooting

---

## Supported Models

### Classification
ResNet, EfficientNet, VGG, Inception, MobileNet, DenseNet, ViT, ConvNeXt

### Detection
YOLOv3/v4/v5/v8, Faster R-CNN, SSD, RetinaNet, EfficientDet, DETR, Mask R-CNN

### Segmentation
UNet, DeepLabv3, PSPNet, SegNet, FCN, Mask R-CNN, YOLACT, SegFormer, Mask2Former

---

## Project Structure

```
cv/
├── main.py                 # Unified FastAPI application
├── requirements.txt        # Python dependencies (UV compatible)
├── Dockerfile              # Multi-stage build (CPU & GPU)
├── docker-compose.yml      # Container orchestration
├── AWS_GPU_DEPLOYMENT.md   # AWS deployment guide
├── training/
│   ├── visiontrain.py      # Training logic and models
│   └── arch.py             # Model architectures
├── inference/
│   ├── inference_engine.py # Inference engine
│   └── unified_stream.py   # Video streaming
└── saved_models/           # Trained model storage
```

---

## License

MIT License