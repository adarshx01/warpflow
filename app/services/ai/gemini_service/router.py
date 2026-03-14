"""
Google Gemini router: execute endpoint for Gemini API.
API key is provided per-request from the frontend node config.
"""
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.models import User
from app.auth.utils import get_current_user
from app.rate_limit import limiter
from app.services.ai.gemini_service.schemas import GeminiExecuteRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gemini", tags=["gemini"])

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

AVAILABLE_MODELS = [
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "description": "Fast and versatile"},
    {"id": "gemini-3-flash-preview", "name": "Gemini 3 Flash Preview", "description": "Next-gen fast model"},
    {"id": "gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro Preview", "description": "Most capable model"},
    {"id": "gemini-3.1-flash-lite-preview", "name": "Gemini 3.1 Flash Lite Preview", "description": "Lightweight and efficient"},
]


@router.get("/models")
async def list_models(
    current_user: User = Depends(get_current_user),
):
    """Return available Gemini models."""
    return AVAILABLE_MODELS


async def generate_content(api_key: str, params: dict[str, Any]) -> dict:
    """Generate content using Gemini models."""
    model = params.get("model", "gemini-3-flash-preview")
    prompt = params.get("prompt", "")
    system_instruction = params.get("systemInstruction")
    temperature = params.get("temperature", 0.7)
    max_tokens = params.get("maxTokens", 1024)

    if not prompt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="prompt is required")

    body: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{GEMINI_API_BASE}/{model}:generateContent",
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json=body,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json()
            except Exception:
                detail = exc.response.text
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail,
            )

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return {"content": "", "finishReason": "UNKNOWN", "usage": data.get("usageMetadata")}

    candidate = candidates[0]
    parts = candidate.get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)

    return {
        "content": text,
        "finishReason": candidate.get("finishReason"),
        "usage": data.get("usageMetadata"),
        "model": model,
    }


async def chat(api_key: str, params: dict[str, Any]) -> dict:
    """Multi-turn chat using Gemini."""
    model = params.get("model", "gemini-3-flash-preview")
    messages = params.get("messages", [])
    system_instruction = params.get("systemInstruction")
    temperature = params.get("temperature", 0.7)
    max_tokens = params.get("maxTokens", 1024)

    if not messages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="messages is required")

    # Convert messages to Gemini format
    contents = []
    for msg in messages:
        role = "user" if msg.get("role", "user") == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg.get("content", "")}],
        })

    body: dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{GEMINI_API_BASE}/{model}:generateContent",
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json=body,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json()
            except Exception:
                detail = exc.response.text
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail,
            )

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return {"content": "", "finishReason": "UNKNOWN", "usage": data.get("usageMetadata")}

    candidate = candidates[0]
    parts = candidate.get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)

    return {
        "content": text,
        "role": "model",
        "finishReason": candidate.get("finishReason"),
        "usage": data.get("usageMetadata"),
        "model": model,
    }


@router.post("/execute")
@limiter.limit("20/minute")
async def execute(
    request: Request,
    body: GeminiExecuteRequest,
    current_user: User = Depends(get_current_user),
):
    match body.operation:
        case "generate_content":
            return await generate_content(body.apiKey, body.params)
        case "chat":
            return await chat(body.apiKey, body.params)
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown operation: {body.operation}",
            )
