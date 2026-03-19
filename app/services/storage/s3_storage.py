"""S3-compatible storage operations for file uploads (AWS S3 or MinIO)."""

import base64
import logging
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)


def _get_s3_client():
    """Create and return an S3 client."""
    settings = get_settings()
    config = {
        "aws_access_key_id": settings.S3_ACCESS_KEY,
        "aws_secret_access_key": settings.S3_SECRET_KEY,
        "region_name": settings.S3_REGION,
    }
    if settings.S3_ENDPOINT_URL:
        config["endpoint_url"] = settings.S3_ENDPOINT_URL
    return boto3.client("s3", **config)


def ensure_bucket_exists() -> None:
    """Ensure the S3 bucket exists, creating it if necessary."""
    settings = get_settings()
    client = _get_s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "404":
            client.create_bucket(
                Bucket=settings.S3_BUCKET_NAME,
                CreateBucketConfiguration={"LocationConstraint": settings.S3_REGION}
                if settings.S3_REGION != "us-east-1"
                else {},
            )
            logger.info("Created S3 bucket: %s", settings.S3_BUCKET_NAME)
        else:
            raise


def _build_s3_path(user_id: UUID, category: str, file_id: UUID, extension: str) -> str:
    """Build the S3 object key path."""
    return f"{category}/{user_id}/{file_id}.{extension}"


def upload_file(
    user_id: UUID,
    category: str,
    file_id: UUID,
    content: bytes,
    extension: str,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Upload a file to S3 storage.

    Args:
        user_id: Owner's user ID
        category: Storage category (datasets, models, documents)
        file_id: Unique file identifier
        content: File content as bytes
        extension: File extension (csv, json, pdf, etc.)
        content_type: MIME type of the file

    Returns:
        The S3 object key (path) for the uploaded file
    """
    settings = get_settings()
    client = _get_s3_client()
    s3_path = _build_s3_path(user_id, category, file_id, extension)

    client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=s3_path,
        Body=content,
        ContentType=content_type,
    )
    logger.info("Uploaded file to S3: %s", s3_path)
    return s3_path


def download_file(s3_path: str) -> bytes:
    """
    Download a file from S3 storage.

    Args:
        s3_path: The S3 object key

    Returns:
        File content as bytes
    """
    settings = get_settings()
    client = _get_s3_client()

    response = client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_path)
    return response["Body"].read()


def delete_file(s3_path: str) -> bool:
    """
    Delete a file from S3 storage.

    Args:
        s3_path: The S3 object key

    Returns:
        True if deleted successfully
    """
    settings = get_settings()
    client = _get_s3_client()

    try:
        client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_path)
        logger.info("Deleted file from S3: %s", s3_path)
        return True
    except ClientError as e:
        logger.error("Failed to delete file from S3: %s - %s", s3_path, e)
        return False


def get_presigned_url(s3_path: str, expires_in: int = 3600) -> str:
    """
    Generate a presigned URL for file download.

    Args:
        s3_path: The S3 object key
        expires_in: URL expiration time in seconds (default 1 hour)

    Returns:
        Presigned URL for downloading the file
    """
    settings = get_settings()
    client = _get_s3_client()

    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": s3_path},
        ExpiresIn=expires_in,
    )


def decode_base64_content(base64_content: str) -> bytes:
    """Decode base64-encoded file content."""
    return base64.b64decode(base64_content)
