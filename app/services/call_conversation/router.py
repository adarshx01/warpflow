"""
Call Conversation Router: Bidirectional voice calls via Twilio + ElevenLabs.

Flow:
  1. POST /api/call-conversation/start  → initiates outbound call
  2. Twilio calls POST /api/call-conversation/twiml/{session_id} → returns <Connect><Stream>
  3. Twilio connects WS /api/call-conversation/ws/{session_id} → audio bridge begins
  4. Bridge: Twilio audio ↔ [mulaw↔PCM] ↔ ElevenLabs Conversational AI WS
"""

import asyncio
import base64
import json
import logging
import uuid
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import websockets
import websockets.exceptions

from app.database import get_db
from app.models import User, UserSecret
from app.auth.utils import get_current_user
from app.rate_limit import limiter
from app.security import decrypt_value
from app.config import get_settings
from app.services.call_conversation.audio_utils import (
    twilio_media_to_pcm,
    pcm_to_twilio_media,
    chunk_audio,
    pcm16k_to_mulaw,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/call-conversation", tags=["call-conversation"])

# ─── In-memory session store ────────────────────────
# Maps session_id -> session config dict
_sessions: Dict[str, Dict[str, Any]] = {}

ELEVENLABS_CONVAI_WS = "wss://api.elevenlabs.io/v1/convai/conversation"


class StartConversationRequest(BaseModel):
    """Request body for starting a conversational call."""
    to: str  # E.164 phone number to call
    from_number: str  # Twilio phone number
    system_prompt: str = "You are a helpful AI assistant having a phone conversation."
    first_message: str = "Hello! How can I help you today?"
    voice_id: Optional[str] = None  # ElevenLabs voice ID (optional)
    model_id: Optional[str] = None  # ElevenLabs TTS model (optional)


class ConversationResult(BaseModel):
    """Response from starting a conversation call."""
    session_id: str
    call_sid: str
    status: str
    to: str
    from_number: str


# ─── Credential helpers ─────────────────────────────

async def _get_twilio_credentials(db: AsyncSession, owner_id: UUID) -> tuple[str, str]:
    """Fetch Twilio Account SID and Auth Token from secrets."""
    result = await db.execute(
        select(UserSecret).where(
            UserSecret.owner_id == owner_id,
            UserSecret.secret_key.in_(['twilio_account_sid', 'twilio_auth_token'])
        )
    )
    secrets = {s.secret_key: s for s in result.scalars().all()}

    sid_secret = secrets.get('twilio_account_sid')
    token_secret = secrets.get('twilio_auth_token')

    if not sid_secret or not token_secret:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Twilio credentials not found. Please configure Account SID and Auth Token."
        )

    return decrypt_value(sid_secret.encrypted_value), decrypt_value(token_secret.encrypted_value)


async def _get_elevenlabs_api_key(db: AsyncSession, owner_id: UUID) -> str:
    """Fetch ElevenLabs API key from secrets."""
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
            detail="ElevenLabs API key not found. Please configure it."
        )

    api_key = decrypt_value(secret.encrypted_value)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ElevenLabs API key is empty."
        )
    return api_key


# ─── REST Endpoints ────────────────────────────────

