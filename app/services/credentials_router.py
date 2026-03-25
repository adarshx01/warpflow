import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import User, Credential, UserSecret
from app.auth.utils import get_current_user
from app.schemas import CredentialCreate, CredentialResponse
from app.security import encrypt_value

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


def _to_response(cred: Credential) -> CredentialResponse:
    return CredentialResponse(
        id=cred.id,
        type=cred.type,
        name=cred.name,
        has_tokens=cred.access_token is not None,
    )


# ──────────────────────────────────────────────
# List credentials (optionally filtered by type)
# ──────────────────────────────────────────────

@router.get("", response_model=list[CredentialResponse])
async def list_credentials(
    type: str | None = Query(None, description="Filter by credential type, e.g. 'google-docs'"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all credentials belonging to the authenticated user."""
    stmt = select(Credential).where(Credential.owner_id == current_user.id)
    if type:
        stmt = stmt.where(Credential.type == type)
    stmt = stmt.order_by(Credential.created_at.desc())
    result = await db.execute(stmt)
    return [_to_response(c) for c in result.scalars().all()]


# ──────────────────────────────────────────────
# Create credential
# ──────────────────────────────────────────────

@router.post("", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_credential(
    body: CredentialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Store a new credential for the authenticated user."""
    # For Google services, use env credentials
    if body.type.startswith("google-"):
        settings = get_settings()
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth credentials not configured in environment",
            )
        client_id = settings.GOOGLE_CLIENT_ID
        client_secret = settings.GOOGLE_CLIENT_SECRET
    else:
        client_id = body.client_id
        client_secret = body.client_secret

    cred = Credential(
        owner_id=current_user.id,
        type=body.type,
        name=body.name,
        client_id=encrypt_value(client_id),
        client_secret=encrypt_value(client_secret),
    )
    db.add(cred)

    await db.commit()
    await db.refresh(cred)
    logger.info("Created credential %s for user %s", cred.id, current_user.id)
    return _to_response(cred)


# ──────────────────────────────────────────────
# Delete credential
# ──────────────────────────────────────────────

@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a credential. Must belong to the authenticated user."""
    stmt = select(Credential).where(
        Credential.id == credential_id,
        Credential.owner_id == current_user.id,
    )
    result = await db.execute(stmt)
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    await db.delete(cred)
    await db.commit()
    logger.info("Deleted credential %s for user %s", credential_id, current_user.id)
