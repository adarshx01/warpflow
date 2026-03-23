import os
import subprocess
import argparse
import sys
import signal
import threading
import time
from typing import List, Optional, Dict, Any

def run_service(cmd: List[str], service_name: str) -> subprocess.Popen:
    print(f"Starting {service_name}...")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )
    
    def monitor_output(process, name):
        for line in process.stdout:
            print(f"[{name}] {line}", end='')
        for line in process.stderr:
            print(f"[{name} ERROR] {line}", end='')
            
    thread = threading.Thread(target=monitor_output, args=(process, service_name))
    thread.daemon = True
    thread.start()
    
    return process

def signal_handler(sig, frame):
    print("\nShutting down services...")
    for process in running_processes:
        if process.poll() is None:
            print(f"Terminating process PID: {process.pid}")
            process.terminate()
    
    time.sleep(2)
    for process in running_processes:
        if process.poll() is None:
            print(f"Force killing process PID: {process.pid}")
            process.kill()
    
    print("All services stopped")
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stratify Labs Vision Platform")
    parser.add_argument("--inference-port", type=int, default=8001, help="Port for inference service")
    parser.add_argument("--training-port", type=int, default=8000, help="Port for training service")
    parser.add_argument("--disable-inference", action="store_true", help="Disable inference service")
    parser.add_argument("--disable-training", action="store_true", help="Disable training service")
    parser.add_argument("--model", type=str, help="Model name for inference")
    parser.add_argument("--task", type=str, help="Task type (classification, detection, segmentation)")
    parser.add_argument("--model-path", type=str, help="Path to model weights file")
    parser.add_argument("--dataset", type=str, help="Path to dataset for class names")
    parser.add_argument("--num-classes", type=int, help="Number of classes for segmentation")
    
    args = parser.parse_args()
    running_processes = []
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Stratify Labs Vision Platform")
    print("============================")
    
    try:
        if not args.disable_training:
            train_cmd = [
                sys.executable, 
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "training", "visiontrain.py")
            ]
            
            if args.training_port:
                train_cmd.extend(["--port", str(args.training_port)])
                
            train_process = run_service(train_cmd, "Training Service")
            running_processes.append(train_process)
            print(f"Training service started on port {args.training_port}")
        
        if not args.disable_inference:
            inference_cmd = [
                sys.executable, 
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "inference", "unified_stream.py")
            ]
            
            if args.inference_port:
                inference_cmd.extend(["--port", str(args.inference_port)])
                
            if args.task and args.model and args.model_path:
                inference_cmd.extend([
                    "--task", args.task,
                    "--model", args.model,
                    "--model-path", args.model_path
                ])
                
                if args.dataset:
                    inference_cmd.extend(["--dataset", args.dataset])
                    
                if args.num_classes:
                    inference_cmd.extend(["--num-classes", str(args.num_classes)])
                    
            inference_process = run_service(inference_cmd, "Inference Service")
            running_processes.append(inference_process)
            print(f"Inference service started on port {args.inference_port}")
            
        print("\nServices are running. Press Ctrl+C to stop.")
        
        while True:
            time.sleep(1)
            for process in running_processes:
                if process.poll() is not None:
                    print(f"Process PID {process.pid} exited with code {process.returncode}")
                    running_processes.remove(process)
                    
            if not running_processes:
                print("All services have stopped. Exiting.")
                break
                
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)