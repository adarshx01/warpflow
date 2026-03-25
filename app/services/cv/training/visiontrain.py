import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms, models
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware 
import numpy as np
from PIL import Image
import json
from pycocotools.coco import COCO


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

class SegmentationDatasetHandler:
    """Universal handler for different segmentation dataset formats"""
    
    @staticmethod
    def create_dataset(dataset_path, transform=None, format_type=None):
        """Factory method to create appropriate dataset based on detected format"""
        if format_type is None:
            format_type = SegmentationDatasetHandler._detect_format(dataset_path)
            
        if format_type == "coco":
            return CocoSegmentationDataset(dataset_path, transform=transform)
        elif format_type == "binary":
            return BinarySegmentationDataset(dataset_path, transform=transform)
        elif format_type == "multiclass":
            return MulticlassSegmentationDataset(dataset_path, transform=transform)
        else:
            raise ValueError(f"Unsupported dataset format: {format_type}")
    
    @staticmethod
    def _detect_format(dataset_path):
        """Detect the dataset format based on directory structure and files"""
        coco_annotation_paths = [
            os.path.join(dataset_path, "_annotations.coco.json"),
            os.path.join(dataset_path, "annotations.json"),
            os.path.join(dataset_path, "annotations", "instances.json")
        ]
        
        for ann_path in coco_annotation_paths:
            if os.path.exists(ann_path):
                print(f"Found COCO annotations at {ann_path}")
                return "coco"
        
        if os.path.exists(os.path.join(dataset_path, "images")) and os.path.exists(os.path.join(dataset_path, "masks")):
            print("Found binary segmentation format (images/ and masks/ directories)")
            return "binary"
        
        if os.path.exists(os.path.join(dataset_path, "labels.txt")):
            print("Found multiclass segmentation format (labels.txt file)")
            return "multiclass"
        
        image_files = [f for f in os.listdir(dataset_path) if f.endswith(('.png', '.jpg', '.jpeg'))]
        if image_files and [f for f in os.listdir(dataset_path) if f.endswith('.json')]:
            print("Found images with JSON file - assuming COCO format")
            return "coco"
        
        print("Could not determine format, defaulting to binary")
        return "binary"

class CocoSegmentationDataset(torch.utils.data.Dataset):
    """Dataset for COCO format segmentation data"""
    
    def __init__(self, dataset_path, transform=None):
        self.dataset_path = dataset_path
        self.transform = transform
        
        self.ann_file = os.path.join(dataset_path, "_annotations.coco.json")
        if not os.path.exists(self.ann_file):
            raise FileNotFoundError(f"COCO annotations file not found at {self.ann_file}")
        
        self.coco = COCO(self.ann_file)
        self.img_ids = self.coco.getImgIds()
        self.num_classes = len(self.coco.getCatIds()) + 1  
        
    def __len__(self):
        return len(self.img_ids)
        
    def __getitem__(self, idx):
        img_id = self.img_ids[idx]
        img_info = self.coco.loadImgs(img_id)[0]
        img_path = os.path.join(self.dataset_path, img_info['file_name'])
        
        img = Image.open(img_path).convert("RGB")
        
        ann_ids = self.coco.getAnnIds(imgIds=img_id)
        anns = self.coco.loadAnns(ann_ids)
        
        # Create binary mask (0 for background, 1+ for objects)
        mask = np.zeros((img_info['height'], img_info['width']), dtype=np.uint8)
        for ann in anns:
            cat_id = ann['category_id']
            mask = np.maximum(self.coco.annToMask(ann) * cat_id, mask)
            
        mask = Image.fromarray(mask)
        
        img = img.resize((256, 256), Image.BILINEAR)
        mask = mask.resize((256, 256), Image.NEAREST)  
        
        if self.transform:
            img = self.transform(img)
        
        mask_transform = transforms.ToTensor()
        mask = mask_transform(mask)
        
        return img, mask.long()  

