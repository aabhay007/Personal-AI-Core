"""Authentication API endpoints."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.api.deps import get_current_user
from app.services.auth_service import AuthService
from app.models.user import User
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth")


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user"
)
async def register(
    req: UserRegisterRequest,
    db: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    """Register a new user account, create a default workspace, and issue tokens."""
    _, _, token_response = await AuthService.register(db, req)
    return token_response


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login"
)
async def login(
    req: UserLoginRequest,
    db: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    """Authenticate email & password and return a fresh token pair."""
    _, token_response = await AuthService.login(db, req)
    return token_response


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token"
)
async def refresh_token(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    """Revoke submitted refresh token and issue a new access token & refresh token."""
    return await AuthService.refresh_tokens(db, req.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User logout"
)
async def logout(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session)
) -> None:
    """Revoke the refresh token on logout."""
    await AuthService.logout(db, req.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile"
)
async def get_me(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Return the profile information of the authenticated user."""
    return current_user
