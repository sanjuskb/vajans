"""
VAJANS — Storage Abstraction Layer
====================================
Base interface + Local implementation.
Extend with S3StorageBackend when moving to cloud.

All paths in the public API are logical paths (relative to storage root).
Implementations convert to absolute/object paths internally.
"""

from __future__ import annotations

import hashlib
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from app.core.settings import settings


# ---------------------------------------------------------------------------
# Abstract Interface
# ---------------------------------------------------------------------------

class StorageBackend(ABC):
    """
    All storage backends must implement this interface.
    Methods are synchronous; wrap in asyncio.to_thread for async contexts.
    """

    @abstractmethod
    def save(self, logical_path: str, data: bytes | BinaryIO) -> str:
        """
        Persist data at logical_path.
        Returns the resolved storage path (usable for later retrieval).
        """

    @abstractmethod
    def load(self, logical_path: str) -> bytes:
        """Load and return raw bytes from logical_path."""

    @abstractmethod
    def delete(self, logical_path: str) -> None:
        """Remove the object at logical_path."""

    @abstractmethod
    def exists(self, logical_path: str) -> bool:
        """Return True if logical_path exists in storage."""

    @abstractmethod
    def get_url(self, logical_path: str, expiry_seconds: int = 3600) -> str:
        """
        Return a URL from which the object can be retrieved.
        Local: returns a file:// or http:// path.
        S3: returns a presigned URL.
        """

    @staticmethod
    def compute_checksum(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Local Storage
# ---------------------------------------------------------------------------

class LocalStorageBackend(StorageBackend):
    """
    Stores files on the local filesystem under `root_dir`.
    Suitable for development and single-node deployments.
    Replace with S3StorageBackend for production scale.
    """

    def __init__(self, root_dir: str | None = None) -> None:
        self.root = Path(root_dir or settings.STORAGE_LOCAL_PATH).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _abs(self, logical_path: str) -> Path:
        # Prevent path traversal
        resolved = (self.root / logical_path).resolve()
        if not str(resolved).startswith(str(self.root)):
            raise ValueError(f"Path traversal detected: {logical_path}")
        return resolved

    def save(self, logical_path: str, data: bytes | BinaryIO) -> str:
        dest = self._abs(logical_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            dest.write_bytes(data)
        else:
            with dest.open("wb") as f:
                shutil.copyfileobj(data, f)
        return logical_path

    def load(self, logical_path: str) -> bytes:
        return self._abs(logical_path).read_bytes()

    def delete(self, logical_path: str) -> None:
        p = self._abs(logical_path)
        if p.exists():
            p.unlink()

    def exists(self, logical_path: str) -> bool:
        return self._abs(logical_path).exists()

    def get_url(self, logical_path: str, expiry_seconds: int = 3600) -> str:
        # In dev we just return an absolute file path
        return str(self._abs(logical_path))


# ---------------------------------------------------------------------------
# S3 Stub  (ready to implement, not wired up in Phase 0)
# ---------------------------------------------------------------------------

class S3StorageBackend(StorageBackend):
    """
    Stub for AWS S3.  Implement in Phase 8 when moving to cloud storage.
    pip install boto3 to activate.
    """

    def __init__(self) -> None:
        try:
            import boto3  # noqa: F401
        except ImportError:
            raise RuntimeError("boto3 not installed. Run: pip install boto3")
        raise NotImplementedError("S3StorageBackend not yet implemented — see Phase 8.")

    def save(self, logical_path: str, data: bytes | BinaryIO) -> str:  # type: ignore
        raise NotImplementedError

    def load(self, logical_path: str) -> bytes:  # type: ignore
        raise NotImplementedError

    def delete(self, logical_path: str) -> None:  # type: ignore
        raise NotImplementedError

    def exists(self, logical_path: str) -> bool:  # type: ignore
        raise NotImplementedError

    def get_url(self, logical_path: str, expiry_seconds: int = 3600) -> str:  # type: ignore
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_storage() -> StorageBackend:
    backend = settings.STORAGE_BACKEND
    if backend == "local":
        return LocalStorageBackend()
    if backend == "s3":
        return S3StorageBackend()
    raise ValueError(f"Unknown storage backend: {backend!r}")


# Singleton for application lifetime
_storage_instance: StorageBackend | None = None


def storage() -> StorageBackend:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = get_storage()
    return _storage_instance