class BinarySegmentationDataset(torch.utils.data.Dataset):
    """Dataset for binary segmentation with images/ and masks/ folders"""
    
    def __init__(self, dataset_path, transform=None):
        self.images_dir = os.path.join(dataset_path, "images")
        self.masks_dir = os.path.join(dataset_path, "masks")
        
        if not os.path.exists(self.images_dir):
            self.images_dir = dataset_path
            potential_masks_dir = os.path.join(dataset_path, "masks")
            if os.path.exists(potential_masks_dir):
                self.masks_dir = potential_masks_dir
            else:
                raise FileNotFoundError(f"Could not find masks directory in {dataset_path}")
        
        self.transform = transform
        self.image_files = sorted([f for f in os.listdir(self.images_dir) 
                                  if f.endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))])
        self.num_classes = 2 
        
    def __len__(self):
        return len(self.image_files)
        
    def __getitem__(self, idx):
        img_name = self.image_files[idx]
        img_path = os.path.join(self.images_dir, img_name)
        
        mask_patterns = [
            img_name, 
            img_name.replace('.jpg', '.png').replace('.jpeg', '.png'),  # Different extension
            img_name.split('.')[0] + '_mask.png',  # _mask suffix
            img_name.split('.')[0] + '_segmentation.png'  # _segmentation suffix
        ]
        
        mask_path = None
        for pattern in mask_patterns:
            potential_path = os.path.join(self.masks_dir, pattern)
            if os.path.exists(potential_path):
                mask_path = potential_path
                break
                
        if mask_path is None:
            raise FileNotFoundError(f"No matching mask found for {img_name}")
            
        img = Image.open(img_path).convert("RGB")
        mask = Image.open(mask_path).convert("L")  
        
        mask = np.array(mask)
        mask = (mask > 0).astype(np.uint8)
        mask = Image.fromarray(mask)
        
        if self.transform:
            img = self.transform(img)
        
        mask_transform = transforms.ToTensor()
        mask = mask_transform(mask)
        
        return img, mask

class MulticlassSegmentationDataset(torch.utils.data.Dataset):
    """Dataset for multiclass segmentation with class labels"""
    
    def __init__(self, dataset_path, transform=None):
        self.dataset_path = dataset_path
        self.transform = transform
        
        # Directory structure expected:
        # - dataset_path/
        #   - images/
        #   - masks/
        #   - labels.txt (optional)
        
        self.images_dir = os.path.join(dataset_path, "images")
        self.masks_dir = os.path.join(dataset_path, "masks")
        
        # Read class labels if available
        labels_file = os.path.join(dataset_path, "labels.txt")
        self.class_names = ["background"]
        if os.path.exists(labels_file):
            with open(labels_file, 'r') as f:
                self.class_names.extend([line.strip() for line in f.readlines()])
        
        self.num_classes = len(self.class_names)
        self.image_files = sorted([f for f in os.listdir(self.images_dir) 
                                  if f.endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))])
        
    def __len__(self):
        return len(self.image_files)
        
    def __getitem__(self, idx):
        img_name = self.image_files[idx]
        img_path = os.path.join(self.images_dir, img_name)
        
        mask_patterns = [
            img_name,
            img_name.replace('.jpg', '.png'),
            img_name.split('.')[0] + '_mask.png'
        ]
        
        mask_path = None
        for pattern in mask_patterns:
            potential_path = os.path.join(self.masks_dir, pattern)
            if os.path.exists(potential_path):
                mask_path = potential_path
                break
                
        if mask_path is None:
            raise FileNotFoundError(f"No matching mask found for {img_name}")
            
        img = Image.open(img_path).convert("RGB")
        mask = Image.open(mask_path).convert("L")  
        
        if self.transform:
            img = self.transform(img)
        
        mask_transform = transforms.ToTensor()
        mask = mask_transform(mask)
        
        return img, mask

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

