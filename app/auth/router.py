import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.rate_limit import limiter
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    GoogleCallbackRequest,
    AuthResponse,
    UserResponse,
)
from app.auth.utils import (
    hash_password,
    verify_password,
    create_access_token,
    set_auth_cookies,
    clear_auth_cookies,
    get_current_user,
)
from app.auth.oauth import (
    get_google_auth_url,
    exchange_google_code,
    generate_oauth_state,
    verify_oauth_state,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ──────────────────────────────────────────────
# Email + Password Auth
# ──────────────────────────────────────────────


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(request: Request, response: Response, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == body.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=body.email,
        name=body.name,
        hashed_password=hash_password(body.password),
        auth_provider="email",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    set_auth_cookies(response, token)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(request: Request, response: Response, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": str(user.id)})
    set_auth_cookies(response, token)
    return AuthResponse(user=UserResponse.model_validate(user))


# ──────────────────────────────────────────────
# Google OAuth
# ──────────────────────────────────────────────


@router.get("/google")
@limiter.limit("10/minute")
async def google_login(request: Request):
    """Return the Google OAuth authorization URL with CSRF state."""
    state = generate_oauth_state()
    return {"url": get_google_auth_url(state), "state": state}


@router.post("/google/callback", response_model=AuthResponse)
@limiter.limit("10/minute")
async def google_callback(request: Request, response: Response, body: GoogleCallbackRequest, db: AsyncSession = Depends(get_db)):
    """Exchange Google auth code for user session."""
    # Verify OAuth state to prevent CSRF
    if not verify_oauth_state(body.state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please try again.",
        )

    try:
        google_user = await exchange_google_code(body.code)
    except Exception:
        logger.exception("Google OAuth code exchange failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google authentication failed. Please try again.",
        )

    google_id = google_user.get("id")
    email = google_user.get("email")
    name = google_user.get("name", email.split("@")[0] if email else "User")
    avatar_url = google_user.get("picture")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account does not have an email address",
        )

    # First, look up by google_id (returning user with Google)
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user:
        # Existing Google user — update avatar
        if avatar_url:
            user.avatar_url = avatar_url
        await db.commit()
        await db.refresh(user)
    else:
        # Check if an account with this email already exists
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            # Don't auto-link Google to an existing password account
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists. Please log in with your password.",
            )

        # Create new user
        user = User(
            email=email,
            name=name,
            google_id=google_id,
            avatar_url=avatar_url,
            auth_provider="google",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    set_auth_cookies(response, token)
    return AuthResponse(user=UserResponse.model_validate(user))

@router.post("/logout")
async def logout(response: Response):
    """Clear auth cookies."""
    clear_auth_cookies(response)
    return {"detail": "Logged out"}




@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
