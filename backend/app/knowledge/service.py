"""Document ingestion and lifecycle management service."""
import uuid
import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document, DocumentChunk
from app.knowledge.storage import get_storage_service
from app.knowledge.ingestion import DocumentExtractor
from app.knowledge.chunking import TextChunker
from app.knowledge.embeddings import embedding_service
from app.core.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class DocumentService:
    @staticmethod
    async def process_and_ingest_document(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        filename: str,
        file_bytes: bytes,
        mime_type: str = "application/octet-stream"
    ) -> Document:
        """Process document upload: store binary, extract text, chunk, embed, and index."""
        storage = get_storage_service()
        doc_id = uuid.uuid4()
        storage_key = f"{workspace_id}/{doc_id}_{filename}"

        # 1. Save file to storage
        await storage.save_file(storage_key, file_bytes)

        # 2. Create initial Document record in DB
        doc = Document(
            id=doc_id,
            workspace_id=workspace_id,
            uploaded_by=user_id,
            filename=filename,
            mime_type=mime_type,
            storage_key=storage_key,
            file_size=len(file_bytes),
            processing_status="processing"
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        try:
            # 3. Extract text sections with page numbers
            sections = DocumentExtractor.extract_text(filename, file_bytes)
            if not sections:
                raise ValueError("No extractable text found in document.")

            # 4. Chunk document
            chunker = TextChunker(chunk_size=500, chunk_overlap=100)
            chunks_data = chunker.chunk_document_sections(sections, filename)

            if not chunks_data:
                raise ValueError("Document yielded 0 text chunks.")

            # 5. Generate vector embeddings
            chunk_texts = [c["content"] for c in chunks_data]
            embeddings = embedding_service.embed_documents(chunk_texts)

            # 6. Save chunks into database
            for idx, c in enumerate(chunks_data):
                chunk_record = DocumentChunk(
                    document_id=doc.id,
                    workspace_id=workspace_id,
                    chunk_index=c["chunk_index"],
                    content=c["content"],
                    embedding=embeddings[idx],
                    chunk_metadata=c["metadata"]
                )
                db.add(chunk_record)

            doc.processing_status = "completed"
            await db.commit()
            await db.refresh(doc)
            logger.info(f"Successfully processed document '{filename}' with {len(chunks_data)} chunks.")
            return doc

        except Exception as e:
            logger.exception(f"Failed to process document '{filename}': {e}")
            doc.processing_status = "failed"
            doc.error_message = str(e)
            await db.commit()
            await db.refresh(doc)
            return doc

    @staticmethod
    async def list_documents(
        db: AsyncSession,
        workspace_id: uuid.UUID
    ) -> List[Document]:
        """List all documents belonging to a workspace."""
        query = select(Document).where(
            Document.workspace_id == workspace_id
        ).order_by(Document.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_document(
        db: AsyncSession,
        document_id: uuid.UUID
    ) -> Document:
        """Fetch document by ID."""
        query = select(Document).where(Document.id == document_id)
        result = await db.execute(query)
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError("Document not found")
        return doc

    @staticmethod
    async def delete_document(
        db: AsyncSession,
        document_id: uuid.UUID
    ) -> None:
        """Delete document from database (cascades chunks) and removes storage file."""
        doc = await DocumentService.get_document(db, document_id)
        storage = get_storage_service()
        await storage.delete_file(doc.storage_key)
        await db.delete(doc)
        await db.commit()