class Task:
    def __init__(self, model_name, optimizer_name, train_pct, val_pct, test_pct, dataset_path, epochs=5):
        self.model_name = model_name.lower()
        self.optimizer_name = optimizer_name.lower()
        self.train_pct = train_pct
        self.val_pct = val_pct
        self.test_pct = test_pct
        self.dataset_path = dataset_path
        self.epochs = epochs
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.optimizer = None

    def load_data(self):
        raise NotImplementedError("Subclasses must implement load_data")

    def get_model(self):
        raise NotImplementedError("Subclasses must implement get_model")

    def get_optimizer(self):
        if self.optimizer_name == "sgd":
            return optim.SGD(self.model.parameters(), lr=0.01, momentum=0.9)
        elif self.optimizer_name == "adam":
            return optim.Adam(self.model.parameters(), lr=0.001)
        elif self.optimizer_name == "rmsprop":
            return optim.RMSprop(self.model.parameters(), lr=0.001)
        elif self.optimizer_name == "adagrad":
            return optim.Adagrad(self.model.parameters(), lr=0.01)
        elif self.optimizer_name == "adamw":
            return optim.AdamW(self.model.parameters(), lr=0.001)
        else:
            raise ValueError(f"Optimizer {self.optimizer_name} not supported")

    def save_model(self):
        save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")
        os.makedirs(save_dir, exist_ok=True)
        
        task_dir = os.path.join(save_dir, self.__class__.__name__.lower().replace("task", ""))
        os.makedirs(task_dir, exist_ok=True)
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = os.path.join(
            task_dir, 
            f"{self.model_name}_{self.optimizer_name}_{timestamp}.pt"
        )
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'model_name': self.model_name,
            'optimizer_name': self.optimizer_name,
        }, model_path)
        
        return model_path

    def train(self):
        self.model = self.get_model()
        self.optimizer = self.get_optimizer()
        train_loader, val_loader = self.load_data()
        criterion = self.get_loss_function()
        
        self.model.to(self.device)
        best_val_loss = float('inf')
        
        for epoch in range(self.epochs):
            self.model.train()
            running_loss = 0.0
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(self.device), targets.to(self.device)
                self.optimizer.zero_grad()
                outputs = self.model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                self.optimizer.step()
                running_loss += loss.item()
            print(f"Epoch {epoch+1}/{self.epochs}, Loss: {running_loss/len(train_loader)}")

            # Validation
            self.model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(self.device), targets.to(self.device)
                    outputs = self.model(inputs)
                    val_loss += criterion(outputs, targets).item()
            
            avg_val_loss = val_loss/len(val_loader)
            print(f"Validation Loss: {avg_val_loss}")
            
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
        
        model_path = self.save_model()
        print(f"Training completed. Model saved to {model_path}")
        
        return model_path

    def get_loss_function(self):
        raise NotImplementedError("Subclasses must define loss function")

# this is for he classification task
class ClassificationTask(Task):
    def load_data(self):
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        dataset = datasets.ImageFolder(self.dataset_path, transform=transform)
        train_size = int(self.train_pct * len(dataset))
        val_size = int(self.val_pct * len(dataset))
        test_size = len(dataset) - train_size - val_size
        train_dataset, val_dataset, _ = random_split(dataset, [train_size, val_size, test_size])
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
        return train_loader, val_loader

    def get_model(self):
        if self.model_name == "resnet":
            model = models.resnet50(pretrained=True)
            num_ftrs = model.fc.in_features
            model.fc = nn.Linear(num_ftrs, len(os.listdir(self.dataset_path)))
        elif self.model_name == "efficientnet":
            from torchvision.models import efficientnet_b0
            model = efficientnet_b0(pretrained=True)
            num_ftrs = model.classifier[1].in_features
            model.classifier[1] = nn.Linear(num_ftrs, len(os.listdir(self.dataset_path)))
        elif self.model_name == "vgg":
            model = models.vgg16(pretrained=True)
            num_ftrs = model.classifier[6].in_features
            model.classifier[6] = nn.Linear(num_ftrs, len(os.listdir(self.dataset_path)))
        elif self.model_name == "inception":
            model = models.inception_v3(pretrained=True)
            num_ftrs = model.fc.in_features
            model.fc = nn.Linear(num_ftrs, len(os.listdir(self.dataset_path)))
        elif self.model_name == "mobilenet":
            model = models.mobilenet_v2(pretrained=True)
            num_ftrs = model.classifier[1].in_features
            model.classifier[1] = nn.Linear(num_ftrs, len(os.listdir(self.dataset_path)))
        elif self.model_name == "densenet":
            model = models.densenet121(pretrained=True)
            num_ftrs = model.classifier.in_features
            model.classifier = nn.Linear(num_ftrs, len(os.listdir(self.dataset_path)))
        elif self.model_name == "vit":
            from torchvision.models import vit_b_16
            model = vit_b_16(pretrained=True)
            num_ftrs = model.heads.head.in_features
            model.heads.head = nn.Linear(num_ftrs, len(os.listdir(self.dataset_path)))
        elif self.model_name == "convnext":
            from torchvision.models import convnext_tiny
            model = convnext_tiny(pretrained=True)
            num_ftrs = model.classifier[2].in_features
            model.classifier[2] = nn.Linear(num_ftrs, len(os.listdir(self.dataset_path)))
        else:
            raise ValueError(f"Model {self.model_name} not supported for classification")
        return model

    def get_loss_function(self):
        return nn.CrossEntropyLoss()

