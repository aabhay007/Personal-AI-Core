"""Storage abstraction for document files (Local development / S3 compatible)."""
import os
import tempfile
from abc import ABC, abstractmethod
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def is_storage_dir_writable(path: str) -> bool:
    """Test if a path can be created and written to."""
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


def get_default_storage_dir() -> str:
    """Determine a guaranteed writable directory for document binary storage."""
    # 1. Custom env var
    env_dir = os.environ.get("STORAGE_DIR")
    if env_dir and is_storage_dir_writable(env_dir):
        return env_dir

    # 2. Local dev repository storage
    local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "documents"))
    if is_storage_dir_writable(local_dir):
        return local_dir

    # 3. Fallback to system temp directory (read-only filesystem safe)
    fallback = os.path.join(tempfile.gettempdir(), "personal_ai_storage", "documents")
    try:
        os.makedirs(fallback, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create fallback storage dir '{fallback}': {e}")
    return fallback


LOCAL_STORAGE_DIR = get_default_storage_dir()


class StorageService(ABC):
    """Abstract storage interface for persistent document binaries."""

    @abstractmethod
    async def save_file(self, storage_key: str, data: bytes) -> str:
        """Store file bytes and return access key."""
        pass

    @abstractmethod
    async def get_file(self, storage_key: str) -> bytes:
        """Retrieve stored file bytes."""
        pass

    @abstractmethod
    async def delete_file(self, storage_key: str) -> bool:
        """Delete file from storage."""
        pass


class LocalStorageService(StorageService):
    """Local filesystem storage driver for development and serverless fallback."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or get_default_storage_dir()
        try:
            os.makedirs(self.base_dir, exist_ok=True)
        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to create storage dir {self.base_dir}: {e}. Falling back to temp directory.")
            self.base_dir = os.path.join(tempfile.gettempdir(), "personal_ai_storage", "documents")
            os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> str:
        # Sanitize storage key to prevent directory traversal
        sanitized = storage_key.replace("..", "").replace("\\", "/").lstrip("/")
        return os.path.join(self.base_dir, sanitized)

    async def save_file(self, storage_key: str, data: bytes) -> str:
        file_path = self._resolve_path(storage_key)
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        except (OSError, PermissionError):
            self.base_dir = os.path.join(tempfile.gettempdir(), "personal_ai_storage", "documents")
            file_path = self._resolve_path(storage_key)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(data)
        logger.info(f"Saved file to local storage: {file_path}")
        return storage_key

    async def get_file(self, storage_key: str) -> bytes:
        file_path = self._resolve_path(storage_key)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File '{storage_key}' not found in storage.")
        with open(file_path, "rb") as f:
            return f.read()

    async def delete_file(self, storage_key: str) -> bool:
        file_path = self._resolve_path(storage_key)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted file from local storage: {file_path}")
                return True
            except OSError as e:
                logger.error(f"Failed to delete local file {file_path}: {e}")
                return False
        return False


def get_storage_service() -> StorageService:
    """Return configured storage service."""
    return LocalStorageService()