@router.post("/start")
@limiter.limit("10/minute")
async def start_conversation(
    request: Request,
    body: StartConversationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initiate an outbound conversational phone call."""
    settings = get_settings()

    # Fetch credentials
    account_sid, auth_token = await _get_twilio_credentials(db, current_user.id)
    elevenlabs_key = await _get_elevenlabs_api_key(db, current_user.id)

    # Create session
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "owner_id": str(current_user.id),
        "system_prompt": body.system_prompt,
        "first_message": body.first_message,
        "voice_id": body.voice_id,
        "model_id": body.model_id,
        "elevenlabs_key": elevenlabs_key,
        "twilio_account_sid": account_sid,
        "twilio_auth_token": auth_token,
        "to": body.to,
        "from": body.from_number,
        "status": "initiating",
        "transcript": [],
    }

    # Build the TwiML URL that Twilio will fetch when call connects
    public_url = settings.PUBLIC_BASE_URL.rstrip("/")
    twiml_url = f"{public_url}/api/call-conversation/twiml/{session_id}"

    # Make the outbound call via Twilio
    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)

        call = client.calls.create(
            to=body.to,
            from_=body.from_number,
            url=twiml_url,
            status_callback=f"{public_url}/api/call-conversation/status/{session_id}",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
        )

        _sessions[session_id]["call_sid"] = call.sid
        _sessions[session_id]["status"] = "queued"

        logger.info("Conversational call initiated: session=%s, call_sid=%s", session_id, call.sid)

        return {
            "session_id": session_id,
            "call_sid": call.sid,
            "status": "queued",
            "to": body.to,
            "from_number": body.from_number,
        }

    except Exception as e:
        _sessions.pop(session_id, None)
        logger.exception("Failed to initiate call: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to initiate call: {str(e)}")


@router.post("/twiml/{session_id}")
async def twiml_webhook(session_id: str, request: Request):
    """TwiML webhook — Twilio fetches this when call connects.

    Returns <Connect><Stream> TwiML to start bidirectional audio streaming.
    """
    session = _sessions.get(session_id)
    if not session:
        logger.warning("TwiML requested for unknown session: %s", session_id)
        return Response(
            content='<Response><Say>Sorry, this call session has expired.</Say></Response>',
            media_type="application/xml",
        )

    settings = get_settings()
    public_url = settings.PUBLIC_BASE_URL.rstrip("/")

    # Convert http(s) URL to ws(s) URL for WebSocket
    ws_url = public_url.replace("https://", "wss://").replace("http://", "ws://")
    stream_url = f"{ws_url}/api/call-conversation/ws/{session_id}"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{stream_url}" />
    </Connect>
</Response>"""

    logger.info("Returning TwiML for session %s, stream URL: %s", session_id, stream_url)

    return Response(content=twiml, media_type="application/xml")


@router.post("/status/{session_id}")
async def status_callback(session_id: str, request: Request):
    """Twilio status callback for call lifecycle events."""
    form_data = await request.form()
    call_status = form_data.get("CallStatus", "unknown")

    session = _sessions.get(session_id)
    if session:
        session["status"] = call_status
        logger.info("Call status update: session=%s, status=%s", session_id, call_status)

    return Response(content="", status_code=200)


@router.get("/session/{session_id}")
async def get_session_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the status and transcript of a call session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("owner_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    return {
        "session_id": session_id,
        "status": session.get("status", "unknown"),
        "call_sid": session.get("call_sid"),
        "transcript": session.get("transcript", []),
    }


# ─── WebSocket: Twilio ↔ ElevenLabs Bridge ─────────

@router.websocket("/ws/{session_id}")
async def websocket_bridge(websocket: WebSocket, session_id: str):
    """Bidirectional WebSocket bridge between Twilio and ElevenLabs.

    Twilio sends mulaw 8kHz audio → we convert to PCM 16kHz → send to ElevenLabs.
    ElevenLabs sends back PCM audio → we convert to mulaw 8kHz → send to Twilio.
    """
    await websocket.accept()

    session = _sessions.get(session_id)
    if not session:
        logger.warning("WebSocket connected for unknown session: %s", session_id)
        await websocket.close(code=4004, reason="Unknown session")
        return

    logger.info("Twilio WebSocket connected for session: %s", session_id)
    session["status"] = "connected"

    stream_sid = None
    elevenlabs_ws = None

    try:
        # Wait for Twilio's 'connected' and 'start' events
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            event = data.get("event")

            if event == "connected":
                logger.info("Twilio stream connected: session=%s", session_id)
                continue

            if event == "start":
                stream_sid = data.get("start", {}).get("streamSid")
                logger.info("Twilio stream started: session=%s, streamSid=%s", session_id, stream_sid)
                break

            if event == "stop":
                logger.info("Twilio stream stopped before start: session=%s", session_id)
                return

        # ─── Connect to ElevenLabs Conversational AI ───
        elevenlabs_key = session["elevenlabs_key"]
        system_prompt = session["system_prompt"]
        first_message = session["first_message"]

        # Build ElevenLabs WebSocket URL with signed URL approach
        # We use the API key directly in headers for server-side connections
        el_headers = {
            "xi-api-key": elevenlabs_key,
        }

        # Build conversation config to send after connection
        conversation_config = {
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {
                    "prompt": {
                        "prompt": system_prompt,
                    },
                    "first_message": first_message,
                },
                "tts": {
                    "output_format": "ulaw_8000",
                },
            },
        }

        # Add optional voice config
        if session.get("voice_id"):
            conversation_config["conversation_config_override"]["tts"]["voice_id"] = session["voice_id"]

        # Connect to ElevenLabs - use agent_id if provided, otherwise create a default agent
        el_url = f"{ELEVENLABS_CONVAI_WS}?agent_id=default"

        try:
            elevenlabs_ws = await websockets.connect(
                el_url,
                additional_headers=el_headers,
                ping_interval=20,
                ping_timeout=10,
            )
            logger.info("ElevenLabs WebSocket connected for session: %s", session_id)
        except Exception as e:
            logger.error("Failed to connect to ElevenLabs: %s", e)
            session["status"] = "error"
            session["error"] = f"ElevenLabs connection failed: {str(e)}"
            await websocket.close(code=4500, reason="ElevenLabs connection failed")
            return

        # Send conversation config
        await elevenlabs_ws.send(json.dumps(conversation_config))
        logger.info("Sent conversation config to ElevenLabs for session: %s", session_id)

        session["status"] = "in_call"

        # ─── Create bidirectional bridge tasks ───

        async def twilio_to_elevenlabs():
            """Forward audio from Twilio → ElevenLabs."""
            try:
                while True:
                    msg = await websocket.receive_text()
                    data = json.loads(msg)
                    event = data.get("event")

                    if event == "media":
                        payload = data.get("media", {}).get("payload", "")
                        if payload and elevenlabs_ws and elevenlabs_ws.open:
                            # Decode mulaw from Twilio
                            mulaw_bytes = base64.b64decode(payload)

                            # Send as base64-encoded audio to ElevenLabs
                            audio_message = {
                                "user_audio_chunk": base64.b64encode(mulaw_bytes).decode("ascii"),
                            }
                            await elevenlabs_ws.send(json.dumps(audio_message))

                    elif event == "stop":
                        logger.info("Twilio stream stopped: session=%s", session_id)
                        break

                    elif event == "mark":
                        # Mark events are acknowledgments
                        pass

            except WebSocketDisconnect:
                logger.info("Twilio WebSocket disconnected: session=%s", session_id)
            except Exception as e:
                logger.error("Error in twilio_to_elevenlabs: %s", e)

        async def elevenlabs_to_twilio():
            """Forward audio from ElevenLabs → Twilio."""
            try:
                async for message in elevenlabs_ws:
                    try:
                        data = json.loads(message)
                    except (json.JSONDecodeError, TypeError):
                        # Binary audio data
                        continue

                    msg_type = data.get("type")

                    if msg_type == "audio":
                        # ElevenLabs sends audio chunks
                        audio_data = data.get("audio", {})
                        audio_b64 = audio_data.get("chunk") or audio_data.get("data")

                        if audio_b64 and stream_sid:
                            # ElevenLabs with ulaw_8000 output format sends mulaw directly
                            # Forward as-is to Twilio
                            twilio_msg = {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {
                                    "payload": audio_b64,
                                },
                            }
                            await websocket.send_json(twilio_msg)

                    elif msg_type == "agent_response":
                        # Agent text response - add to transcript
                        text = data.get("agent_response_text", "") or data.get("text", "")
                        if text:
                            session.setdefault("transcript", []).append({
                                "role": "agent",
                                "text": text,
                            })
                            logger.info("Agent said: %s", text[:100])

                    elif msg_type == "user_transcript":
                        # User speech transcribed
                        text = data.get("user_transcript_text", "") or data.get("text", "")
                        if text:
                            session.setdefault("transcript", []).append({
                                "role": "user",
                                "text": text,
                            })
                            logger.info("User said: %s", text[:100])

                    elif msg_type == "conversation_initiation_metadata":
                        # Connection metadata from ElevenLabs
                        conversation_id = data.get("conversation_initiation_metadata_event", {}).get("conversation_id")
                        if conversation_id:
                            session["elevenlabs_conversation_id"] = conversation_id
                            logger.info("ElevenLabs conversation started: %s", conversation_id)

                    elif msg_type == "interruption":
                        # User interrupted the agent - send clear message to Twilio
                        if stream_sid:
                            clear_msg = {
                                "event": "clear",
                                "streamSid": stream_sid,
                            }
                            await websocket.send_json(clear_msg)
                            logger.info("User interruption detected, cleared Twilio buffer")

                    elif msg_type == "ping":
                        # Respond to ping
                        pong = {"type": "pong", "event_id": data.get("ping_event", {}).get("event_id")}
                        await elevenlabs_ws.send(json.dumps(pong))

                    elif msg_type == "error":
                        error_msg = data.get("message", "Unknown error")
                        logger.error("ElevenLabs error: %s", error_msg)

            except websockets.exceptions.ConnectionClosed:
                logger.info("ElevenLabs WebSocket closed: session=%s", session_id)
            except Exception as e:
                logger.error("Error in elevenlabs_to_twilio: %s", e)

        # Run both bridge tasks concurrently
        try:
            await asyncio.gather(
                twilio_to_elevenlabs(),
                elevenlabs_to_twilio(),
                return_exceptions=True,
            )
        except Exception as e:
            logger.error("Bridge error: %s", e)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: session=%s", session_id)
    except Exception as e:
        logger.exception("WebSocket error: session=%s, error=%s", session_id, e)
    finally:
        # Cleanup
        session["status"] = "completed"

        if elevenlabs_ws:
            try:
                await elevenlabs_ws.close()
            except Exception:
                pass

        # Keep session for a while for status queries, then clean up
        # (In production, use Redis or DB for persistent sessions)
        asyncio.get_event_loop().call_later(
            300,  # 5 minutes
            lambda: _sessions.pop(session_id, None),
        )

        logger.info("Call conversation ended: session=%s", session_id)


