"""Authentication and user management service."""
from datetime import datetime, timezone
from typing import Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_token,
)
from app.core.exceptions import AuthenticationError, ConflictError
from app.models.user import User, RefreshToken
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.auth import TokenResponse, UserRegisterRequest, UserLoginRequest


class AuthService:
    @staticmethod
    async def register(
        db: AsyncSession,
        req: UserRegisterRequest
    ) -> Tuple[User, Workspace, TokenResponse]:
        """Register a new user, create a default workspace, and issue tokens."""
        # Check duplicate email
        query = select(User).where(User.email == req.email)
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise ConflictError(f"User with email '{req.email}' already exists")

        # Create user
        user = User(
            email=req.email,
            password_hash=hash_password(req.password),
            full_name=req.full_name,
            is_active=True
        )
        db.add(user)
        await db.flush()

        # Create default workspace
        workspace_name = f"{req.full_name or 'Personal'}'s Workspace"
        workspace = Workspace(
            name=workspace_name,
            owner_id=user.id
        )
        db.add(workspace)
        await db.flush()

        # Assign user as workspace owner
        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner"
        )
        db.add(membership)

        # Issue tokens
        access_token = create_access_token(
            subject=str(user.id),
            workspace_id=str(workspace.id)
        )
        raw_refresh, token_hash, expires_at = create_refresh_token()

        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked=False
        )
        db.add(refresh_record)

        await db.commit()
        await db.refresh(user)
        await db.refresh(workspace)

        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return user, workspace, token_response

    @staticmethod
    async def login(
        db: AsyncSession,
        req: UserLoginRequest
    ) -> Tuple[User, TokenResponse]:
        """Authenticate user credentials and issue new tokens."""
        query = select(User).where(User.email == req.email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not verify_password(req.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is inactive")

        # Fetch primary or first owned workspace if available
        ws_query = select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
        ws_res = await db.execute(ws_query)
        first_membership = ws_res.scalars().first()
        ws_id_str = str(first_membership.workspace_id) if first_membership else None

        access_token = create_access_token(
            subject=str(user.id),
            workspace_id=ws_id_str
        )
        raw_refresh, token_hash, expires_at = create_refresh_token()

        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked=False
        )
        db.add(refresh_record)
        await db.commit()

        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return user, token_response

    @staticmethod
    async def refresh_tokens(
        db: AsyncSession,
        raw_refresh_token: str
    ) -> TokenResponse:
        """Rotate refresh token: revoke current token and issue a fresh pair."""
        token_hash = hash_token(raw_refresh_token)
        now = datetime.now(timezone.utc)

        query = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False
        )
        result = await db.execute(query)
        record = result.scalar_one_or_none()

        if not record:
            raise AuthenticationError("Invalid or expired refresh token")

        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            record.revoked = True
            await db.commit()
            raise AuthenticationError("Invalid or expired refresh token")

        # Fetch user
        user_query = select(User).where(User.id == record.user_id)
        user_res = await db.execute(user_query)
        user = user_res.scalar_one_or_none()

        if not user or not user.is_active:
            raise AuthenticationError("User is inactive or no longer exists")

        # 1. Revoke the used refresh token (Rotation)
        record.revoked = True

        # 2. Issue new tokens
        ws_query = select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
        ws_res = await db.execute(ws_query)
        first_membership = ws_res.scalars().first()
        ws_id_str = str(first_membership.workspace_id) if first_membership else None

        new_access_token = create_access_token(
            subject=str(user.id),
            workspace_id=ws_id_str
        )
        new_raw_refresh, new_token_hash, new_expires_at = create_refresh_token()

        new_record = RefreshToken(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
            revoked=False
        )
        db.add(new_record)
        await db.commit()

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_raw_refresh,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    @staticmethod
    async def logout(
        db: AsyncSession,
        raw_refresh_token: str
    ) -> None:
        """Revoke a refresh token on logout."""
        token_hash = hash_token(raw_refresh_token)
        stmt = update(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        ).values(revoked=True)
        await db.execute(stmt)
        await db.commit()
