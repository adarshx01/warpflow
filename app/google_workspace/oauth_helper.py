"""
Shared OAuth helper for all Google Workspace services.
Handles token exchange, refresh, and building the google-auth credentials object.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

# Scopes per service type
SERVICE_SCOPES: dict[str, list[str]] = {
    "gmail": [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
    ],
    "google-docs": [
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive.file",
    ],
    "google-drive": [
        "https://www.googleapis.com/auth/drive",
    ],
    "google-forms": [
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/forms.responses.readonly",
    ],
    "google-sheets": [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ],
}

# Callback URIs per service type (must match what's registered in Google Cloud Console)
SERVICE_CALLBACKS: dict[str, str] = {
    "gmail":          "http://localhost:8000/api/gmail/oauth/callback",
    "google-docs":    "http://localhost:8000/api/google-docs/oauth/callback",
    "google-drive":   "http://localhost:8000/api/google-drive/oauth/callback",
    "google-forms":   "http://localhost:8000/api/google-forms/oauth/callback",
    "google-sheets":  "http://localhost:8000/api/google-sheets/oauth/callback",
}


def build_auth_url(service: str, client_id: str, credential_id: str) -> str:
    """Construct the Google OAuth consent URL for a given service."""
    scopes = " ".join(SERVICE_SCOPES[service])
    redirect_uri = SERVICE_CALLBACKS[service]
    params = (
        f"client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scopes.replace(' ', '%20')}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={credential_id}"
    )
    return f"{GOOGLE_AUTH_URL}?{params}"


async def exchange_code_for_tokens(
    service: str, client_id: str, client_secret: str, code: str
) -> dict:
    """Exchange an authorization code for access + refresh tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": SERVICE_CALLBACKS[service],
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """Use the refresh token to obtain a new access token."""
    async with httpx.AsyncClient() as client:
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
        return resp.json()


def token_expiry_from_response(token_data: dict) -> Optional[datetime]:
    expires_in = token_data.get("expires_in")
    if expires_in is None:
        return None
    return datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
