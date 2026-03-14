"""
Shared helpers for all Google Workspace service integrations.
Handles credential lookup, token refresh, and common error handling.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Credential
from app.security import decrypt_value, encrypt_value

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"


async def get_user_credential(
    db: AsyncSession,
    credential_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> Credential:
    """Fetch a credential and verify ownership."""
    stmt = select(Credential).where(
        Credential.id == credential_id,
        Credential.owner_id == owner_id,
    )
    result = await db.execute(stmt)
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    return cred


async def get_valid_access_token(credential: Credential, db: AsyncSession) -> str:
    """Return a valid access token, auto-refreshing if expired."""
    access_token = decrypt_value(credential.access_token)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account not connected. Please complete OAuth flow.",
        )

    if credential.token_expiry and credential.token_expiry > datetime.now(timezone.utc):
        return access_token

    refresh_token = decrypt_value(credential.refresh_token)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account not connected. Please complete OAuth flow.",
        )

    client_id = decrypt_value(credential.client_id)
    client_secret = decrypt_value(credential.client_secret)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("Token refresh failed: %s", exc.response.text)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to refresh Google access token: {exc.response.text}",
            )

    token_data = resp.json()
    credential.access_token = encrypt_value(token_data["access_token"])
    expires_in = token_data.get("expires_in", 3600)
    credential.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    await db.commit()
    return token_data["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def handle_google_error(exc: httpx.HTTPStatusError) -> None:
    try:
        detail = exc.response.json()
    except Exception:
        detail = exc.response.text
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=detail,
    )


async def google_oauth_start(
    credential: Credential,
    scopes: list[str],
    redirect_uri: str,
) -> str:
    """Build Google OAuth consent screen URL."""
    from urllib.parse import urlencode

    client_id = decrypt_value(credential.client_id)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": str(credential.id),
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def google_oauth_callback(
    code: str,
    state: str,
    redirect_uri: str,
    db: AsyncSession,
    frontend_success_url: str,
) -> Credential:
    """Exchange auth code for tokens and store them on the credential."""
    try:
        cred_id = uuid.UUID(state)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state")

    stmt = select(Credential).where(Credential.id == cred_id)
    result = await db.execute(stmt)
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    client_id = decrypt_value(cred.client_id)
    client_secret = decrypt_value(cred.client_secret)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("OAuth code exchange failed: %s", exc.response.text)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google OAuth failed: {exc.response.text}",
            )

    token_data = resp.json()
    cred.access_token = encrypt_value(token_data["access_token"])
    new_refresh_token = token_data.get("refresh_token")
    if new_refresh_token:
        cred.refresh_token = encrypt_value(new_refresh_token)
    expires_in = token_data.get("expires_in", 3600)
    cred.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    await db.commit()
    logger.info("OAuth tokens stored for credential %s", cred_id)
    return cred
