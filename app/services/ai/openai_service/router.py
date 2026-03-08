"""
OpenAI / ChatGPT router: execute endpoint for OpenAI API.
API key is provided per-request from the frontend node config.
"""
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.models import User
from app.auth.utils import get_current_user
from app.rate_limit import limiter
from app.services.ai.openai_service.schemas import OpenAIExecuteRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/openai", tags=["openai"])

OPENAI_API_BASE = "https://api.openai.com/v1"


async def chat_completion(api_key: str, params: dict[str, Any]) -> dict:
    """Generate a chat completion using OpenAI GPT models."""
    model = params.get("model", "gpt-3.5-turbo")
    messages = params.get("messages", [])
    temperature = params.get("temperature", 0.7)
    max_tokens = params.get("maxTokens", 1024)
    system_prompt = params.get("systemPrompt")

    if not messages and not system_prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'messages' or 'systemPrompt' with user input is required",
        )

    # Build messages list
    api_messages = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})

    if isinstance(messages, list) and messages:
        api_messages.extend(messages)
    elif params.get("prompt"):
        api_messages.append({"role": "user", "content": params["prompt"]})

    if not api_messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages to send",
        )

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{OPENAI_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": api_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
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
    choice = data.get("choices", [{}])[0]
    return {
        "content": choice.get("message", {}).get("content", ""),
        "role": choice.get("message", {}).get("role", "assistant"),
        "model": data.get("model"),
        "usage": data.get("usage"),
        "finishReason": choice.get("finish_reason"),
    }


async def image_generation(api_key: str, params: dict[str, Any]) -> dict:
    """Generate images using DALL-E."""
    prompt = params.get("prompt")
    if not prompt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="prompt is required")

    model = params.get("model", "dall-e-3")
    size = params.get("size", "1024x1024")
    n = min(params.get("n", 1), 4)

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                f"{OPENAI_API_BASE}/images/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "prompt": prompt,
                    "size": size,
                    "n": n,
                },
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
    return {
        "images": [
            {"url": img.get("url"), "revisedPrompt": img.get("revised_prompt")}
            for img in data.get("data", [])
        ],
    }


@router.post("/execute")
@limiter.limit("20/minute")
async def execute(
    request: Request,
    body: OpenAIExecuteRequest,
    current_user: User = Depends(get_current_user),
):
    match body.operation:
        case "chat_completion":
            return await chat_completion(body.apiKey, body.params)
        case "image_generation":
            return await image_generation(body.apiKey, body.params)
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown operation: {body.operation}",
            )
