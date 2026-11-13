"""Code Repositories and Developer Assistant API endpoints."""
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db_session
from app.api.deps import get_current_user, verify_workspace_access
from app.models.user import User
from app.models.code_repository import CodeRepository, RepositoryFile
from app.integrations.encryption import encrypt_secret, decrypt_secret
from app.integrations.github.client import GitHubClient
from app.knowledge.code_indexer import CodeIndexer, CodeSearchEngine
from app.schemas.repository import (
    CodeRepositoryCreate,
    CodeRepositoryResponse,
    RepositoryFileResponse,
    CodeSearchRequest,
    CodeSearchResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories")


def _to_repo_response(repo: CodeRepository) -> CodeRepositoryResponse:
    return CodeRepositoryResponse(
        id=repo.id,
        workspace_id=repo.workspace_id,
        name=repo.name,
        owner=repo.owner,
        repo_name=repo.repo_name,
        default_branch=repo.default_branch,
        has_token=bool(repo.encrypted_token),
        is_indexed=repo.is_indexed,
        file_count=repo.file_count,
        last_indexed_at=repo.last_indexed_at,
        created_at=repo.created_at,
        updated_at=repo.updated_at
    )


@router.post(
    "",
    response_model=CodeRepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect a code repository"
)
async def create_repository(
    payload: CodeRepositoryCreate,
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> CodeRepositoryResponse:
    """Connect a new GitHub or Git repository to the workspace."""
    await verify_workspace_access(workspace_id, current_user, db)

    enc_token = encrypt_secret(payload.token) if payload.token else None

    repo = CodeRepository(
        workspace_id=workspace_id,
        created_by=current_user.id,
        name=payload.name,
        owner=payload.owner,
        repo_name=payload.repo_name,
        default_branch=payload.default_branch,
        encrypted_token=enc_token,
        is_indexed=False,
        file_count=0
    )

    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    return _to_repo_response(repo)


@router.get(
    "",
    response_model=List[CodeRepositoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List workspace repositories"
)
async def list_repositories(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> List[CodeRepositoryResponse]:
    """List all connected code repositories in the workspace."""
    await verify_workspace_access(workspace_id, current_user, db)

    stmt = select(CodeRepository).where(CodeRepository.workspace_id == workspace_id).order_by(CodeRepository.created_at.desc())
    result = await db.execute(stmt)
    repos = result.scalars().all()

    return [_to_repo_response(r) for r in repos]


@router.get(
    "/{repo_id}",
    response_model=CodeRepositoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get repository details"
)
async def get_repository(
    repo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> CodeRepositoryResponse:
    """Retrieve repository metadata."""
    stmt = select(CodeRepository).where(CodeRepository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalars().first()

    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")

    await verify_workspace_access(repo.workspace_id, current_user, db)
    return _to_repo_response(repo)


@router.delete(
    "/{repo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect repository"
)
async def delete_repository(
    repo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Disconnect and delete an indexed code repository and its chunks."""
    stmt = select(CodeRepository).where(CodeRepository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalars().first()

    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")

    await verify_workspace_access(repo.workspace_id, current_user, db)
    await db.delete(repo)
    await db.commit()


@router.post(
    "/{repo_id}/sync",
    status_code=status.HTTP_200_OK,
    summary="Sync and index repository files"
)
async def sync_repository(
    repo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Fetch files from GitHub and index them into local vector storage."""
    stmt = select(CodeRepository).where(CodeRepository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalars().first()

    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")

    await verify_workspace_access(repo.workspace_id, current_user, db)

    token = decrypt_secret(repo.encrypted_token)
    gh_client = GitHubClient(token=token)

    try:
        tree = await gh_client.get_tree(owner=repo.owner, repo=repo.repo_name, branch=repo.default_branch)
        blob_items = [item for item in tree if item.get("type") == "blob"][:100]  # Cap initial sync at 100 files

        files_to_index = []
        for item in blob_items:
            path = item.get("path")
            if not path:
                continue
            content = await gh_client.get_file_content(owner=repo.owner, repo=repo.repo_name, path=path, branch=repo.default_branch)
            if content:
                files_to_index.append({"path": path, "content": content})

        indexed_count = await CodeIndexer.index_repository_files(db=db, repository=repo, files=files_to_index)
        return {"status": "success", "indexed_files": indexed_count}
    except Exception as e:
        logger.error(f"Sync error for repo {repo.name}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to sync repository: {str(e)}")


@router.get(
    "/{repo_id}/tree",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
    summary="Get repository file paths"
)
async def get_repository_tree(
    repo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> List[str]:
    """Retrieve file paths belonging to this repository."""
    stmt = select(CodeRepository).where(CodeRepository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalars().first()

    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")

    await verify_workspace_access(repo.workspace_id, current_user, db)

    f_stmt = select(RepositoryFile.file_path).where(RepositoryFile.repository_id == repo_id).order_by(RepositoryFile.file_path)
    res = await db.execute(f_stmt)
    paths = res.scalars().all()
    return list(paths)


@router.get(
    "/{repo_id}/file",
    response_model=RepositoryFileResponse,
    status_code=status.HTTP_200_OK,
    summary="View repository file content"
)
async def get_repository_file(
    repo_id: uuid.UUID,
    path: str = Query(..., description="File path within the repository"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> RepositoryFileResponse:
    """Retrieve file content and line metadata."""
    stmt = select(CodeRepository).where(CodeRepository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalars().first()

    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")

    await verify_workspace_access(repo.workspace_id, current_user, db)

    f_stmt = select(RepositoryFile).where(
        RepositoryFile.repository_id == repo_id,
        RepositoryFile.file_path == path
    )
    res = await db.execute(f_stmt)
    file_record = res.scalars().first()

    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{path}' not found.")

    return file_record


@router.post(
    "/{repo_id}/search",
    response_model=CodeSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search code repository"
)
async def search_repository_code(
    repo_id: uuid.UUID,
    payload: CodeSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> CodeSearchResponse:
    """Perform semantic code search within this repository."""
    stmt = select(CodeRepository).where(CodeRepository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalars().first()

    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")

    await verify_workspace_access(repo.workspace_id, current_user, db)

    matches = await CodeSearchEngine.search(
        db=db,
        workspace_id=repo.workspace_id,
        query=payload.query,
        repository_id=repo_id,
        file_extension=payload.file_extension,
        top_k=payload.limit
    )

    return CodeSearchResponse(
        query=payload.query,
        match_count=len(matches),
        results=matches
    )
