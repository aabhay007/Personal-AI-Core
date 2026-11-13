"""Semantic search and vector retrieval engine with strict workspace isolation."""
import math
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import DocumentChunk
from app.knowledge.embeddings import embedding_service


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two numerical vectors."""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


class SemanticRetriever:
    @staticmethod
    async def search(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        query: str,
        top_k: int = 4,
        min_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Retrieve most relevant document chunks strictly bounded within workspace_id."""
        # 1. Embed query
        query_vector = embedding_service.embed_query(query)

        # 2. Fetch chunks scoped strictly by workspace_id
        stmt = select(DocumentChunk).where(DocumentChunk.workspace_id == workspace_id)
        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return []

        # 3. Score chunks
        scored_chunks = []
        for chunk in chunks:
            score = cosine_similarity(query_vector, chunk.embedding)
            if score >= min_score:
                scored_chunks.append({
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "content": chunk.content,
                    "score": round(score, 4),
                    "filename": chunk.chunk_metadata.get("filename", "Unknown Document") if chunk.chunk_metadata else "Unknown Document",
                    "page_number": chunk.chunk_metadata.get("page_number", 1) if chunk.chunk_metadata else 1,
                })

        # 4. Sort descending by relevance score
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]
