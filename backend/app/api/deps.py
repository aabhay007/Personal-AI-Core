"""API dependency injection utilities."""
import uuid
from typing import Optional
from fastapi import Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.core.security import decode_token
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.models.user import User
from app.models.workspace import WorkspaceMember

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """Validate access token and return the authenticated user."""
    if not auth or not auth.credentials:
        raise AuthenticationError("Authentication required")

    payload = decode_token(auth.credentials)
    if not payload or payload.get("type") != "access":
        raise AuthenticationError("Invalid or expired token")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Malformed token payload")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationError("Invalid user identifier in token")

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    return user


async def verify_workspace_access(
    workspace_id: uuid.UUID,
    user: User,
    db: AsyncSession,
    required_role: Optional[str] = None
) -> WorkspaceMember:
    """Verify that user belongs to the specified workspace and has necessary permissions."""
    query = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user.id
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()

    if not member:
        raise AuthorizationError("You do not have access to this workspace")

    if required_role:
        role_hierarchy = {"owner": 3, "admin": 2, "member": 1}
        user_level = role_hierarchy.get(member.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        if user_level < required_level:
            raise AuthorizationError(f"Operation requires '{required_role}' privileges")

    return member
