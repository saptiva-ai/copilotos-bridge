"""
Local storage management for uploaded documents.

Provides streaming write helpers and a background reaper that evicts
files based on age and disk pressure. Designed so it can be swapped
for MinIO/S3 in the future.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import structlog
from fastapi import UploadFile

logger = structlog.get_logger(__name__)


class FileTooLargeError(Exception):
    """Raised when an upload exceeds the configured size limit."""

    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        super().__init__(f"File too large: {size_bytes} > {max_bytes}")
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes


@dataclass(frozen=True)
class StorageConfig:
    root: Path
    ttl_seconds: int
    reap_interval_seconds: int
    max_disk_usage_percent: int


def _default_storage_root() -> Path:
    root_env = os.getenv("DOCUMENTS_STORAGE_ROOT")
    if root_env:
        return Path(root_env).expanduser().resolve()
    return Path(tempfile.gettempdir()) / "copilotos_documents"


DEFAULT_STORAGE_CONFIG = StorageConfig(
    root=_default_storage_root(),
    ttl_seconds=int(os.getenv("DOCUMENTS_TTL_HOURS", "72")) * 3600,
    reap_interval_seconds=int(os.getenv("DOCUMENTS_REAPER_INTERVAL_SECONDS", "900")),
    max_disk_usage_percent=int(os.getenv("DOCUMENTS_MAX_DISK_USAGE_PERCENT", "85")),
)


class Storage:
    """Simple filesystem-based storage backend."""

    def __init__(self, config: StorageConfig = DEFAULT_STORAGE_CONFIG) -> None:
        self.config = config
        self.config.root.mkdir(parents=True, exist_ok=True)
        self._reaper_task: Optional[asyncio.Task] = None
        logger.info(
            "Storage initialised",
            root=str(self.config.root),
            ttl_seconds=self.config.ttl_seconds,
            reap_interval_seconds=self.config.reap_interval_seconds,
            max_disk_usage_percent=self.config.max_disk_usage_percent,
        )

    async def save_upload(
        self,
        doc_id: str,
        upload: UploadFile,
        max_bytes: int,
    ) -> Tuple[Path, str, int]:
        """
        Persist an UploadFile to disk streaming in 1MB chunks.

        Returns the destination path, sanitized filename, and size.
        Raises FileTooLargeError if the stream exceeds max_bytes.
        """
        safe_name = self._sanitize_filename(upload.filename or "document")
        doc_dir = self.config.root / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)

        dest_path = doc_dir / safe_name
        size = 0
        chunk_size = 1024 * 1024

        await upload.seek(0)
        try:
            with dest_path.open("wb") as output:
                while True:
                    chunk = await upload.read(chunk_size)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise FileTooLargeError(size, max_bytes)
                    output.write(chunk)
        except FileTooLargeError:
            self._safe_delete(dest_path)
            self._safe_remove_dir(doc_dir)
            raise
        except Exception as exc:
            self._safe_delete(dest_path)
            self._safe_remove_dir(doc_dir)
            logger.error("Failed to save upload", error=str(exc), doc_id=doc_id)
            raise
        finally:
            await upload.close()

        logger.info("Upload stored", doc_id=doc_id, path=str(dest_path), size_bytes=size)
        return dest_path, safe_name, size

    def delete_document(self, doc_id: str) -> None:
        """Remove all files for a document."""
        doc_dir = self.config.root / doc_id
        if doc_dir.exists():
            shutil.rmtree(doc_dir, ignore_errors=True)
            logger.info("Deleted document directory", doc_id=doc_id, path=str(doc_dir))

    async def start_reaper(self) -> None:
        if self._reaper_task is None and self.config.reap_interval_seconds > 0:
            self._reaper_task = asyncio.create_task(self._reaper_loop(), name="storage-reaper")
            logger.info("Storage reaper started", interval_seconds=self.config.reap_interval_seconds)

    async def stop_reaper(self) -> None:
        if self._reaper_task:
            self._reaper_task.cancel()
            try:
                await self._reaper_task
            except asyncio.CancelledError:
                logger.info("Storage reaper cancelled")
            finally:
                self._reaper_task = None

    async def _reaper_loop(self) -> None:
        """Periodic cleanup loop."""
        try:
            while True:
                await asyncio.sleep(self.config.reap_interval_seconds)
                self.cleanup_expired()
                self._enforce_disk_quota()
        except asyncio.CancelledError:
            logger.debug("Storage reaper stopping")
            raise

    def cleanup_expired(self) -> None:
        """Remove document directories older than TTL."""
        if self.config.ttl_seconds <= 0:
            return

        now = time.time()
        for doc_dir in self.config.root.iterdir():
            if not doc_dir.is_dir():
                continue
            try:
                created_at = doc_dir.stat().st_ctime
            except OSError:
                continue

            if now - created_at >= self.config.ttl_seconds:
                shutil.rmtree(doc_dir, ignore_errors=True)
                logger.info(
                    "Storage TTL eviction",
                    path=str(doc_dir),
                    age_seconds=int(now - created_at),
                )

    def _enforce_disk_quota(self) -> None:
        """Ensure disk usage stays below the configured threshold."""
        try:
            usage = shutil.disk_usage(self.config.root)
        except FileNotFoundError:
            return

        percent_used = (usage.used / usage.total) * 100 if usage.total else 0.0
        if percent_used < self.config.max_disk_usage_percent:
            return

        logger.warning(
            "Disk usage above threshold, evicting oldest documents",
            percent_used=round(percent_used, 2),
            threshold=self.config.max_disk_usage_percent,
        )

        doc_dirs = [
            (dir_path.stat().st_mtime, dir_path)
            for dir_path in self.config.root.iterdir()
            if dir_path.is_dir()
        ]
        doc_dirs.sort()  # Oldest first

        for _, dir_path in doc_dirs:
            shutil.rmtree(dir_path, ignore_errors=True)
            logger.info("Storage quota eviction", path=str(dir_path))
            try:
                usage = shutil.disk_usage(self.config.root)
            except FileNotFoundError:
                break
            percent_used = (usage.used / usage.total) * 100 if usage.total else 0.0
            if percent_used < self.config.max_disk_usage_percent:
                break

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        base = re.sub(r"[^A-Za-z0-9._-]", "_", name)
        return base or "document"

    @staticmethod
    def _safe_delete(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass

    @staticmethod
    def _safe_remove_dir(path: Path) -> None:
        try:
            if path.exists() and not any(path.iterdir()):
                path.rmdir()
        except Exception:
            pass


storage = Storage()
