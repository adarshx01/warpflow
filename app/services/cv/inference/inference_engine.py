import torch
import torch.nn as nn
import cv2
import numpy as np
import os
from torchvision import transforms, models
from PIL import Image
from typing import Dict, List, Tuple, Optional, Any, Union

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

CLASSIFICATION_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

class InferenceEngine:
    def __init__(self, task_type: str, model_name: str, model_path: str, 
                 dataset_path: Optional[str] = None, num_classes: Optional[int] = None):
        """
        Initialize the inference engine.
        
        Args:
            task_type: Type of task ('classification', 'detection', or 'segmentation')
            model_name: Name of the model architecture
            model_path: Path to the saved model weights
            dataset_path: Path to dataset (for class names in classification)
            num_classes: Number of classes (used if dataset_path is None)
        """
        self.task_type = task_type.lower()
        self.model_name = model_name.lower()
        self.model_path = model_path
        self.dataset_path = dataset_path
        self.num_classes = num_classes
        
        print(f"\nInitializing Inference Engine:")
        print(f"  Task Type: {self.task_type}")
        print(f"  Model: {self.model_name}")
        print(f"  Model Path: {self.model_path}")
        print(f"  Dataset Path: {self.dataset_path}")
        print(f"  Num Classes: {self.num_classes}")
        
        if self.task_type not in TASKS:
            raise ValueError(f"Task type '{task_type}' not supported")
        if self.model_name not in TASKS[self.task_type]:
            raise ValueError(f"Model '{model_name}' not supported for task '{task_type}'")
        
        if self.task_type == "segmentation" and self.num_classes is None:
            raise ValueError("Number of classes must be specified for segmentation tasks")
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"  Using device: {self.device}")
        
        self.class_names = None
        if self.task_type == "classification" and self.dataset_path:
            if os.path.exists(self.dataset_path):
                self.class_names = sorted(os.listdir(self.dataset_path))
                if self.num_classes and len(self.class_names) != self.num_classes:
                    print(f"Warning: Found {len(self.class_names)} classes, but expected {self.num_classes}")
        
        try:
            print("  Loading model...")
            self.model = self._load_model()
            self.model.to(self.device)
            self.model.eval()
            print("  Model loaded successfully")
        except Exception as e:
            import traceback
            print(f"❌ Error loading model: {str(e)}")
            traceback.print_exc()
            raise RuntimeError(f"Failed to load model: {str(e)}")
        
        self.preprocess = self._get_preprocessor()
        
        self.detection_threshold = 0.5
        self.face_detector = None
        if self.task_type == "classification":
            self.face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    def _load_model(self) -> nn.Module:
        """Load and configure the appropriate model based on task type and model name."""
        import torch  
        model = None
        
        # CLASSIFICATION MODELS
        if self.task_type == "classification":
            if self.num_classes is None and self.dataset_path:
                self.num_classes = len(self.class_names)
            elif self.num_classes is None:
                raise ValueError("For classification, either num_classes or dataset_path must be provided")
                
            if self.model_name == "resnet":
                model = models.resnet50(weights=None)
                model.fc = nn.Linear(model.fc.in_features, self.num_classes)
            elif self.model_name == "efficientnet":
                model = models.efficientnet_b0(weights=None)
                model.classifier[1] = nn.Linear(model.classifier[1].in_features, self.num_classes)
            elif self.model_name == "vgg":
                model = models.vgg16(weights=None)
                model.classifier[6] = nn.Linear(model.classifier[6].in_features, self.num_classes)
            elif self.model_name == "inception":
                model = models.inception_v3(weights=None, aux_logits=False)
                model.fc = nn.Linear(model.fc.in_features, self.num_classes)
            elif self.model_name == "mobilenet":
                model = models.mobilenet_v2(weights=None)
                model.classifier[1] = nn.Linear(model.classifier[1].in_features, self.num_classes)
            elif self.model_name == "densenet":
                model = models.densenet121(weights=None)
                model.classifier = nn.Linear(model.classifier.in_features, self.num_classes)
            elif self.model_name == "vit":
                model = models.vit_b_16(weights=None)
                model.heads.head = nn.Linear(model.heads.head.in_features, self.num_classes)
            elif self.model_name == "convnext":
                model = models.convnext_tiny(weights=None)
                model.classifier[2] = nn.Linear(model.classifier[2].in_features, self.num_classes)
        
        # DETECTION MODELS
        elif self.task_type == "detection":
            if self.model_name == "fasterrcnn":
                model = models.detection.fasterrcnn_resnet50_fpn(weights=None)
            elif self.model_name == "ssd":
                model = models.detection.ssd300_vgg16(weights=None)
            elif self.model_name == "retinanet":
                model = models.detection.retinanet_resnet50_fpn(weights=None)
            elif self.model_name == "maskrcnn":
                model = models.detection.maskrcnn_resnet50_fpn(weights=None)
            elif self.model_name == "yolov5":
                try:
                    import torch.hub
                    model = torch.hub.load('ultralytics/yolov5', 'yolov5s')
                except Exception as e:
                    raise ImportError(f"Failed to load YOLOv5: {e}. Install with 'pip install yolov5'")
            elif self.model_name == "yolov8":
                try:
                    from ultralytics import YOLO
                    model = YOLO("yolov8n.pt")
                except Exception as e:
                    raise ImportError(f"Failed to load YOLOv8: {e}. Install with 'pip install ultralytics'")
            else:
                raise NotImplementedError(f"Detection model {self.model_name} not implemented yet")
        
        # SEGMENTATION MODELS
        elif self.task_type == "segmentation":
            if self.num_classes is None:
                raise ValueError("Number of classes must be specified for segmentation tasks")
            
            print(f"Loading segmentation model: {self.model_name} with {self.num_classes} classes")
            
            if self.model_name == "deeplabv3":
                model = models.segmentation.deeplabv3_resnet50(pretrained=False)
                model.classifier[4] = nn.Conv2d(256, self.num_classes, kernel_size=1)
                print(f"Modified DeepLabV3 classifier to output {self.num_classes} classes")
            elif self.model_name == "fcn":
                model = models.segmentation.fcn_resnet50(pretrained=False)
                model.classifier[4] = nn.Conv2d(512, self.num_classes, kernel_size=1)
                print(f"Modified FCN classifier to output {self.num_classes} classes")
            elif self.model_name == "unet":
                try:
                    import segmentation_models_pytorch as smp
                    model = smp.Unet(
                        encoder_name="resnet34",
                        encoder_weights=None,
                        in_channels=3,
                        classes=self.num_classes
                    )
                    print(f"Created UNet model with {self.num_classes} output classes")
                except ImportError:
                    raise ImportError("segmentation-models-pytorch not installed. Install with 'pip install segmentation-models-pytorch'")
            else:
                raise NotImplementedError(f"Segmentation model {self.model_name} not implemented yet")
        
        if model is not None:
            try:
                checkpoint = torch.load(self.model_path, map_location=self.device)
                
                print(f"Checkpoint keys: {list(checkpoint.keys()) if isinstance(checkpoint, dict) else 'Not a dict'}")
                
                if isinstance(checkpoint, dict):
                    if "model_state_dict" in checkpoint:
                        state_dict = checkpoint["model_state_dict"]
                    elif "state_dict" in checkpoint:
                        state_dict = checkpoint["state_dict"]
                    else:
                        state_dict = checkpoint
                else:
                    state_dict = checkpoint
                    
                try:
                    model.load_state_dict(state_dict)
                    print(f"Successfully loaded state dict directly")
                except Exception as e1:
                    print(f"First attempt failed: {e1}")
                    try:
                        model.load_state_dict({k.replace('module.', ''): v for k, v in state_dict.items()})
                        print(f"Successfully loaded state dict after removing 'module.' prefix")
                    except Exception as e2:
                        print(f"Second attempt failed: {e2}")
                        
                        try:
                            model_dict = model.state_dict()
                            pretrained_dict = {k: v for k, v in state_dict.items() if k in model_dict}
                            model_dict.update(pretrained_dict)
                            model.load_state_dict(model_dict)
                            print(f"Successfully loaded state dict with partial key matching ({len(pretrained_dict)}/{len(state_dict)} keys)")
                        except Exception as e3:
                            print(f"Third attempt failed: {e3}")
                            print("Warning: Could not fully load state dict, model may not work correctly")
                            
            except Exception as e:
                print(f"Error loading checkpoint: {e}")
                raise
        
        return model
    
    def _get_preprocessor(self):
        """Get the appropriate preprocessing pipeline for the model."""
        if self.task_type == "classification":
            return transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
        
        elif self.task_type == "detection":
            if self.model_name in ["fasterrcnn", "maskrcnn", "retinanet", "ssd"]:
                return transforms.Compose([
                    transforms.ToPILImage(),
                    transforms.ToTensor(),
                ])
            elif self.model_name in ["yolov5", "yolov8"]:
                return lambda x: x  
        
        elif self.task_type == "segmentation":
            if self.model_name in ["deeplabv3", "fcn"]:
                return transforms.Compose([
                    transforms.ToPILImage(),
                    transforms.Resize((256, 256), interpolation=transforms.InterpolationMode.BILINEAR),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                ])
            elif self.model_name == "unet":
                return transforms.Compose([
                    transforms.ToPILImage(),
                    transforms.Resize((256, 256), interpolation=transforms.InterpolationMode.BILINEAR),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                ])
            elif self.model_name == "maskrcnn":
                return transforms.Compose([
                    transforms.ToPILImage(),
                    transforms.ToTensor(),
                ])
        
        return transforms.Compose([transforms.ToPILImage(), transforms.ToTensor()])
    
    def detect_faces(self, frame):
        """Detect faces in a frame using OpenCV's Haar Cascades."""
        if self.face_detector is None:
            self.face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_detector.detectMultiScale(gray, 1.1, 4)
        return faces
    
    def process_frame(self, frame):
        """
        Process a frame with the appropriate model, showing proper visualizations.
        
        Args:
            frame: The input frame (OpenCV format BGR)
            
        Returns:
            processed_frame: Frame with predictions visualized
            results: Raw prediction results
        """
        processed_frame = frame.copy()
        results = None
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # CLASSIFICATION MODELS
        if self.task_type == "classification":
            if self.model_name in ["resnet", "vgg", "densenet"] and self.face_detector is not None:
                faces = self.detect_faces(frame)
                
                if len(faces) > 0:
                    results = []
                    for (x, y, w, h) in faces:
                        cv2.rectangle(processed_frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                        
                        face_roi = rgb_frame[y:y+h, x:x+w]
                        if face_roi.size > 0:  
                            input_tensor = self.preprocess(face_roi)
                            input_batch = input_tensor.unsqueeze(0).to(self.device)
                            
                            with torch.no_grad():
                                output = self.model(input_batch)
                                probabilities = torch.softmax(output, dim=1)[0]
                                _, predicted_idx = torch.max(output, 1)
                                predicted_class = predicted_idx.item()
                                confidence = probabilities[predicted_class].item()
                            
                            if self.class_names:
                                class_name = self.class_names[predicted_class]
                            else:
                                class_name = f"Class {predicted_class}"
                            
                            label = f"{class_name}: {confidence:.2f}"
                            cv2.putText(processed_frame, label, (x, y-10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            
                            bar_width = int(w * confidence)
                            cv2.rectangle(processed_frame, (x, y+h+5), (x+bar_width, y+h+10), (0, 255, 0), -1)
                            
                            results.append({
                                "bbox": (x, y, w, h),
                                "class": predicted_class,
                                "name": class_name,
                                "confidence": confidence
                            })
                    return processed_frame, results
                
 
            input_tensor = self.preprocess(rgb_frame)
            input_batch = input_tensor.unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                output = self.model(input_batch)
                probabilities = torch.softmax(output, dim=1)[0]
                values, indices = torch.topk(probabilities, k=min(3, len(probabilities)))
                
            results = []
            overlay = processed_frame.copy()
            cv2.rectangle(overlay, (10, 10), (300, 100), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, processed_frame, 0.4, 0, processed_frame)
            
            for i, (conf, idx) in enumerate(zip(values, indices)):
                class_idx = idx.item()
                confidence = conf.item()
                
                if self.class_names:
                    class_name = self.class_names[class_idx]
                else:
                    class_name = f"Class {class_idx}"
                
                label = f"{class_name}: {confidence:.2f}"
                cv2.putText(processed_frame, label, (15, 30 + i*20), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                results.append({
                    "class": class_idx,
                    "name": class_name,
                    "confidence": confidence
                })
        
        # DETECTION MODELS
        elif self.task_type == "detection":
            if self.model_name in ["fasterrcnn", "maskrcnn", "retinanet", "ssd"]:
                input_tensor = self.preprocess(rgb_frame)
                input_batch = input_tensor.unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    detections = self.model(input_batch)[0]
                
                results = []
                colors = [
                    (0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0),
                    (255, 0, 255), (0, 255, 255), (128, 0, 0), (0, 128, 0)
                ]
                
                for idx, (box, label, score) in enumerate(zip(detections['boxes'], detections['labels'], detections['scores'])):
                    if score > self.detection_threshold:
                        box = box.cpu().numpy().astype(np.int32)
                        label_idx = label.item()
                        score_val = score.item()
                        
                        color = colors[label_idx % len(colors)]
                        
                        cv2.rectangle(processed_frame, (box[0], box[1]), (box[2], box[3]), color, 2)
                        
                        # Draw filled rectangle for the text background
                        text = f"Class {label_idx}: {score_val:.2f}"
                        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                        cv2.rectangle(processed_frame, 
                                     (box[0], box[1] - text_size[1] - 5),
                                     (box[0] + text_size[0], box[1]),
                                     color, -1)
                        
                        cv2.putText(processed_frame, text, (box[0], box[1] - 5), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                        
                        results.append({
                            "bbox": box.tolist(),
                            "class": label_idx,
                            "score": score_val
                        })
            
            elif self.model_name == "yolov5":
                with torch.no_grad():
                    results = self.model(rgb_frame)
                
                processed_frame = results.render()[0]
                results = results.pandas().xyxy[0].to_dict(orient="records")
            
            elif self.model_name == "yolov8":
                with torch.no_grad():
                    results = self.model(rgb_frame)
                
                processed_frame = results[0].plot()
                results = results[0].boxes.data.cpu().numpy()
        
        # SEGMENTATION MODELS
        elif self.task_type == "segmentation":
            input_tensor = self.preprocess(rgb_frame)
            input_batch = input_tensor.unsqueeze(0).to(self.device)
            
            colormap = np.array([
                [0, 0, 0],         # Background (black)
                [255, 0, 0],       # Class 1 (red)
                [0, 255, 0],       # Class 2 (green)
                [0, 0, 255],       # Class 3 (blue)
                [255, 255, 0],     # Class 4 (yellow)
                [255, 0, 255],     # Class 5 (magenta)
                [0, 255, 255],     # Class 6 (cyan)
                [128, 128, 255],   # Class 7 (light blue)
                [255, 128, 128],   # Class 8 (light red)
                [128, 255, 128],   # Class 9 (light green)
                [255, 128, 0],     # Class 10 (orange)
                [128, 0, 255],     # Class 11 (purple)
            ], dtype=np.uint8)
            
            h, w = frame.shape[:2]
            
            if self.model_name in ["deeplabv3", "fcn"]:
                with torch.no_grad():
                    output = self.model(input_batch)['out'][0]
                    output_softmax = torch.softmax(output, dim=0)
                    confidence, prediction = torch.max(output_softmax, dim=0)
                    prediction = prediction.byte().cpu().numpy()
                
                prediction_resized = cv2.resize(prediction, (w, h), interpolation=cv2.INTER_NEAREST)
                confidence = confidence.cpu().numpy()
                confidence_resized = cv2.resize(confidence, (w, h), interpolation=cv2.INTER_LINEAR)
                
                segmentation_map = np.zeros((h, w, 3), dtype=np.uint8)
                
                legend_img = np.zeros((30 * min(self.num_classes, 6), 150, 3), dtype=np.uint8) + 255
                
                for i in range(min(self.num_classes, 6)):  
                    color = colormap[i % len(colormap)].tolist()
                    cv2.rectangle(legend_img, (5, 5 + i*30), (30, 25 + i*30), color, -1)
                    cv2.putText(legend_img, f"Class {i}", (40, 20 + i*30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                
                for class_idx in range(self.num_classes):
                    mask = (prediction_resized == class_idx)
                    if mask.any():  
                        segmentation_map[mask] = colormap[class_idx % len(colormap)]
                
                alpha = 0.5  
                overlay = processed_frame.copy()
                cv2.addWeighted(segmentation_map, alpha, overlay, 1 - alpha, 0, processed_frame)
                
                for class_idx in range(1, self.num_classes):  
                    mask = (prediction_resized == class_idx).astype(np.uint8) * 255
                    if np.sum(mask) > 100: 
                        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        significant_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 100]
                        
                        color = colormap[class_idx % len(colormap)].tolist()
                        cv2.drawContours(processed_frame, significant_contours, -1, color, 2)
                        
                        if significant_contours:
                            largest = max(significant_contours, key=cv2.contourArea)
                            M = cv2.moments(largest)
                            if M["m00"] > 0:
                                cx = int(M["m10"] / M["m00"])
                                cy = int(M["m01"] / M["m00"])
                                text = f"Class {class_idx}"
                                textsize = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                                cv2.rectangle(processed_frame, 
                                             (cx - 5, cy - textsize[1] - 5),
                                             (cx + textsize[0] + 5, cy + 5),
                                             (0, 0, 0), -1)
                                cv2.putText(processed_frame, text, (cx, cy), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                legend_h, legend_w = legend_img.shape[:2]
                processed_frame[10:10+legend_h, processed_frame.shape[1]-legend_w-10:processed_frame.shape[1]-10] = legend_img
                
                results = {
                    "prediction": prediction,
                    "confidence": confidence,
                    "num_classes": self.num_classes
                }
            
            elif self.model_name == "unet":
                with torch.no_grad():
                    output = self.model(input_batch)
                    
                    if output.shape[1] > 1:
                        output_softmax = torch.softmax(output, dim=1)
                        confidence, prediction = torch.max(output_softmax, dim=1)
                        prediction = prediction[0].byte().cpu().numpy()
                        confidence = confidence[0].cpu().numpy()
                    else: 
                        prediction = (torch.sigmoid(output) > 0.5)[0, 0].byte().cpu().numpy()
                        confidence = torch.sigmoid(output)[0, 0].cpu().numpy()
                        prediction = prediction.astype(np.uint8)
                
                prediction_resized = cv2.resize(prediction, (w, h), interpolation=cv2.INTER_NEAREST)
                confidence_resized = cv2.resize(confidence, (w, h), interpolation=cv2.INTER_LINEAR)
                
                segmentation_map = np.zeros((h, w, 3), dtype=np.uint8)
                
                if output.shape[1] == 1: 
                    mask = prediction_resized > 0
                    segmentation_map[mask] = [0, 255, 0]  
                    
                    binary_mask = (prediction_resized > 0).astype(np.uint8) * 255
                    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.drawContours(processed_frame, contours, -1, (0, 255, 0), 2)
                    
                    confidence_map = (confidence_resized * 255).astype(np.uint8)
                    confidence_color = cv2.applyColorMap(confidence_map, cv2.COLORMAP_JET)
                    
                    conf_vis_size = (150, 150)
                    confidence_vis = cv2.resize(confidence_color, conf_vis_size)
                    h_offset, w_offset = 10, 10
                    processed_frame[h_offset:h_offset+conf_vis_size[1], 
                                   w_offset:w_offset+conf_vis_size[0]] = confidence_vis
                    
                else:  
                    for class_idx in range(self.num_classes):
                        mask = (prediction_resized == class_idx)
                        if mask.any(): 
                            segmentation_map[mask] = colormap[class_idx % len(colormap)]
                    
                    legend_img = np.zeros((30 * min(self.num_classes, 6), 150, 3), dtype=np.uint8) + 255
                    for i in range(min(self.num_classes, 6)):
                        color = colormap[i % len(colormap)].tolist()
                        cv2.rectangle(legend_img, (5, 5 + i*30), (30, 25 + i*30), color, -1)
                        cv2.putText(legend_img, f"Class {i}", (40, 20 + i*30), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                    
                    legend_h, legend_w = legend_img.shape[:2]
                    processed_frame[10:10+legend_h, processed_frame.shape[1]-legend_w-10:processed_frame.shape[1]-10] = legend_img
                
                alpha = 0.5
                overlay = processed_frame.copy()
                cv2.addWeighted(segmentation_map, alpha, overlay, 1 - alpha, 0, processed_frame)
                
                results = {
                    "prediction": prediction,
                    "confidence": confidence,
                    "num_classes": output.shape[1]
                }
            
            elif self.model_name == "maskrcnn":
                with torch.no_grad():
                    predictions = self.model(input_batch)[0]
                
                boxes = predictions["boxes"].cpu().numpy().astype(np.int32)
                scores = predictions["scores"].cpu().numpy()
                labels = predictions["labels"].cpu().numpy()
                masks = predictions["masks"].squeeze().cpu().numpy()
                
                keep = scores > self.detection_threshold
                boxes = boxes[keep]
                scores = scores[keep]
                labels = labels[keep]
                masks = masks[keep]
                
                for i, (box, mask, label, score) in enumerate(zip(boxes, masks, labels, scores)):
                    color = colormap[label % len(colormap)].tolist()
                    
                    mask_resized = cv2.resize(mask, (w, h))
                    mask_binary = (mask_resized > 0.5).astype(np.uint8)
                    
                    mask_color = np.zeros((h, w, 3), dtype=np.uint8)
                    mask_color[mask_binary > 0] = color
                    
                    alpha = 0.5
                    cv2.addWeighted(mask_color, alpha, processed_frame, 1.0, 0, processed_frame)
                    
                    cv2.rectangle(processed_frame, (box[0], box[1]), (box[2], box[3]), color, 2)
                    
                    label_text = f"Class {label}: {score:.2f}"
                    cv2.putText(processed_frame, label_text, (box[0], box[1] - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                results = {
                    "boxes": boxes,
                    "labels": labels,
                    "scores": scores,
                    "masks": masks
                }
        
        cv2.putText(processed_frame, f"{self.model_name}", 
                    (processed_frame.shape[1] - 120, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return processed_frame, results