class DetectionTask(Task):
    def load_data(self):
        # In practice, use a dataset like COCO with torchvision.datasets.CocoDetection
        transform = transforms.Compose([transforms.ToTensor()])
        dataset = datasets.ImageFolder(self.dataset_path, transform=transform)  
        train_size = int(self.train_pct * len(dataset))
        val_size = int(self.val_pct * len(dataset))
        test_size = len(dataset) - train_size - val_size
        train_dataset, val_dataset, _ = random_split(dataset, [train_size, val_size, test_size])
        train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=4, shuffle=False)
        return train_loader, val_loader

    def get_model(self):
        if self.model_name == "fasterrcnn":
            model = models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
        elif self.model_name == "ssd":
            model = models.detection.ssd300_vgg16(pretrained=True)
        elif self.model_name == "retinanet":
            model = models.detection.retinanet_resnet50_fpn(pretrained=True)
        elif self.model_name == "maskrcnn":
            model = models.detection.maskrcnn_resnet50_fpn(pretrained=True)
        elif self.model_name in ["yolov3", "yolov4", "yolov5", "yolov8", "efficientdet", "detr"]:
            raise NotImplementedError(f"{self.model_name} requires additional library installation")
        else:
            raise ValueError(f"Model {self.model_name} not supported for detection")
        return model

    def get_loss_function(self):
        return lambda outputs, targets: sum(loss for loss in outputs.values())

