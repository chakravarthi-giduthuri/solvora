import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import create_access_token, get_current_user, revoke_token
from app.models.problem import User
from app.schemas.auth import GoogleOAuthCallback, Token, UserCreate, UserLogin, UserResponse
from app.services.auth_service import authenticate_user, create_user, exchange_google_code, get_or_create_google_user

router = APIRouter()
security_logger = structlog.get_logger("security")
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
async def signup(request: Request, user_create: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await create_user(db, user_create)
    security_logger.info("signup_success", user_id=user.id, ip=request.client.host if request.client else "unknown")
    token = create_access_token({"sub": user.id})
    return Token(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, credentials.email, credentials.password)
    if not user:
        security_logger.warning(
            "login_failed",
            email=credentials.email,
            ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    security_logger.info(
        "login_success",
        user_id=user.id,
        ip=request.client.host if request.client else "unknown",
    )
    token = create_access_token({"sub": user.id})
    return Token(access_token=token, user=UserResponse.model_validate(user))


@router.post("/oauth/google", response_model=Token)
async def google_oauth(body: GoogleOAuthCallback, db: AsyncSession = Depends(get_db)):
    google_user = await exchange_google_code(body.code, body.redirect_uri)
    user = await get_or_create_google_user(db, google_user)
    token = create_access_token({"sub": user.id})
    return Token(access_token=token, user=UserResponse.model_validate(user))


@router.post("/logout")
async def logout(
    request: Request,
    raw_credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
):
    if raw_credentials:
        await revoke_token(raw_credentials.credentials)
    security_logger.info("logout", user_id=current_user.id)
    return {"status": "logged_out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


from pydantic import BaseModel as _BaseModel


class GoogleIdTokenBody(_BaseModel):
    id_token: str


@router.post("/google-id-token", response_model=Token)
async def google_id_token_login(body: GoogleIdTokenBody, db: AsyncSession = Depends(get_db)):
    """Verify a Google id_token and return a backend JWT. Used by NextAuth server-side callback."""
    import httpx
    async with httpx.AsyncClient() as hclient:
        r = await hclient.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": body.id_token},
            timeout=10,
        )
    if r.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")

    info = r.json()
    email = info.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No email in Google token")

    name = info.get("name") or email.split("@")[0]
    avatar = info.get("picture")

    google_user_data = {"email": email, "name": name, "avatar_url": avatar}
    user = await get_or_create_google_user(db, google_user_data)
    token = create_access_token({"sub": user.id})
    return Token(access_token=token, user=UserResponse.model_validate(user))
