"""Code chunking, indexing, and semantic search engine for repositories."""
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.code_repository import CodeRepository, RepositoryFile, RepositoryChunk
from app.knowledge.embeddings import embedding_service
from app.knowledge.retrieval import cosine_similarity

logger = logging.getLogger(__name__)

# Valid extensions for code indexing
SUPPORTED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".sql", ".yaml", ".yml",
    ".sh", ".dockerfile", ".toml", ".rs", ".go", ".java", ".c", ".cpp", ".h", ".html", ".css"
}

IGNORED_DIRECTORIES = {
    ".git", "node_modules", ".next", "dist", "build", "__pycache__", ".venv", "venv", ".turbo"
}


def is_indexable_path(path: str) -> bool:
    """Determine whether a file path should be indexed based on directory and extension rules."""
    norm_path = path.replace("\\", "/")
    parts = norm_path.split("/")
    for p in parts:
        if p in IGNORED_DIRECTORIES:
            return False

    base_name = parts[-1].lower()
    if base_name in ("dockerfile", "makefile", ".env.example"):
        return True

    _, ext = os.path.splitext(base_name)
    return ext in SUPPORTED_EXTENSIONS


def chunk_code_file(
    file_path: str,
    content: str,
    chunk_lines: int = 50,
    overlap_lines: int = 10
) -> List[Dict[str, Any]]:
    """Split code file content into line-bounded chunks with start_line and end_line metadata."""
    lines = content.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return []

    chunks = []
    chunk_idx = 0
    step = max(1, chunk_lines - overlap_lines)

    for start_idx in range(0, total_lines, step):
        end_idx = min(start_idx + chunk_lines, total_lines)
        chunk_text = "\n".join(lines[start_idx:end_idx])
        if chunk_text.strip():
            chunks.append({
                "chunk_index": chunk_idx,
                "start_line": start_idx + 1,  # 1-indexed
                "end_line": end_idx,
                "content": f"# File: {file_path} (Lines {start_idx + 1}-{end_idx})\n{chunk_text}"
            })
            chunk_idx += 1

        if end_idx >= total_lines:
            break

    return chunks


class CodeIndexer:
    """Service for indexing repository files and computing vector representations."""

    @staticmethod
    async def index_repository_files(
        db: AsyncSession,
        repository: CodeRepository,
        files: List[Dict[str, Any]]
    ) -> int:
        """Process, chunk, and embed a batch of files for a code repository."""
        # 1. Clear existing indexed data for this repository
        await db.execute(delete(RepositoryChunk).where(RepositoryChunk.repository_id == repository.id))
        await db.execute(delete(RepositoryFile).where(RepositoryFile.repository_id == repository.id))

        total_files = 0
        all_chunks_to_insert = []
        chunk_texts_to_embed = []

        for f in files:
            path = f["path"]
            content = f.get("content", "")
            if not content or not is_indexable_path(path):
                continue

            lines = content.splitlines()
            line_count = len(lines)
            size_bytes = len(content.encode("utf-8"))
            _, ext = os.path.splitext(path)

            file_record = RepositoryFile(
                repository_id=repository.id,
                workspace_id=repository.workspace_id,
                file_path=path,
                file_name=os.path.basename(path),
                extension=ext.lower() or "txt",
                size_bytes=size_bytes,
                line_count=line_count,
                content=content[:50000]  # Store up to 50KB inline for quick retrieval
            )
            db.add(file_record)
            total_files += 1

            # Chunk file
            file_chunks = chunk_code_file(path, content)
            for c in file_chunks:
                all_chunks_to_insert.append((path, c))
                chunk_texts_to_embed.append(c["content"])

        # 2. Batch generate local vector embeddings
        if chunk_texts_to_embed:
            embeddings = embedding_service.embed_documents(chunk_texts_to_embed)

            for (path, c), emb in zip(all_chunks_to_insert, embeddings):
                chunk_record = RepositoryChunk(
                    repository_id=repository.id,
                    workspace_id=repository.workspace_id,
                    file_path=path,
                    chunk_index=c["chunk_index"],
                    start_line=c["start_line"],
                    end_line=c["end_line"],
                    content=c["content"],
                    embedding=emb
                )
                db.add(chunk_record)

        # 3. Update repository stats
        repository.is_indexed = True
        repository.file_count = total_files
        repository.last_indexed_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info(f"Indexed {total_files} files and {len(all_chunks_to_insert)} code chunks for repo '{repository.name}'")
        return total_files


class CodeSearchEngine:
    """Semantic and keyword search over indexed repository code."""

    @staticmethod
    async def search(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        query: str,
        repository_id: Optional[uuid.UUID] = None,
        file_extension: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.25
    ) -> List[Dict[str, Any]]:
        """Search code chunks strictly scoped by workspace_id and optional repository_id."""
        query_vec = embedding_service.embed_query(query)

        stmt = select(RepositoryChunk).where(RepositoryChunk.workspace_id == workspace_id)
        if repository_id:
            stmt = stmt.where(RepositoryChunk.repository_id == repository_id)

        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return []

        scored = []
        for c in chunks:
            if file_extension and not c.file_path.endswith(file_extension):
                continue

            score = cosine_similarity(query_vec, c.embedding)
            if score >= min_score:
                scored.append({
                    "repository_id": str(c.repository_id),
                    "file_path": c.file_path,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "content": c.content,
                    "similarity_score": round(score, 4)
                })

        scored.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored[:top_k]