# Segmentation Task
class SegmentationTask(Task):
    def load_data(self):
        img_transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        try:
            print(f"Loading dataset from {self.dataset_path}")
            dataset = SegmentationDatasetHandler.create_dataset(self.dataset_path, transform=img_transform)
            self.num_classes = dataset.num_classes
            print(f"Dataset loaded with {len(dataset)} samples and {self.num_classes} classes")
            
            total_size = len(dataset)
            train_size = int(self.train_pct * total_size)
            val_size = int(self.val_pct * total_size)
            test_size = total_size - train_size - val_size
            
            train_dataset, val_dataset, _ = random_split(
                dataset, [train_size, val_size, test_size]
            )
            
        except Exception as e:
            print(f"Failed to load dataset as segmentation dataset: {str(e)}")
            print("Falling back to ImageFolder dataset")
            transform = transforms.Compose([transforms.Resize((256, 256)), transforms.ToTensor()])
            dataset = datasets.ImageFolder(self.dataset_path, transform=transform)
            train_size = int(self.train_pct * len(dataset))
            val_size = int(self.val_pct * len(dataset))
            test_size = len(dataset) - train_size - val_size
            train_dataset, val_dataset, _ = random_split(dataset, [train_size, val_size, test_size])
            self.num_classes = 2
        
        train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=4, shuffle=False)
        
        return train_loader, val_loader

    def get_model(self):
        if not hasattr(self, 'num_classes'):
            self.num_classes = 2  
            
        if self.model_name == "unet":
            try:
                import segmentation_models_pytorch as smp
                model = smp.Unet(
                    encoder_name="resnet34",
                    encoder_weights="imagenet",
                    in_channels=3,
                    classes=self.num_classes,
                )
            except ImportError:
                raise ImportError("Please install segmentation-models-pytorch: pip install segmentation-models-pytorch")
        elif self.model_name == "deeplabv3":
            model = models.segmentation.deeplabv3_resnet50(pretrained=True)
            model.classifier[4] = nn.Conv2d(256, self.num_classes, kernel_size=1)
        elif self.model_name == "fcn":
            model = models.segmentation.fcn_resnet50(pretrained=True)
            model.classifier[4] = nn.Conv2d(512, self.num_classes, kernel_size=1)
        elif self.model_name == "maskrcnn":
            model = models.detection.maskrcnn_resnet50_fpn(pretrained=True)
            # Adjust mask rcnn for number of classes
            in_features = model.roi_heads.box_predictor.cls_score.in_features
            model.roi_heads.box_predictor = models.detection.faster_rcnn.FastRCNNPredictor(
                in_features, self.num_classes)
            in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
            hidden_layer = 256
            model.roi_heads.mask_predictor = models.detection.mask_rcnn.MaskRCNNPredictor(
                in_features_mask, hidden_layer, self.num_classes)
        elif self.model_name in ["pspnet"]:
            try:
                import segmentation_models_pytorch as smp
                model = smp.PSPNet(
                    encoder_name="resnet34",
                    encoder_weights="imagenet",
                    classes=self.num_classes
                )
            except ImportError:
                raise ImportError("Please install segmentation-models-pytorch: pip install segmentation-models-pytorch")
        elif self.model_name in ["segnet", "yolact", "segformer", "mask2former"]:
            raise NotImplementedError(f"{self.model_name} requires additional library installation")
        else:
            raise ValueError(f"Model {self.model_name} not supported for segmentation")
        return model

    def train(self):
        self.model = self.get_model()
        self.optimizer = self.get_optimizer()
        train_loader, val_loader = self.load_data()
        criterion = self.get_loss_function()
        
        self.model.to(self.device)
        best_val_loss = float('inf')
        
        for epoch in range(self.epochs):
            self.model.train()
            running_loss = 0.0
            
            # Training loop
            for inputs, targets in train_loader:
                inputs = inputs.to(self.device)
                targets = targets.to(self.device)
                
                self.optimizer.zero_grad()
                
                # Handle different model outputs based on architecture
                if self.model_name in ["deeplabv3", "fcn"]:
                    outputs = self.model(inputs)["out"]
                    # Make sure target is prepared as expected by CrossEntropyLoss
                    targets = targets.squeeze(1).long()  # Remove channel dim and convert to long
                    loss = criterion(outputs, targets)
                elif self.model_name == "maskrcnn":
                    # MaskRCNN needs a different approach
                    try:
                        target_list = []
                        for i, t in enumerate(targets):
                            # Convert mask tensor to proper format for MaskRCNN
                            target_dict = {
                                'boxes': torch.tensor([[0, 0, inputs.shape[3]-1, inputs.shape[2]-1]], device=self.device).float(),
                                'labels': torch.ones(1, dtype=torch.int64, device=self.device),
                                'masks': t.unsqueeze(0)
                            }
                            target_list.append(target_dict)
                        
                        loss_dict = self.model(inputs, target_list)
                        loss = sum(loss for loss in loss_dict.values())
                    except Exception as e:
                        print(f"Error in MaskRCNN forward pass: {str(e)}")
                        continue
                else:
                    # Generic case (like UNet from smp)
                    outputs = self.model(inputs)
                    # Check if model output and target have matching dimensions
                    if outputs.shape[2:] != targets.shape[2:]:
                        targets = torch.nn.functional.interpolate(targets.float(), size=outputs.shape[2:], mode='nearest')
                    
                    # For binary segmentation or multiclass segmentation
                    if outputs.shape[1] > 1:  # Multi-class
                        targets = targets.squeeze(1).long()
                        loss = criterion(outputs, targets)
                    else:  # Binary
                        loss = criterion(outputs, targets)
                        
                loss.backward()
                self.optimizer.step()
                running_loss += loss.item()
                
            avg_train_loss = running_loss / len(train_loader)
            print(f"Epoch {epoch+1}/{self.epochs}, Loss: {avg_train_loss}")
            
            # Validation phase
            self.model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(self.device)
                    targets = targets.to(self.device)
                    
                    if self.model_name in ["deeplabv3", "fcn"]:
                        outputs = self.model(inputs)["out"]
                        loss = criterion(outputs, targets.squeeze(1).long())
                    elif self.model_name == "maskrcnn":
                        # Skip validation for MaskRCNN for simplicity
                        continue
                    else:
                        outputs = self.model(inputs)
                        loss = criterion(outputs, targets.squeeze(1).long())
                        
                    val_loss += loss.item()
                    
            if len(val_loader) > 0:  # Avoid division by zero
                avg_val_loss = val_loss / len(val_loader)
                print(f"Validation Loss: {avg_val_loss}")
                
                if avg_val_loss < best_val_loss:
                    best_val_loss = avg_val_loss
                    # You could save the best model here
            
        # Save final model
        model_path = self.save_model()
        print(f"Training completed. Model saved to {model_path}")
        return model_path

    def get_loss_function(self):
        if hasattr(self, 'num_classes') and self.num_classes > 2:
            print(f"Using CrossEntropyLoss for {self.num_classes} classes")
            return nn.CrossEntropyLoss()
        else:
            print("Using Binary Cross Entropy loss for binary segmentation")
            return nn.BCEWithLogitsLoss()

