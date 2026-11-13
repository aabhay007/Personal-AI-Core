"""Tool for exploring repository directory structure and architecture."""
import uuid
import logging
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.tools.base import BaseTool
from app.models.code_repository import RepositoryFile, CodeRepository
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


class RepoFileTreeInput(BaseModel):
    repository_id: Optional[str] = Field(
        None,
        description="Optional repository ID. If omitted, uses active repositories in workspace."
    )
    subpath: Optional[str] = Field(
        None,
        description="Optional folder subpath to filter tree by (e.g. 'backend/app')."
    )
    workspace_id: Optional[str] = Field(
        None,
        description="Contextual workspace ID."
    )


class RepoFileTreeTool(BaseTool):
    name = "repo_file_tree"
    description = (
        "Inspect the file tree structure of an indexed repository to understand project layout and architecture."
    )
    args_schema = RepoFileTreeInput
    timeout_seconds = 10.0

    async def execute(
        self,
        repository_id: Optional[str] = None,
        subpath: Optional[str] = None,
        workspace_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        if not workspace_id:
            return {"error": "Workspace context is required to inspect repository tree."}

        try:
            ws_uuid = uuid.UUID(workspace_id)
        except ValueError:
            return {"error": "Invalid workspace UUID."}

        async def _run(session):
            stmt = select(RepositoryFile).where(RepositoryFile.workspace_id == ws_uuid)
            if repository_id:
                try:
                    stmt = stmt.where(RepositoryFile.repository_id == uuid.UUID(repository_id))
                except ValueError:
                    return {"error": f"Invalid repository ID '{repository_id}'"}

            result = await session.execute(stmt)
            files = result.scalars().all()

            file_paths = [f.file_path for f in files]
            if subpath:
                norm_sub = subpath.strip("/").replace("\\", "/")
                file_paths = [p for p in file_paths if p.startswith(norm_sub)]

            file_paths.sort()

            return {
                "total_files": len(file_paths),
                "subpath_filter": subpath,
                "files": file_paths[:200]  # Cap at 200 paths
            }

        if db is not None:
            return await _run(db)
        else:
            async with AsyncSessionLocal() as session:
                return await _run(session)
