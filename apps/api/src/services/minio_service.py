"""
MinIO service for document storage and retrieval.
"""

import io
import os
from typing import Optional, BinaryIO
from datetime import timedelta

from minio import Minio
from minio.error import S3Error
import structlog

logger = structlog.get_logger(__name__)


class MinIOService:
    """MinIO client for document storage"""

    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

        # Default buckets
        self.documents_bucket = "documents"
        self.artifacts_bucket = "artifacts"

        # Ensure buckets exist
        self._ensure_buckets()

    def _ensure_buckets(self):
        """Ensure required buckets exist"""
        for bucket in [self.documents_bucket, self.artifacts_bucket]:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info(f"Created MinIO bucket: {bucket}")
            except S3Error as e:
                logger.error(f"Error ensuring bucket {bucket}", error=str(e))

    async def upload_file(
        self,
        bucket: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload file to MinIO.

        Args:
            bucket: Bucket name
            object_name: Object key
            data: File data stream
            length: Data length in bytes
            content_type: MIME type

        Returns:
            Object key
        """
        try:
            self.client.put_object(
                bucket,
                object_name,
                data,
                length,
                content_type=content_type,
            )
            logger.info(f"Uploaded to MinIO", bucket=bucket, key=object_name, size=length)
            return object_name
        except S3Error as e:
            logger.error(f"MinIO upload failed", error=str(e), bucket=bucket, key=object_name)
            raise

    async def download_file(self, bucket: str, object_name: str) -> bytes:
        """
        Download file from MinIO.

        Args:
            bucket: Bucket name
            object_name: Object key

        Returns:
            File bytes
        """
        try:
            response = self.client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            logger.info(f"Downloaded from MinIO", bucket=bucket, key=object_name)
            return data
        except S3Error as e:
            logger.error(f"MinIO download failed", error=str(e), bucket=bucket, key=object_name)
            raise

    def get_presigned_url(
        self,
        bucket: str,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        """
        Get presigned URL for object.

        Args:
            bucket: Bucket name
            object_name: Object key
            expires: Expiration time

        Returns:
            Presigned URL
        """
        try:
            url = self.client.presigned_get_object(bucket, object_name, expires=expires)
            logger.info(f"Generated presigned URL", bucket=bucket, key=object_name)
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL", error=str(e))
            raise

    async def delete_file(self, bucket: str, object_name: str) -> None:
        """
        Delete file from MinIO.

        Args:
            bucket: Bucket name
            object_name: Object key
        """
        try:
            self.client.remove_object(bucket, object_name)
            logger.info(f"Deleted from MinIO", bucket=bucket, key=object_name)
        except S3Error as e:
            logger.error(f"MinIO delete failed", error=str(e), bucket=bucket, key=object_name)
            raise

    def object_exists(self, bucket: str, object_name: str) -> bool:
        """Check if object exists"""
        try:
            self.client.stat_object(bucket, object_name)
            return True
        except S3Error:
            return False


# Singleton instance
minio_service = MinIOService()
