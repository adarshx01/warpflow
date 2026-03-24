"""ElevenLabs service router for text-to-speech."""

import logging
import base64
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database import get_db
from app.models import User, UserSecret
from app.auth.utils import get_current_user
from app.rate_limit import limiter
from app.security import decrypt_value

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/elevenlabs", tags=["elevenlabs"])

ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"


class ElevenLabsExecuteRequest(BaseModel):
    """Request body for executing ElevenLabs operations."""
    operation: str
    params: Dict[str, Any]


async def _get_elevenlabs_api_key(db: AsyncSession, owner_id: UUID) -> str:
    """Fetch and decrypt ElevenLabs API key."""
    result = await db.execute(
        select(UserSecret).where(
            UserSecret.owner_id == owner_id,
            UserSecret.secret_key == 'elevenlabs_api_key'
        )
    )
    secret = result.scalar_one_or_none()

    if not secret:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ElevenLabs API key not found. Please configure it in the node settings."
        )

    api_key = decrypt_value(secret.encrypted_value)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ElevenLabs API key is empty. Please reset and re-enter it."
        )

    return api_key


async def text_to_speech(api_key: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Convert text to speech using ElevenLabs."""
    text = params.get('text')
    voice_id = params.get('voice_id')
    model_id = params.get('model_id', 'eleven_v3')
    stability = params.get('stability', 0.5)
    similarity_boost = params.get('similarity_boost', 0.5)

    if not text:
        raise HTTPException(status_code=400, detail="'text' is required")
    if not voice_id:
        raise HTTPException(status_code=400, detail="'voice_id' is required")

    url = f"{ELEVENLABS_API_BASE}/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)

        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"ElevenLabs API error: {error_detail}")
            raise HTTPException(status_code=response.status_code, detail=f"ElevenLabs API error: {error_detail}")

        # Return audio as base64 encoded string
        audio_base64 = base64.b64encode(response.content).decode('utf-8')

        return {
            "audio_base64": audio_base64,
            "content_type": response.headers.get("content-type", "audio/mpeg"),
            "text": text,
            "voice_id": voice_id,
            "model_id": model_id
        }


async def list_voices(api_key: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """List all available ElevenLabs voices."""
    url = f"{ELEVENLABS_API_BASE}/voices"
    headers = {"xi-api-key": api_key}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=30.0)

        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"ElevenLabs API error: {error_detail}")
            raise HTTPException(status_code=response.status_code, detail=f"ElevenLabs API error: {error_detail}")

        return response.json()


async def get_voice(api_key: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Get details of a specific voice."""
    voice_id = params.get('voice_id')

    if not voice_id:
        raise HTTPException(status_code=400, detail="'voice_id' is required")

    url = f"{ELEVENLABS_API_BASE}/voices/{voice_id}"
    headers = {"xi-api-key": api_key}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=30.0)

        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"ElevenLabs API error: {error_detail}")
            raise HTTPException(status_code=response.status_code, detail=f"ElevenLabs API error: {error_detail}")

        return response.json()


@router.get("/voices")
async def get_voices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all available voices for the frontend dropdown."""
    try:
        api_key = await _get_elevenlabs_api_key(db, current_user.id)
        result = await list_voices(api_key, {})
        return result
    except HTTPException:
        # Return empty list if API key not configured yet
        return {"voices": []}


@router.post("/execute")
@limiter.limit("20/minute")
async def execute_operation(
    request: Request,
    body: ElevenLabsExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute an ElevenLabs operation."""
    api_key = await _get_elevenlabs_api_key(db, current_user.id)

    operations = {
        'text_to_speech': text_to_speech,
        'list_voices': list_voices,
        'get_voice': get_voice,
    }

    operation_fn = operations.get(body.operation)
    if not operation_fn:
        raise HTTPException(status_code=400, detail=f"Unknown operation: {body.operation}")

    try:
        result = await operation_fn(api_key, body.params)
        return result
    except Exception as e:
        logger.exception(f"ElevenLabs operation failed: {body.operation}")
        raise HTTPException(status_code=500, detail=str(e))
