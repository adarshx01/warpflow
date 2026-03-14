import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import get_current_user
from app.database import get_db
from app.models import User, UserSecret
from app.security import decrypt_value, encrypt_value

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/secrets", tags=["secrets"])


class SecretSetRequest(BaseModel):
    value: str


class SecretGetResponse(BaseModel):
    exists: bool
    # value is None for agent API keys — they are never returned to the frontend
    value: str | None = None


_ALLOWED_KEYS = {
    "google_oauth_client_id",
    "google_oauth_client_secret",
    "agent_openai_api_key",
    "agent_gemini_api_key",
}

# These keys hold credentials that are only used inside the backend.
# Their values are NEVER sent back to the frontend.
_BACKEND_ONLY_KEYS = {
    "agent_openai_api_key",
    "agent_gemini_api_key",
}


def _validate_key(secret_key: str) -> None:
    if secret_key not in _ALLOWED_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported secret key",
        )


@router.get("/{secret_key}", response_model=SecretGetResponse)
async def get_secret(
    secret_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_key(secret_key)

    stmt = select(UserSecret).where(
        UserSecret.owner_id == current_user.id,
        UserSecret.secret_key == secret_key,
    )
    secret = (await db.execute(stmt)).scalar_one_or_none()
    if not secret:
        return SecretGetResponse(exists=False, value=None)

    # Agent API keys are backend-only — never send the plaintext to the frontend
    if secret_key in _BACKEND_ONLY_KEYS:
        return SecretGetResponse(exists=True, value=None)

    return SecretGetResponse(
        exists=True,
        value=decrypt_value(secret.encrypted_value) or "",
    )


@router.put("/{secret_key}", status_code=status.HTTP_204_NO_CONTENT)
async def upsert_secret(
    secret_key: str,
    body: SecretSetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_key(secret_key)

    stmt = select(UserSecret).where(
        UserSecret.owner_id == current_user.id,
        UserSecret.secret_key == secret_key,
    )
    secret = (await db.execute(stmt)).scalar_one_or_none()
    encrypted = encrypt_value(body.value)

    if secret:
        secret.encrypted_value = encrypted
    else:
        db.add(
            UserSecret(
                owner_id=current_user.id,
                secret_key=secret_key,
                encrypted_value=encrypted,
            )
        )

    await db.commit()
    logger.info("Upserted secret key=%s for user=%s", secret_key, current_user.id)


@router.delete("/{secret_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(
    secret_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_key(secret_key)

    stmt = select(UserSecret).where(
        UserSecret.owner_id == current_user.id,
        UserSecret.secret_key == secret_key,
    )
    secret = (await db.execute(stmt)).scalar_one_or_none()
    if secret:
        await db.delete(secret)
        await db.commit()
        logger.info("Deleted secret key=%s for user=%s", secret_key, current_user.id)
