# CV Service AWS GPU Deployment Guide

This guide covers deploying the CV microservice on AWS with GPU support for model training.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Instance Selection](#aws-instance-selection)
3. [EC2 Setup](#ec2-setup)
4. [Docker GPU Setup](#docker-gpu-setup)
5. [Deployment Options](#deployment-options)
6. [Cost Optimization](#cost-optimization)
7. [Monitoring](#monitoring)

---

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured locally
- SSH key pair for EC2 access
- Docker and docker-compose knowledge

---

## AWS Instance Selection

### Recommended GPU Instances

| Instance Type | GPU | VRAM | vCPUs | RAM | Cost/hr (On-Demand) | Best For |
|---------------|-----|------|-------|-----|---------------------|----------|
| `g4dn.xlarge` | T4 | 16GB | 4 | 16GB | ~$0.53 | Development, small models |
| `g4dn.2xlarge` | T4 | 16GB | 8 | 32GB | ~$0.75 | Medium models, classification |
| `g5.xlarge` | A10G | 24GB | 4 | 16GB | ~$1.01 | Production, segmentation |
| `g5.2xlarge` | A10G | 24GB | 8 | 32GB | ~$1.21 | Large models, training |
| `p3.2xlarge` | V100 | 16GB | 8 | 61GB | ~$3.06 | Heavy training workloads |
| `p4d.24xlarge` | 8xA100 | 320GB | 96 | 1152GB | ~$32.77 | Multi-GPU training |

### Recommendation

For most CV training tasks, start with **g4dn.xlarge** for development/testing and scale to **g5.xlarge** for production training.

---

## EC2 Setup

### Step 1: Launch EC2 Instance

```bash
# Using AWS CLI
aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1f0 \  # Deep Learning AMI (Ubuntu)
    --instance-type g4dn.xlarge \
    --key-name your-key-pair \
    --security-group-ids sg-xxxxxxxx \
    --subnet-id subnet-xxxxxxxx \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3"}}]' \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=cv-service}]'
```

### Step 2: Use Deep Learning AMI

AWS Deep Learning AMIs come pre-configured with:
- NVIDIA drivers
- CUDA toolkit
- Docker with NVIDIA runtime
- PyTorch/TensorFlow

Search for: **"Deep Learning AMI GPU PyTorch"** in the AMI marketplace.

### Step 3: Security Group Configuration

Open the following ports:
- **22**: SSH access
- **8080**: CV Service API
- **443**: HTTPS (if using load balancer)

```bash
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxx \
    --protocol tcp \
    --port 8080 \
    --cidr 0.0.0.0/0
```

---

## Docker GPU Setup

### Step 1: Connect to Instance

```bash
ssh -i your-key.pem ubuntu@<ec2-public-ip>
```

### Step 2: Verify GPU Access

```bash
# Check NVIDIA drivers
nvidia-smi

# Expected output shows GPU info:
# +-----------------------------------------------------------------------------+
# | NVIDIA-SMI 525.x.x    Driver Version: 525.x.x    CUDA Version: 12.x       |
# |-------------------------------+----------------------+----------------------+
# | GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
# | Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
# |===============================+======================+======================|
# |   0  Tesla T4            On   | 00000000:00:1E.0 Off |                    0 |
# | N/A   32C    P8     9W /  70W |      0MiB / 15360MiB |      0%      Default |
# +-------------------------------+----------------------+----------------------+
```

### Step 3: Install NVIDIA Container Toolkit (if not pre-installed)

```bash
# Add NVIDIA repo
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Restart Docker
sudo systemctl restart docker

# Verify GPU access in Docker
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi
```

---

## Deployment Options

### Option 1: Docker Compose (Recommended)

```bash
# Clone or copy the CV service
cd /home/ubuntu
mkdir cv-service && cd cv-service

# Copy files from local machine
scp -i your-key.pem -r ./warpcore/app/services/cv/* ubuntu@<ec2-ip>:~/cv-service/

# Start with GPU support
docker-compose --profile gpu up -d

# Check logs
docker-compose logs -f cv-service-gpu
```

### Option 2: Direct Docker Run

```bash
# Build GPU image
docker build --target gpu -t cv-service:gpu .

# Run with GPU
docker run -d \
    --name cv-service \
    --gpus all \
    -p 8080:8080 \
    -v cv-models:/app/saved_models \
    -v $(pwd)/data:/app/data \
    -e NVIDIA_VISIBLE_DEVICES=all \
    cv-service:gpu
```

### Option 3: AWS ECS with GPU

```json
// Task Definition (ecs-task-definition.json)
{
    "family": "cv-service",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["EC2"],
    "cpu": "4096",
    "memory": "16384",
    "containerDefinitions": [
        {
            "name": "cv-service",
            "image": "your-ecr-repo/cv-service:gpu",
            "portMappings": [
                {
                    "containerPort": 8080,
                    "protocol": "tcp"
                }
            ],
            "resourceRequirements": [
                {
                    "type": "GPU",
                    "value": "1"
                }
            ],
            "environment": [
                {"name": "CV_MODEL_BASE_PATH", "value": "/app/saved_models"}
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/cv-service",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
```

---

## Cost Optimization

### 1. Use Spot Instances

Save up to 90% on GPU instances:

```bash
aws ec2 request-spot-instances \
    --instance-count 1 \
    --type "one-time" \
    --launch-specification '{
        "ImageId": "ami-xxxxxxxx",
        "InstanceType": "g4dn.xlarge",
        "KeyName": "your-key"
    }'
```

### 2. Auto-Scaling Based on Training Jobs

Scale down when idle:

```yaml
# cloudwatch-alarm.yaml
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  ScaleDownAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: cv-service-idle
      MetricName: CPUUtilization
      Namespace: AWS/EC2
      Statistic: Average
      Period: 300
      EvaluationPeriods: 3
      Threshold: 10
      ComparisonOperator: LessThanThreshold
```

### 3. Scheduled Scaling

Run GPU instances only during work hours:

```bash
# Start at 9 AM
aws events put-rule \
    --name "start-cv-gpu" \
    --schedule-expression "cron(0 9 ? * MON-FRI *)"

# Stop at 6 PM
aws events put-rule \
    --name "stop-cv-gpu" \
    --schedule-expression "cron(0 18 ? * MON-FRI *)"
```

### 4. Use S3 for Model Storage

```bash
# Upload trained models to S3
aws s3 cp /app/saved_models s3://your-bucket/cv-models/ --recursive

# Download when needed
aws s3 sync s3://your-bucket/cv-models/ /app/saved_models/
```

---

## Monitoring

### Health Check Endpoint

```bash
# Check service health
curl http://<ec2-ip>:8080/health

# Expected response:
# {"status":"healthy","service":"cv","gpu_available":true,"device":"cuda"}
```

### CloudWatch Metrics

```bash
# Install CloudWatch agent
sudo apt-get install amazon-cloudwatch-agent

# Configure GPU metrics
cat << 'EOF' > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
{
    "metrics": {
        "namespace": "CVService",
        "metrics_collected": {
            "nvidia_gpu": {
                "measurement": [
                    "utilization_gpu",
                    "utilization_memory",
                    "temperature_gpu"
                ],
                "metrics_collection_interval": 60
            }
        }
    }
}
EOF

# Start agent
sudo systemctl start amazon-cloudwatch-agent
```

### Training Job Monitoring

```bash
# Watch training logs
docker logs -f cv-service-gpu 2>&1 | grep -E "(Epoch|Loss|completed)"
```

---

## Quick Start Script

Save this as `deploy-cv-service.sh`:

```bash
#!/bin/bash
set -e

echo "=== CV Service GPU Deployment ==="

# Update system
sudo apt-get update

# Verify GPU
nvidia-smi || { echo "GPU not available"; exit 1; }

# Clone/copy service files
mkdir -p ~/cv-service
cd ~/cv-service

# Build and run
docker-compose --profile gpu up -d --build

# Wait for health
echo "Waiting for service to be healthy..."
for i in {1..30}; do
    if curl -s http://localhost:8080/health | grep -q "healthy"; then
        echo "CV Service is running!"
        curl http://localhost:8080/health
        exit 0
    fi
    sleep 2
done

echo "Service failed to start"
docker-compose logs
exit 1
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CV_SERVICE_URL` | `http://localhost:8080` | For warpcore backend |
| `CV_MODEL_BASE_PATH` | `/app/saved_models` | Model storage path |
| `NVIDIA_VISIBLE_DEVICES` | `all` | GPU devices to use |

Update your warpcore `.env`:

```env
CV_SERVICE_URL=http://<ec2-private-ip>:8080
```

---

## Troubleshooting

### GPU Not Detected

```bash
# Check NVIDIA driver
dmesg | grep -i nvidia

# Reinstall drivers
sudo apt-get install --reinstall nvidia-driver-525
sudo reboot
```

### Out of GPU Memory

```bash
# Clear GPU memory
nvidia-smi --gpu-reset

# Or in Python
import torch
torch.cuda.empty_cache()
```

### Docker Permission Denied

```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## Support

For issues:
1. Check service logs: `docker-compose logs cv-service-gpu`
2. Verify GPU: `nvidia-smi`
3. Test health: `curl http://localhost:8080/health`
