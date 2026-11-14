"""Vector embedding generation service using FastEmbed (BGE-Small-EN)."""
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSION = 384


def find_local_model_path() -> Optional[str]:
    """Search for locally cached ONNX model files across persistent storage and temp caches."""
    search_dirs = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "fastembed_cache")),
        os.path.join(tempfile.gettempdir(), "fastembed_cache"),
        os.path.expanduser("~/.cache/fastembed"),
        os.path.expanduser("~/.cache/huggingface"),
    ]
    for base in search_dirs:
        if not os.path.isdir(base):
            continue
        for root, _, files in os.walk(base):
            if ("model_optimized.onnx" in files or "model.onnx" in files) and ("tokenizer.json" in files or "config.json" in files):
                logger.info(f"Discovered local embedding model snapshot at: {root}")
                return root
    return None


class EmbeddingService:
    """Embedding generator powered by FastEmbed ONNX runtime for local, high-speed execution."""

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self._model: Optional[TextEmbedding] = None

    def _get_model(self) -> TextEmbedding:
        if self._model is None:
            local_path = find_local_model_path()
            if local_path:
                logger.info(f"Loading FastEmbed model from local path: '{local_path}'...")
                self._model = TextEmbedding(model_name=self.model_name, specific_model_path=local_path)
            else:
                persistent_cache = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..", "storage", "fastembed_cache")
                )
                os.makedirs(persistent_cache, exist_ok=True)
                logger.info(f"Loading FastEmbed model '{self.model_name}' with cache dir '{persistent_cache}'...")
                self._model = TextEmbedding(model_name=self.model_name, cache_dir=persistent_cache)
        return self._model

    def warmup(self) -> None:
        """Pre-load model into memory during server startup."""
        try:
            self._get_model()
            logger.info("FastEmbed embedding model warmed up successfully.")
        except Exception as e:
            logger.warning(f"Could not warm up FastEmbed model: {e}")

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
