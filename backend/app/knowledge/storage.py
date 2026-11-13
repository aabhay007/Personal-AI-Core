"""Storage abstraction for document files (Local development / S3 compatible)."""
import os
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

LOCAL_STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "documents"))


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
    """Local filesystem storage driver for development."""

    def __init__(self, base_dir: str = LOCAL_STORAGE_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> str:
        # Sanitize storage key to prevent directory traversal
        sanitized = storage_key.replace("..", "").replace("\\", "/").lstrip("/")
        return os.path.join(self.base_dir, sanitized)

    async def save_file(self, storage_key: str, data: bytes) -> str:
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
