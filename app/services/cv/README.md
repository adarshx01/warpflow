# Stratify Labs Vision Platform

**A comprehensive platform for computer vision tasks including training, inference, and model management.**

---

## 🌟 Features

- **Training Service**: Train models for classification, detection, and segmentation tasks.
- **Inference Service**: Perform real-time inference with webcam or video inputs.
- **Model Management**: Load, save, and switch between different models.
- **Unified Interface**: Control both services from a single application.

---

## 🛠 Installation

### Prerequisites

- Python 3.10+
- CUDA-compatible GPU (recommended for training)

### Setup

```bash
git clone https://github.com/adarshx01/StratifyLabs.git
cd StratifyLabs-Server
pip install -r requirements.txt
```

---

## 🚀 Usage

### Running the Application

```bash
# Start both training and inference services
python main.py

# Start only the inference service
python main.py --disable-training

# Start only the training service
python main.py --disable-inference
```

### Command-Line Arguments

- `--inference-port`: Port for inference service (default: 8001)
- `--training-port`: Port for training service (default: 8000)
- `--disable-inference`: Disable the inference service
- `--disable-training`: Disable the training service
- `--model`: Model name for inference
- `--task`: Task type (`classification`, `detection`, `segmentation`)
- `--model-path`: Path to the model weights file
- `--dataset`: Path to dataset for class names
- `--num-classes`: Number of classes (for segmentation)

### Using Docker

```bash
# Build the Docker image
docker build -t stratify-vision .

# Run the container
docker run -p 8000:8000 -p 8001:8001 stratify-vision
```

---

## 📡 API Endpoints

### Training Service

- `GET /alive`: Check if the training service is running
- `POST /train`: Start training a model

### Inference Service

- `GET /video_feed`: Stream video with inference results
- `GET /api/models/available`: Get list of available models
- `GET /api/models/current`: Get currently loaded model info
- `POST /api/models/load`: Load a model for inference
- `GET /api/detection/latest`: Fetch latest detection results
- `WebSocket /api/detection/stream`: Stream detection results in real-time

---

## ✅ Supported Models

### Classification

- ResNet  
- EfficientNet  
- VGG  
- Inception  
- MobileNet  
- DenseNet  
- ViT  
- ConvNeXt

### Detection

- YOLOv3/v4/v5/v8  
- Faster R-CNN  
- SSD  
- RetinaNet  
- EfficientDet  
- DETR  
- Mask R-CNN

### Segmentation

- UNet  
- DeepLabv3  
- PSPNet  
- SegNet  
- FCN  
- Mask R-CNN  
- YOLACT  
- SegFormer  
- Mask2Former

---

## 📄 License

This project is licensed under the **MIT License**.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.