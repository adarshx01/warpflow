"""
Shared OAuth + execute router factory for all Google Workspace services.
Each service (gmail, google-docs, google-drive, google-forms, google-sheets)
gets its own router built from this factory.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import GoogleCredential, User
from app.auth.utils import get_current_user
from app.google_workspace.oauth_helper import (
    build_auth_url,
    exchange_code_for_tokens,
    refresh_access_token,
    token_expiry_from_response,
)

FRONTEND_CALLBACK_PAGE = "http://localhost:5173"


# ── Execute request schema ────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    credentialId: str
    operation: str
    params: dict[str, Any] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_credential(
    db: AsyncSession,
    credential_id: str,
    owner_id: uuid.UUID,
    service: str,
) -> GoogleCredential:
    try:
        cid = uuid.UUID(credential_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid credential ID")
    stmt = select(GoogleCredential).where(
        GoogleCredential.id == cid,
        GoogleCredential.owner_id == owner_id,
        GoogleCredential.type == service,
    )
    result = await db.execute(stmt)
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    return cred


async def _ensure_fresh_token(db: AsyncSession, cred: GoogleCredential) -> str:
    """Return a valid access token, refreshing if expired or missing."""
    if not cred.refresh_token:
        raise HTTPException(
            status_code=400,
            detail="Google account not connected. Please complete the OAuth flow.",
        )
    now = datetime.now(timezone.utc)
    token_expired = cred.token_expiry is None or cred.token_expiry <= now
    if not cred.access_token or token_expired:
        data = await refresh_access_token(
            cred.client_id, cred.client_secret, cred.refresh_token
        )
        cred.access_token = data["access_token"]
        cred.token_expiry = token_expiry_from_response(data)
        await db.commit()
    return cred.access_token  # type: ignore[return-value]


# ── Router factory ────────────────────────────────────────────────────────────

def make_google_service_router(service: str, execute_fn) -> APIRouter:
    """
    Build a FastAPI router for a Google Workspace service with:
      GET  /oauth/start   — redirect user to Google consent page
      GET  /oauth/callback — exchange auth code, store tokens
      POST /execute        — call execute_fn with a valid access token
    """
    router = APIRouter(prefix=f"/api/{service}", tags=[service])

    @router.get("/oauth/start")
    async def oauth_start(
        credential_id: str = Query(...),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        cred = await _get_credential(db, credential_id, current_user.id, service)
        url = build_auth_url(service, cred.client_id, credential_id)
        return RedirectResponse(url)

    @router.get("/oauth/callback")
    async def oauth_callback(
        code: str = Query(...),
        state: str = Query(...),  # credential_id passed as state
        db: AsyncSession = Depends(get_db),
    ):
        # state = credential_id (no auth required — Google redirects here)
        try:
            cid = uuid.UUID(state)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid state")

        stmt = select(GoogleCredential).where(GoogleCredential.id == cid)
        result = await db.execute(stmt)
        cred = result.scalar_one_or_none()
        if not cred:
            raise HTTPException(status_code=404, detail="Credential not found")

        token_data = await exchange_code_for_tokens(
            service, cred.client_id, cred.client_secret, code
        )
        cred.access_token = token_data.get("access_token")
        cred.refresh_token = token_data.get("refresh_token", cred.refresh_token)
        cred.token_expiry = token_expiry_from_response(token_data)
        await db.commit()

        # Redirect back to the frontend with a success flag
        return RedirectResponse(f"{FRONTEND_CALLBACK_PAGE}?google_oauth=success&service={service}")

    @router.post("/execute")
    async def execute(
        body: ExecuteRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        cred = await _get_credential(db, body.credentialId, current_user.id, service)
        access_token = await _ensure_fresh_token(db, cred)
        return await execute_fn(access_token, body.operation, body.params)

    return router