# Add TensorFlow support (if installed)
try:
    import tensorflow as tf
    
    class TFSegmentationTask(Task):
        """TensorFlow implementation of segmentation task"""
        
        def load_data(self):
            # The dataset loading logic is similar, but we'll use TF's data pipeline
            try:
                # Auto-detect format and convert to TF dataset
                torch_dataset = SegmentationDatasetHandler.create_dataset(self.dataset_path)
                self.num_classes = torch_dataset.num_classes
                
                def generator():
                    for i in range(len(torch_dataset)):
                        img, mask = torch_dataset[i]
                        # Convert PyTorch tensors to numpy arrays
                        img_np = img.numpy()
                        mask_np = mask.numpy()
                        yield img_np, mask_np
                
                # Get shape from first sample to handle dynamic shapes
                sample_img, sample_mask = torch_dataset[0]
                img_shape = sample_img.shape
                mask_shape = sample_mask.shape
                
                # Create TF dataset from generator
                dataset = tf.data.Dataset.from_generator(
                    generator,
                    output_signature=(
                        tf.TensorSpec(shape=img_shape, dtype=tf.float32),
                        tf.TensorSpec(shape=mask_shape, dtype=tf.float32)
                    )
                )
                
                # Convert channels-first to channels-last (TF standard)
                dataset = dataset.map(lambda x, y: (
                    tf.transpose(x, [1, 2, 0]), 
                    tf.squeeze(y, axis=0) if tf.shape(y)[0] == 1 else y
                ))
                
                # Split dataset
                total_size = len(torch_dataset)
                train_size = int(self.train_pct * total_size)
                val_size = int(self.val_pct * total_size)
                
                train_dataset = dataset.take(train_size).batch(4).prefetch(tf.data.AUTOTUNE)
                val_dataset = dataset.skip(train_size).take(val_size).batch(4).prefetch(tf.data.AUTOTUNE)
                
                return train_dataset, val_dataset
            
            except Exception as e:
                print(f"Error loading TensorFlow dataset: {str(e)}")
                raise
        
        def get_model(self):
            if not hasattr(self, 'num_classes'):
                self.num_classes = 2
                
            if self.model_name == "unet":
                return self._create_tf_unet()
            elif self.model_name == "deeplabv3":
                # DeepLabV3 would require TensorFlow hub or custom implementation
                raise NotImplementedError("TensorFlow DeepLabV3 not implemented")
            else:
                raise ValueError(f"Model {self.model_name} not supported for TF segmentation")
        
        def _create_tf_unet(self):
            """Create a simple U-Net model in TensorFlow"""
            inputs = tf.keras.Input(shape=(256, 256, 3))
            
            # Encoder
            x = tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same')(inputs)
            x = tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same')(x)
            skip1 = x
            x = tf.keras.layers.MaxPooling2D((2, 2))(x)
            
            x = tf.keras.layers.Conv2D(128, 3, activation='relu', padding='same')(x)
            x = tf.keras.layers.Conv2D(128, 3, activation='relu', padding='same')(x)
            skip2 = x
            x = tf.keras.layers.MaxPooling2D((2, 2))(x)
            
            x = tf.keras.layers.Conv2D(256, 3, activation='relu', padding='same')(x)
            x = tf.keras.layers.Conv2D(256, 3, activation='relu', padding='same')(x)
            skip3 = x
            x = tf.keras.layers.MaxPooling2D((2, 2))(x)
            
            x = tf.keras.layers.Conv2D(512, 3, activation='relu', padding='same')(x)
            x = tf.keras.layers.Conv2D(512, 3, activation='relu', padding='same')(x)
            
            # Decoder
            x = tf.keras.layers.Conv2DTranspose(256, 3, strides=2, padding='same')(x)
            x = tf.keras.layers.Concatenate()([x, skip3])
            x = tf.keras.layers.Conv2D(256, 3, activation='relu', padding='same')(x)
            x = tf.keras.layers.Conv2D(256, 3, activation='relu', padding='same')(x)
            
            x = tf.keras.layers.Conv2DTranspose(128, 3, strides=2, padding='same')(x)
            x = tf.keras.layers.Concatenate()([x, skip2])
            x = tf.keras.layers.Conv2D(128, 3, activation='relu', padding='same')(x)
            x = tf.keras.layers.Conv2D(128, 3, activation='relu', padding='same')(x)
            
            x = tf.keras.layers.Conv2DTranspose(64, 3, strides=2, padding='same')(x)
            x = tf.keras.layers.Concatenate()([x, skip1])
            x = tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same')(x)
            x = tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same')(x)
            
            outputs = tf.keras.layers.Conv2D(self.num_classes, 1, activation='softmax')(x)
            
            model = tf.keras.Model(inputs, outputs)
            return model
        
        def train(self):
            model = self.get_model()
            train_dataset, val_dataset = self.load_data()
            
            # Compile model
            model.compile(
                optimizer=tf.keras.optimizers.Adam(0.001),
                loss='sparse_categorical_crossentropy' if self.num_classes > 2 else 'binary_crossentropy',
                metrics=['accuracy']
            )
            
            # Add ModelCheckpoint callback to save best model
            checkpoint_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "saved_models", 
                "tf_segmentation",
                f"{self.model_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.h5"
            )
            os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
            
            callbacks = [
                tf.keras.callbacks.ModelCheckpoint(
                    checkpoint_path, monitor='val_loss', save_best_only=True
                ),
                tf.keras.callbacks.EarlyStopping(
                    patience=5, monitor='val_loss'
                )
            ]
            
            # Train model
            history = model.fit(
                train_dataset,
                epochs=self.epochs,
                validation_data=val_dataset,
                callbacks=callbacks
            )
            
            # Save final model
            model.save(checkpoint_path)
            print(f"TensorFlow model saved to {checkpoint_path}")
            
            return checkpoint_path
        
    # Add TF task to the factory function
    def get_task_extended(task_name, model_name, optimizer_name, train_pct, val_pct, 
                        test_pct, dataset_path, epochs=5, backend="pytorch"):
        task_name = task_name.lower()
        if backend.lower() == "tensorflow" and task_name == "segmentation":
            return TFSegmentationTask(model_name, optimizer_name, train_pct, val_pct, 
                                    test_pct, dataset_path, epochs)
        else:
            return get_task(task_name, model_name, optimizer_name, train_pct, val_pct, 
                            test_pct, dataset_path, epochs)
                            
    # Update TrainRequest model
    class TrainRequest(BaseModel):
        task: str
        model: str
        optimizer: str
        train_pct: float
        val_pct: float
        test_pct: float
        dataset_path: str
        epochs: int = 5
        backend: str = "pytorch"  # "pytorch" or "tensorflow"
        