# ─── Agent Tool Function ──────────────────────────

async def start_conversation_call(
    user_id: str, params: dict[str, Any], db: AsyncSession
) -> dict:
    """Agent tool: start a conversational phone call.

    This is called by the AI agent engine when the agent decides to make
    a conversational call.
    """
    from uuid import UUID as _UUID

    to = params.get("to")
    from_number = params.get("from")
    system_prompt = params.get("system_prompt", "You are a helpful AI assistant having a phone conversation.")
    first_message = params.get("first_message", "Hello! How can I help you today?")
    voice_id = params.get("voice_id")

    if not to or not from_number:
        return {"error": "'to' and 'from' phone numbers are required"}

    settings = get_settings()

    # Fetch credentials
    owner_id = _UUID(user_id)

    result = await db.execute(
        select(UserSecret).where(
            UserSecret.owner_id == owner_id,
            UserSecret.secret_key.in_(['twilio_account_sid', 'twilio_auth_token'])
        )
    )
    twilio_secrets = {s.secret_key: s for s in result.scalars().all()}

    sid_secret = twilio_secrets.get('twilio_account_sid')
    token_secret = twilio_secrets.get('twilio_auth_token')

    if not sid_secret or not token_secret:
        return {"error": "Twilio credentials not configured"}

    account_sid = decrypt_value(sid_secret.encrypted_value)
    auth_token = decrypt_value(token_secret.encrypted_value)

    # Get ElevenLabs key
    result = await db.execute(
        select(UserSecret).where(
            UserSecret.owner_id == owner_id,
            UserSecret.secret_key == 'elevenlabs_api_key'
        )
    )
    el_secret = result.scalar_one_or_none()
    if not el_secret:
        return {"error": "ElevenLabs API key not configured"}

    elevenlabs_key = decrypt_value(el_secret.encrypted_value)

    # Create session
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "owner_id": user_id,
        "system_prompt": system_prompt,
        "first_message": first_message,
        "voice_id": voice_id,
        "model_id": None,
        "elevenlabs_key": elevenlabs_key,
        "twilio_account_sid": account_sid,
        "twilio_auth_token": auth_token,
        "to": to,
        "from": from_number,
        "status": "initiating",
        "transcript": [],
    }

    # Build TwiML URL
    public_url = settings.PUBLIC_BASE_URL.rstrip("/")
    twiml_url = f"{public_url}/api/call-conversation/twiml/{session_id}"

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)

        call = client.calls.create(
            to=to,
            from_=from_number,
            url=twiml_url,
            status_callback=f"{public_url}/api/call-conversation/status/{session_id}",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
        )

        _sessions[session_id]["call_sid"] = call.sid
        _sessions[session_id]["status"] = "queued"

        logger.info("Agent-initiated conversation call: session=%s, call_sid=%s", session_id, call.sid)

        return {
            "session_id": session_id,
            "call_sid": call.sid,
            "status": "queued",
            "to": to,
            "from_number": from_number,
            "message": (
                f"Conversational call initiated to {to}. "
                f"The AI agent will have a real-time voice conversation with the person. "
                f"System prompt: {system_prompt[:100]}..."
            ),
        }

    except Exception as e:
        _sessions.pop(session_id, None)
        logger.exception("Agent tool: Failed to initiate call: %s", e)
        return {"error": f"Failed to initiate call: {str(e)}"}
