import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.problem import User
from app.schemas.auth import UserCreate, _ALLOWED_REDIRECT_URIS
from app.core.security import get_password_hash, verify_password

# Constant-time dummy hash used to prevent email enumeration via timing
_DUMMY_HASH = "$2b$12$KIXtAhC3TW9YGtdQCbQ/JeWfWwJRpQrJB1OXTrElnY5q6jnNMqiCu"

_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
    existing = await get_user_by_email(db, user_create.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=user_create.email,
        name=user_create.name,
        hashed_password=get_password_hash(user_create.password),
        auth_provider="email",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    # Always run bcrypt to prevent email enumeration via timing side-channel
    hash_to_check = user.hashed_password if (user and user.hashed_password) else _DUMMY_HASH
    is_valid = verify_password(password, hash_to_check)
    if not user or not user.hashed_password or not is_valid:
        return None
    return user


async def exchange_google_code(code: str, redirect_uri: str) -> dict:
    # redirect_uri is already validated by the Pydantic schema, but double-check
    if redirect_uri not in _ALLOWED_REDIRECT_URIS:
        raise HTTPException(status_code=400, detail="Invalid redirect URI")

    from app.core.config import settings
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        token_resp = await client.post(_GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise HTTPException(status_code=502, detail="Invalid token response from Google")

        user_resp = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_resp.raise_for_status()
        return user_resp.json()


async def get_or_create_google_user(db: AsyncSession, google_user: dict) -> User:
    email = google_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Could not get email from Google")
    user = await get_user_by_email(db, email)
    if not user:
        user = User(
            email=email,
            name=google_user.get("name", email.split("@")[0]),
            auth_provider="google",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user
