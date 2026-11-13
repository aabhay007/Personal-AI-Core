"""API v1 router configuration."""
from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.workspaces import router as workspaces_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.chat import router as chat_router
from app.api.v1.tools import router as tools_router
from app.api.v1.documents import router as documents_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.repositories import router as repositories_router
from app.api.v1.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(auth_router, tags=["Authentication"])
api_router.include_router(workspaces_router, tags=["Workspaces"])
api_router.include_router(conversations_router, tags=["Conversations"])
api_router.include_router(chat_router, tags=["Chat"])
api_router.include_router(tools_router, tags=["Tools"])
api_router.include_router(documents_router, tags=["Documents"])
api_router.include_router(integrations_router, tags=["Integrations"])
api_router.include_router(repositories_router, tags=["Repositories"])
api_router.include_router(tasks_router, tags=["Tasks"])
