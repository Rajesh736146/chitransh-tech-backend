"""Cloudflare R2 storage service (S3-compatible)."""

import uuid
import logging
from datetime import datetime
from typing import BinaryIO

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── S3 client configured for Cloudflare R2 ────────────────────────────────────

_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            config=BotoConfig(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
            region_name="auto",
        )
    return _s3_client


class R2StorageService:
    """Service for uploading, downloading, and managing files in Cloudflare R2."""

    def __init__(self):
        self.client = get_s3_client()
        self.bucket = settings.r2_bucket_name

    def upload_file(
        self,
        file: BinaryIO,
        filename: str,
        folder: str = "uploads",
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload a file to R2 and return the object key.

        Args:
            file: File-like object to upload.
            filename: Original filename (used for extension).
            folder: Folder/prefix in the bucket.
            content_type: MIME type of the file.

        Returns:
            The full object key (path) in the bucket.
        """
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        unique_name = f"{uuid.uuid4().hex}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        if ext:
            unique_name = f"{unique_name}.{ext}"

        key = f"{folder}/{unique_name}"

        try:
            self.client.upload_fileobj(
                file,
                self.bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            logger.info(f"Uploaded file to R2: {key}")
            return key
        except ClientError as e:
            logger.error(f"R2 upload failed: {e}")
            raise

    def get_public_url(self, key: str) -> str:
        """
        Get the public URL for an object.
        Requires the bucket to have public access enabled or a custom domain.
        """
        return f"{settings.r2_endpoint_url}/{self.bucket}/{key}"

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generate a presigned URL for temporary access to a private object.

        Args:
            key: Object key in the bucket.
            expires_in: URL expiry time in seconds (default 1 hour).

        Returns:
            Presigned URL string.
        """
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def delete_file(self, key: str) -> bool:
        """
        Delete a file from R2.

        Args:
            key: Object key to delete.

        Returns:
            True if deleted successfully.
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Deleted file from R2: {key}")
            return True
        except ClientError as e:
            logger.error(f"R2 delete failed: {e}")
            raise

    def list_files(self, prefix: str = "", max_keys: int = 100) -> list[dict]:
        """
        List files in a given prefix/folder.

        Returns:
            List of dicts with 'key', 'size', 'last_modified'.
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket, Prefix=prefix, MaxKeys=max_keys
            )
            files = []
            for obj in response.get("Contents", []):
                files.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                    }
                )
            return files
        except ClientError as e:
            logger.error(f"R2 list failed: {e}")
            raise
