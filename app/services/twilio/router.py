"""Twilio service router for phone calls and SMS."""

import logging
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserSecret
from app.auth.utils import get_current_user
from app.rate_limit import limiter
from app.security import decrypt_value

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/twilio", tags=["twilio"])


class TwilioExecuteRequest(BaseModel):
    """Request body for executing Twilio operations."""
    operation: str
    params: Dict[str, Any]


async def _get_twilio_credentials(db: AsyncSession, owner_id: UUID) -> tuple[str, str]:
    """Fetch and decrypt Twilio Account SID and Auth Token."""
    result = await db.execute(
        select(UserSecret).where(
            UserSecret.owner_id == owner_id,
            UserSecret.secret_key.in_(['twilio_account_sid', 'twilio_auth_token'])
        )
    )
    secrets = {s.secret_key: s for s in result.scalars().all()}

    account_sid_secret = secrets.get('twilio_account_sid')
    auth_token_secret = secrets.get('twilio_auth_token')

    if not account_sid_secret or not auth_token_secret:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Twilio credentials not found. Please configure Account SID and Auth Token."
        )

    account_sid = decrypt_value(account_sid_secret.encrypted_value)
    auth_token = decrypt_value(auth_token_secret.encrypted_value)

    if not account_sid or not auth_token:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Twilio credentials are empty. Please reset and re-enter them."
        )

    return account_sid, auth_token


async def make_call(account_sid: str, auth_token: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Make an outbound phone call using Twilio."""
    try:
        from twilio.rest import Client
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Twilio library not installed. Please install twilio package."
        )

    to = params.get('to')
    from_ = params.get('from')
    twiml = params.get('twiml')
    status_callback = params.get('statusCallback')

    if not to or not from_:
        raise HTTPException(status_code=400, detail="'to' and 'from' phone numbers are required")

    if not twiml:
        raise HTTPException(
            status_code=400,
            detail="'twiml' is required. Provide TwiML instructions (e.g., '<Response><Say>Hello!</Say></Response>') or a URL to fetch TwiML from."
        )

    client = Client(account_sid, auth_token)

    call_params = {'to': to, 'from_': from_}

    if twiml:
        if twiml.startswith('http://') or twiml.startswith('https://'):
            call_params['url'] = twiml
        else:
            call_params['twiml'] = twiml

    if status_callback:
        call_params['status_callback'] = status_callback

    call = client.calls.create(**call_params)

    return {
        'sid': call.sid,
        'status': call.status,
        'to': call.to,
        'from': getattr(call, 'from_', None) or getattr(call, 'from_number', None) or from_,
        'date_created': call.date_created.isoformat() if call.date_created else None,
    }


async def send_sms(account_sid: str, auth_token: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Send an SMS using Twilio."""
    try:
        from twilio.rest import Client
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Twilio library not installed. Please install twilio package."
        )

    to = params.get('to')
    from_ = params.get('from')
    body = params.get('body')

    if not to or not from_ or not body:
        raise HTTPException(status_code=400, detail="'to', 'from', and 'body' are required")

    client = Client(account_sid, auth_token)
    message = client.messages.create(to=to, from_=from_, body=body)

    return {
        'sid': message.sid,
        'status': message.status,
        'to': message.to,
        'from': getattr(message, 'from_', None) or from_,
        'body': message.body,
        'date_created': message.date_created.isoformat() if message.date_created else None,
    }


async def get_call_status(account_sid: str, auth_token: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Get the status of a call."""
    try:
        from twilio.rest import Client
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Twilio library not installed. Please install twilio package."
        )

    sid = params.get('sid')
    if not sid:
        raise HTTPException(status_code=400, detail="'sid' is required")

    client = Client(account_sid, auth_token)
    call = client.calls(sid).fetch()

    return {
        'sid': call.sid,
        'status': call.status,
        'to': call.to,
        'from': getattr(call, 'from_', None),
        'duration': call.duration,
        'date_created': call.date_created.isoformat() if call.date_created else None,
    }


async def get_message_status(account_sid: str, auth_token: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Get the status of an SMS message."""
    try:
        from twilio.rest import Client
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Twilio library not installed. Please install twilio package."
        )

    sid = params.get('sid')
    if not sid:
        raise HTTPException(status_code=400, detail="'sid' is required")

    client = Client(account_sid, auth_token)
    message = client.messages(sid).fetch()

    return {
        'sid': message.sid,
        'status': message.status,
        'to': message.to,
        'from': getattr(message, 'from_', None),
        'body': message.body,
        'date_created': message.date_created.isoformat() if message.date_created else None,
    }


@router.post("/execute")
@limiter.limit("20/minute")
async def execute_operation(
    request: Request,
    body: TwilioExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a Twilio operation."""
    account_sid, auth_token = await _get_twilio_credentials(db, current_user.id)

    operations = {
        'make_call': make_call,
        'send_sms': send_sms,
        'get_call_status': get_call_status,
        'get_message_status': get_message_status,
    }

    operation_fn = operations.get(body.operation)
    if not operation_fn:
        raise HTTPException(status_code=400, detail=f"Unknown operation: {body.operation}")

    try:
        result = await operation_fn(account_sid, auth_token, body.params)
        return result
    except Exception as e:
        logger.exception(f"Twilio operation failed: {body.operation}")
        raise HTTPException(status_code=500, detail=str(e))
