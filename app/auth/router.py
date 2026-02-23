from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    GoogleCallbackRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.utils import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.auth.oauth import get_google_auth_url, exchange_google_code

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ──────────────────────────────────────────────
# Email + Password Auth
# ──────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
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
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
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
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


# ──────────────────────────────────────────────
# Google OAuth
# ──────────────────────────────────────────────


@router.get("/google")
async def google_login():
    """Return the Google OAuth authorization URL."""
    return {"url": get_google_auth_url()}


@router.post("/google/callback", response_model=TokenResponse)
async def google_callback(body: GoogleCallbackRequest, db: AsyncSession = Depends(get_db)):
    """Exchange Google auth code for user session."""
    try:
        google_user = await exchange_google_code(body.code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}",
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

    # Check if user exists by google_id or email
    result = await db.execute(
        select(User).where((User.google_id == google_id) | (User.email == email))
    )
    user = result.scalar_one_or_none()

    if user:
        # Update google_id and avatar if not set
        if not user.google_id:
            user.google_id = google_id
        if avatar_url:
            user.avatar_url = avatar_url
        await db.commit()
        await db.refresh(user)
    else:
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
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


# ──────────────────────────────────────────────
# Current User
# ──────────────────────────────────────────────


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
