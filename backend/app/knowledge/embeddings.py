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


def is_directory_writable(path: str) -> bool:
    """Test if a directory can be created and written to."""
    try:
        os.makedirs(path, exist_ok=True)
        test_file = os.path.join(path, f".test_write_{os.getpid()}")
        with open(test_file, "w") as f:
            f.write("ok")
        if os.path.exists(test_file):
            os.remove(test_file)
        return True
    except (OSError, PermissionError):
        return False


def get_writable_cache_dir() -> str:
    """Return a directory that is guaranteed to be writable for FastEmbed models.
    
    In read-only environments (such as AWS Lambda where /var/task is read-only,
    or secured container runtimes), this gracefully falls back to /tmp.
    """
    # 1. Custom environment variable
    custom_env = os.environ.get("FASTEMBED_CACHE_DIR")
    if custom_env and is_directory_writable(custom_env):
        return custom_env

    # 2. Local repository storage (ideal for local development)
    local_storage = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "storage", "fastembed_cache")
    )
    if is_directory_writable(local_storage):
        return local_storage

    # 3. Fallback to system temp directory (guaranteed writable in AWS Lambda / Vercel / Linux)
    temp_dir = os.path.join(tempfile.gettempdir(), "fastembed_cache")
    try:
        os.makedirs(temp_dir, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create temp fastembed cache dir '{temp_dir}': {e}")
    return temp_dir


def find_local_model_path() -> Optional[str]:
    """Search for locally cached ONNX model files across persistent storage, current working dir, and temp caches."""
    search_dirs = [
        os.environ.get("FASTEMBED_CACHE_DIR"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "fastembed_cache")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "fastembed_cache")),
        os.path.abspath(os.path.join(os.getcwd(), "storage", "fastembed_cache")),
        os.path.abspath(os.path.join(os.getcwd(), "backend", "storage", "fastembed_cache")),
        os.path.abspath(os.path.join(os.getcwd(), "..", "backend", "storage", "fastembed_cache")),
        os.path.join(tempfile.gettempdir(), "fastembed_cache"),
        "/tmp/fastembed_cache",
        os.path.expanduser("~/.cache/fastembed"),
        os.path.expanduser("~/.cache/huggingface"),
    ]
    for base in search_dirs:
        if not base or not os.path.isdir(base):
            continue
        try:
            for root, _, files in os.walk(base):
                if ("model_optimized.onnx" in files or "model.onnx" in files) and ("tokenizer.json" in files or "config.json" in files):
                    logger.info(f"Discovered local embedding model snapshot at: {root}")
                    return root
        except Exception as e:
            logger.warning(f"Error inspecting search dir '{base}': {e}")
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
                cache_dir = get_writable_cache_dir()
                logger.info(f"Loading FastEmbed model '{self.model_name}' with cache dir '{cache_dir}'...")
                self._model = TextEmbedding(model_name=self.model_name, cache_dir=cache_dir)
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
