import torch
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
import torchvision.models as models

model = models.resnet18(pretrained=False)  
state_dict = torch.load("/home/adarsh/WorkSpace/VisionFlow/saved_models/classification/resnet_adam_20250321_084930.pt", map_location=device)
model.load_state_dict(state_dict)
model.to(device)
model.eval()