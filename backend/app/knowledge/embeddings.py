"""Vector embedding generation service using FastEmbed (BGE-Small-EN)."""
import logging
from typing import List, Optional
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSION = 384


class EmbeddingService:
    """Embedding generator powered by FastEmbed ONNX runtime for local, high-speed execution."""

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self._model: Optional[TextEmbedding] = None

    def _get_model(self) -> TextEmbedding:
        if self._model is None:
            logger.info(f"Loading FastEmbed model '{self.model_name}'...")
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate dense vector embeddings for a list of document chunk texts."""
        if not texts:
            return []
        model = self._get_model()
        # model.embed returns a generator of numpy arrays
        embeddings_gen = model.embed(texts)
        return [embedding.tolist() for embedding in embeddings_gen]

    def embed_query(self, query: str) -> List[float]:
        """Generate dense vector embedding for a search query string."""
        model = self._get_model()
        query_embeddings = list(model.embed([query]))
        return query_embeddings[0].tolist()


# Global embedding service singleton
embedding_service = EmbeddingService()
