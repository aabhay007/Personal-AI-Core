"""Tool for semantic code and documentation search across repositories."""
import uuid
import logging
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from app.tools.base import BaseTool
from app.knowledge.code_indexer import CodeSearchEngine
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


class RepoCodeSearchInput(BaseModel):
    query: str = Field(
        ...,
        description="The semantic search query for functions, classes, APIs, or architectural logic."
    )
    repository_id: Optional[str] = Field(
        None,
        description="Optional repository ID filter."
    )
    file_extension: Optional[str] = Field(
        None,
        description="Optional file extension filter (e.g. '.py', '.tsx', '.sql')."
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of code chunks to return."
    )
    workspace_id: Optional[str] = Field(
        None,
        description="Contextual workspace ID."
    )


class RepoCodeSearchTool(BaseTool):
    name = "repo_code_search"
    description = (
        "Search indexed repository source code and documentation using semantic search. "
        "Returns code snippets with precise file paths and line ranges for citations."
    )
    args_schema = RepoCodeSearchInput
    timeout_seconds = 10.0

    async def execute(
        self,
        query: str,
        repository_id: Optional[str] = None,
        file_extension: Optional[str] = None,
        limit: int = 5,
        workspace_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        if not workspace_id:
            return {"error": "Workspace context is required for repository code search."}

        try:
            ws_uuid = uuid.UUID(workspace_id)
            repo_uuid = uuid.UUID(repository_id) if repository_id else None
        except ValueError:
            return {"error": "Invalid workspace or repository UUID."}

        async def _run(session):
            matches = await CodeSearchEngine.search(
                db=session,
                workspace_id=ws_uuid,
                query=query,
                repository_id=repo_uuid,
                file_extension=file_extension,
                top_k=limit
            )
            return {
                "query": query,
                "match_count": len(matches),
                "results": matches
            }

        if db is not None:
            return await _run(db)
        else:
            async with AsyncSessionLocal() as session:
                return await _run(session)
