# CV Service Dockerfile
# Unified microservice for training and inference

# ─── Base Stage ───────────────────────────────────────────────────────────────
FROM python:3.10-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ─── Dependencies Stage ───────────────────────────────────────────────────────
FROM base AS dependencies

# Install UV for faster package installation
RUN pip install --no-cache-dir uv

COPY requirements.txt .

# Install Python dependencies with UV
RUN uv pip install --system --no-cache -r requirements.txt

# ─── Production Stage ─────────────────────────────────────────────────────────
FROM dependencies AS production

COPY . .

# Create directories for saved models and data
RUN mkdir -p /app/saved_models /app/data

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV CV_MODEL_BASE_PATH=/app/saved_models
ENV PYTHONPATH=/app

# Single port for unified service
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health')" || exit 1

# Entry point
ENTRYPOINT ["python", "main.py"]
CMD ["--port", "8080", "--host", "0.0.0.0"]

# ─── GPU Stage (for NVIDIA GPU support) ──────────────────────────────────────
FROM nvidia/cuda:11.8-cudnn8-runtime-ubuntu22.04 AS gpu

WORKDIR /app

# Install Python and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3.10-venv \
    build-essential \
    cmake \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.10 /usr/bin/python

# Install UV
RUN pip install --no-cache-dir uv

COPY requirements.txt .

# Install PyTorch with CUDA support
RUN uv pip install --system --no-cache torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Install remaining dependencies
RUN uv pip install --system --no-cache -r requirements.txt

COPY . .

RUN mkdir -p /app/saved_models /app/data

ENV PYTHONUNBUFFERED=1
ENV CV_MODEL_BASE_PATH=/app/saved_models
ENV PYTHONPATH=/app
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health')" || exit 1

ENTRYPOINT ["python", "main.py"]
CMD ["--port", "8080", "--host", "0.0.0.0"]