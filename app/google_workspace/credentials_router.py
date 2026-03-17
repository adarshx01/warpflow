"""
Generic /api/credentials router — handles all Google Workspace credential types.
Credential types: gmail, google-docs, google-drive, google-forms, google-sheets
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import GoogleCredential, User
from app.auth.utils import get_current_user

router = APIRouter(prefix="/api/credentials", tags=["credentials"])

VALID_TYPES = {"gmail", "google-docs", "google-drive", "google-forms", "google-sheets"}


# ── Schemas ──────────────────────────────────────────────────────────────────

class CredentialCreate(BaseModel):
    type: str
    name: str
    client_id: str
    client_secret: str


class CredentialResponse(BaseModel):
    id: str
    name: str
    type: str
    connected: bool  # True if tokens have been obtained via OAuth

    class Config:
        from_attributes = True


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("", response_model=list[CredentialResponse])
async def list_credentials(
    type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List credentials for the current user, optionally filtered by type."""
    stmt = select(GoogleCredential).where(GoogleCredential.owner_id == current_user.id)
    if type:
        if type not in VALID_TYPES:
            raise HTTPException(status_code=400, detail=f"Unknown credential type: {type}")
        stmt = stmt.where(GoogleCredential.type == type)
    result = await db.execute(stmt)
    creds = result.scalars().all()
    return [
        CredentialResponse(
            id=str(c.id),
            name=c.name,
            type=c.type,
            connected=bool(c.refresh_token),
        )
        for c in creds
    ]


@router.post("", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_credential(
    body: CredentialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a new Google OAuth client credential (client_id + client_secret)."""
    if body.type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown credential type: {body.type}")

    cred = GoogleCredential(
        owner_id=current_user.id,
        type=body.type,
        name=body.name,
        client_id=body.client_id,
        client_secret=body.client_secret,
    )
    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return CredentialResponse(
        id=str(cred.id),
        name=cred.name,
        type=cred.type,
        connected=False,
    )
