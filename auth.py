import os
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from dotenv import load_dotenv

from database import get_connection

load_dotenv()

BETTER_AUTH_SECRET = os.getenv("BETTER_AUTH_SECRET", "")


def verify_session_token(token: str) -> bool:
    """
    Verify the HMAC signature of a better-auth session token.
    Token format: <session_token>.<hmac_signature>
    """
    parts = token.split(".")
    if len(parts) != 2:
        return False

    session_token, signature = parts

    expected_signature = hmac.new(
        BETTER_AUTH_SECRET.encode("utf-8"),
        session_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


def get_session_from_db(session_token: str) -> Optional[dict]:
    """
    Look up a session in the database by token.
    Returns session dict if valid and not expired, else None.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.*, u.id as user_id, u.name, u.email, u.image
                FROM "session" s
                JOIN "user" u ON s."userId" = u.id
                WHERE s.token = %s
                """,
                (session_token,),
            )
            row = cur.fetchone()

            if not row:
                return None

            # Check if session is expired
            expires_at = row.get("expiresAt")
            if expires_at:
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < datetime.now(timezone.utc):
                    return None

            return dict(row)
    finally:
        conn.close()


async def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency: extract and verify the better-auth session cookie.
    Returns the user dict if valid, raises 401 otherwise.
    """
    # Try cookie first, then Authorization header
    token = request.cookies.get("better-auth.session_token")

    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Extract the raw session token (before the HMAC dot)
    raw_token = token.split(".")[0]

    # Look up session in DB
    session = get_session_from_db(raw_token)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    return {
        "id": session["user_id"],
        "name": session["name"],
        "email": session["email"],
        "image": session.get("image"),
    }
