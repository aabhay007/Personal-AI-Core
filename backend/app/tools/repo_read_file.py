"""Tool for reading specific lines of a file from an indexed repository."""
import uuid
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.tools.base import BaseTool
from app.models.code_repository import RepositoryFile, CodeRepository
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


class RepoReadFileInput(BaseModel):
    file_path: str = Field(
        ...,
        description="Path of the file to inspect (e.g. 'backend/app/main.py' or 'frontend/src/app/page.tsx')."
    )
    repository_id: Optional[str] = Field(
        None,
        description="Optional ID of the repository. If omitted, checks active repositories in the workspace."
    )
    start_line: int = Field(
        default=1,
        ge=1,
        description="First line to read (1-indexed)."
    )
    end_line: int = Field(
        default=100,
        ge=1,
        description="Last line to read (max 200 lines per call)."
    )
    workspace_id: Optional[str] = Field(
        None,
        description="Contextual workspace ID."
    )


class RepoReadFileTool(BaseTool):
    name = "repo_read_file"
    description = (
        "Read source code from an indexed file within the authorized workspace. "
        "Returns line-numbered code snippets. Always include file path and line numbers when explaining code."
    )
    args_schema = RepoReadFileInput
    timeout_seconds = 10.0

    async def execute(
        self,
        file_path: str,
        repository_id: Optional[str] = None,
        start_line: int = 1,
        end_line: int = 100,
        workspace_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        if not workspace_id:
            return {"error": "Workspace context is required to read repository files."}

        try:
            ws_uuid = uuid.UUID(workspace_id)
        except ValueError:
            return {"error": "Invalid workspace UUID."}

        # Clamp line window
        max_window = 200
        safe_start = max(1, start_line)
        safe_end = min(safe_start + max_window - 1, max(safe_start, end_line))

        async def _run(session):
            stmt = select(RepositoryFile).where(
                RepositoryFile.workspace_id == ws_uuid,
                RepositoryFile.file_path == file_path
            )
            if repository_id:
                try:
                    stmt = stmt.where(RepositoryFile.repository_id == uuid.UUID(repository_id))
                except ValueError:
                    return {"error": f"Invalid repository ID '{repository_id}'"}

            result = await session.execute(stmt)
            file_record = result.scalars().first()

            if not file_record or not file_record.content:
                return {
                    "error": f"File '{file_path}' not found in indexed repositories for this workspace."
                }

            lines = file_record.content.splitlines()
            total_lines = len(lines)
            selected_lines = lines[safe_start - 1:safe_end]

            numbered_lines = [
                f"{safe_start + idx:4d} | {line}"
                for idx, line in enumerate(selected_lines)
            ]

            return {
                "file_path": file_record.file_path,
                "total_lines": total_lines,
                "start_line": safe_start,
                "end_line": min(safe_end, total_lines),
                "content": "\n".join(numbered_lines)
            }

        if db is not None:
            return await _run(db)
        else:
            async with AsyncSessionLocal() as session:
                return await _run(session)
