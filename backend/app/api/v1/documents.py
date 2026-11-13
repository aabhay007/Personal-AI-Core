"""Document ingestion, status, and management API endpoints."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, Form, UploadFile, File, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.api.deps import get_current_user, verify_workspace_access
from app.models.user import User
from app.knowledge.service import DocumentService
from app.schemas.document import DocumentResponse, DocumentStatusResponse

router = APIRouter(prefix="/documents")


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest document",
    description="Upload a document (PDF, TXT, MD, DOCX) to be chunked, embedded, and indexed for semantic search."
)
async def upload_document(
    workspace_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> DocumentResponse:
    """Upload and ingest a document into the workspace knowledge engine."""
    # 1. Enforce workspace authorization
    await verify_workspace_access(workspace_id, current_user, db)

    # 2. Read file data
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # 3. Process, chunk, embed, and index
    doc = await DocumentService.process_and_ingest_document(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        filename=file.filename or "uploaded_document",
        file_bytes=content,
        mime_type=file.content_type or "application/octet-stream"
    )
    return doc


@router.get(
    "",
    response_model=List[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List workspace documents"
)
async def list_documents(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> List[DocumentResponse]:
    """List all documents indexed in the given workspace."""
    await verify_workspace_access(workspace_id, current_user, db)
    return await DocumentService.list_documents(db, workspace_id)


@router.get(
    "/{id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document details"
)
async def get_document(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> DocumentResponse:
    """Fetch document details after verifying workspace ownership."""
    doc = await DocumentService.get_document(db, id)
    await verify_workspace_access(doc.workspace_id, current_user, db)
    return doc


@router.get(
    "/{id}/status",
    response_model=DocumentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document processing status"
)
async def get_document_status(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> DocumentStatusResponse:
    """Check processing status of a document."""
    doc = await DocumentService.get_document(db, id)
    await verify_workspace_access(doc.workspace_id, current_user, db)
    return DocumentStatusResponse(
        id=doc.id,
        filename=doc.filename,
        processing_status=doc.processing_status,
        error_message=doc.error_message
    )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document and indexed chunks"
)
async def delete_document(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> None:
    """Delete document and its associated vector chunks."""
    doc = await DocumentService.get_document(db, id)
    await verify_workspace_access(doc.workspace_id, current_user, db, required_role="member")
    await DocumentService.delete_document(db, id)