except ImportError:
    print("TensorFlow not installed. TensorFlow support disabled.")

# Factory function to create task instances
def get_task(task_name, model_name, optimizer_name, train_pct, val_pct, test_pct, dataset_path, epochs=5):
    task_name = task_name.lower()
    if task_name == "classification":
        return ClassificationTask(model_name, optimizer_name, train_pct, val_pct, test_pct, dataset_path, epochs)
    elif task_name == "detection":
        return DetectionTask(model_name, optimizer_name, train_pct, val_pct, test_pct, dataset_path, epochs)
    elif task_name == "segmentation":
        return SegmentationTask(model_name, optimizer_name, train_pct, val_pct, test_pct, dataset_path, epochs)
    else:
        raise ValueError(f"Task {task_name} not supported")

class TrainRequest(BaseModel):
    task: str
    model: str
    optimizer: str
    train_pct: float
    val_pct: float
    test_pct: float
    dataset_path: str
    epochs: int = 5  

@app.get("/alive")
async def alive():
    return {"status":"alive"}
# @app.get("/tasks")
# async def get_tasks():
#     return

@app.post("/train")
async def train_model(request: TrainRequest):
    try:
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
            raise HTTPException(status_code=400, detail=f"Dataset path {request.dataset_path} does not exist")
        if request.epochs <= 0:
            raise HTTPException(status_code=400, detail="Number of epochs must be greater than 0")

        task = get_task(
            request.task, request.model, request.optimizer,
            request.train_pct, request.val_pct, request.test_pct, 
            request.dataset_path, request.epochs
        )
        model_path = task.train()
        return {
            "status": "Training completed successfully",
            "model_saved_at": model_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during training: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)