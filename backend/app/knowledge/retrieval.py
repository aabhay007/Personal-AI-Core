"""Semantic search and vector retrieval engine with strict workspace isolation."""
import logging
import math
import re
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import DocumentChunk
from app.knowledge.embeddings import embedding_service

logger = logging.getLogger(__name__)


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two numerical vectors."""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def compute_keyword_score(query: str, content: str, filename: str = "") -> float:
    """Compute lexical relevance score using token matching, exact phrase matches, and filename match."""
    query_lower = query.lower().strip()
    content_lower = content.lower()
    filename_lower = filename.lower()

    if not query_lower:
        return 0.0

    score = 0.0
    # Exact full query match in content or filename gives strong initial boost
    if query_lower in content_lower:
        score += 0.8
    elif query_lower in filename_lower:
        score += 0.6

    # Tokenized word overlap
    query_tokens = [t for t in re.findall(r"\w+", query_lower) if len(t) > 1 or t.isdigit()]
    if not query_tokens:
        return min(score, 1.0)

    matched_tokens = 0
    for token in query_tokens:
        if token in content_lower:
            matched_tokens += 1
            count = min(content_lower.count(token), 5)
            score += 0.08 * count
        if token in filename_lower:
            matched_tokens += 1
            score += 0.2

    token_overlap_ratio = matched_tokens / max(len(query_tokens), 1)
    score += token_overlap_ratio * 0.4

    return min(score, 1.0)


class SemanticRetriever:
    @staticmethod
    async def search(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        query: str,
        top_k: int = 4,
        min_score: float = 0.25
    ) -> List[Dict[str, Any]]:
        """Retrieve most relevant document chunks strictly bounded within workspace_id.
        
        Uses robust hybrid search: dense ONNX vector similarity + lexical keyword matching.
        If vector embedding model loading fails or HuggingFace is unreachable in the environment,
        this seamlessly falls back to high-precision lexical retrieval so search never crashes.
        """
        # 1. Fetch chunks scoped strictly by workspace_id
        stmt = select(DocumentChunk).where(DocumentChunk.workspace_id == workspace_id)
        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return []

        # 2. Attempt dense vector embedding for query with graceful fallback
        query_vector = None
        try:
            query_vector = embedding_service.embed_query(query)
        except Exception as e:
            logger.warning(
                f"Dense vector embedding failed for query '{query}': {e}. "
                "Seamlessly falling back to high-precision lexical retrieval."
            )

        # 3. Score chunks
        scored_chunks = []
        for chunk in chunks:
            filename = (
                chunk.chunk_metadata.get("filename", "Unknown Document")
                if chunk.chunk_metadata
                else "Unknown Document"
            )
            keyword_score = compute_keyword_score(query, chunk.content, filename)

            if query_vector is not None and chunk.embedding:
                try:
                    vec_score = cosine_similarity(query_vector, chunk.embedding)
                except Exception:
                    vec_score = 0.0
                # Hybrid weighted score: 70% vector + 30% lexical
                final_score = (vec_score * 0.7) + (keyword_score * 0.3)
            else:
                final_score = keyword_score

            if final_score >= min_score or keyword_score >= 0.3:
                scored_chunks.append({
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "content": chunk.content,
                    "score": round(final_score, 4),
                    "filename": filename,
                    "page_number": chunk.chunk_metadata.get("page_number", 1) if chunk.chunk_metadata else 1,
                })

        # 4. Sort descending by relevance score
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]
