from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from ultralytics import YOLO
import shutil
import os
import time
from pydantic import BaseModel

app = FastAPI()

model = YOLO('yolov8n-seg.pt')

class TrainParams(BaseModel):
    data_yaml: str  # Path to dataset configuration file
    epochs: int = 10  # Number of training epochs
    imgsz: int = 640  # Image size

def remove_file(path: str):
    os.remove(path)

@app.post("/train")
def train(params: TrainParams):
    """
    Train the YOLOv8 segmentation model with the provided parameters.
    Updates the global model with the trained weights upon completion.
    """
    results = model.train(data=params.data_yaml, epochs=params.epochs, imgsz=params.imgsz)
    save_dir = results.save_dir
    best_model_path = os.path.join(save_dir, 'weights', 'best.pt')
    
    global model
    model = YOLO(best_model_path)
    return {"message": "Training completed and model updated"}

@app.post("/infer")
def infer(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Perform inference on an uploaded image using the current model.
    Returns the segmented image as a file response.
    """
    temp_path = f"temp_image_{int(time.time())}.jpg"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    results = model(temp_path)
    
    output_path = f"output_{int(time.time())}.jpg"
    results[0].save(output_path)
    
    background_tasks.add_task(remove_file, temp_path)
    background_tasks.add_task(remove_file, output_path)
    
    return FileResponse(output_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)