import httpx
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def generate_oauth_state() -> str:
    """Generate a signed state token for OAuth CSRF protection."""
    return jwt.encode(
        {
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            "type": "oauth_state",
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def verify_oauth_state(state: str) -> bool:
    """Verify the signed OAuth state token."""
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("type") == "oauth_state"
    except JWTError:
        return False


def get_google_auth_url(state: str) -> str:
    """Generate the Google OAuth2 authorization URL with CSRF state."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_google_code(code: str) -> dict:
    """Exchange the authorization code for tokens and user info."""
    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            },
        )

        if token_response.status_code != 200:
            raise Exception(f"Failed to exchange code: {token_response.text}")

        tokens = token_response.json()
        access_token = tokens["access_token"]

        # Fetch user info
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_response.status_code != 200:
            raise Exception(f"Failed to fetch user info: {userinfo_response.text}")

        return userinfo_response.json()
