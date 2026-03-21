"""
AWS S3 service — covers all major S3 operations.
Uses boto3 wrapped in asyncio.to_thread to avoid blocking the event loop.
Credentials are passed as a dict: {"access_key", "secret_key", "region"}.
"""
import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _client(cred: str):
    """Build a boto3 S3 client from a JSON credential string."""
    import boto3  # lazy import so missing boto3 doesn't break startup
    c = json.loads(cred)
    return boto3.client(
        "s3",
        aws_access_key_id=c["access_key"],
        aws_secret_access_key=c["secret_key"],
        region_name=c.get("region", "us-east-1"),
    )


# ── Objects ───────────────────────────────────────────────────────────────────

async def s3_upload_text(cred: str, params: dict[str, Any]) -> dict:
    """Upload a text string as a file to S3."""
    def _run():
        s3 = _client(cred)
        s3.put_object(
            Bucket=params["bucket"],
            Key=params["key"],
            Body=params["content"].encode("utf-8"),
            ContentType=params.get("content_type", "text/plain"),
        )
        return {"bucket": params["bucket"], "key": params["key"], "status": "uploaded"}
    return await asyncio.to_thread(_run)


async def s3_download_as_text(cred: str, params: dict[str, Any]) -> dict:
    """Download an S3 object and return its content as a string."""
    def _run():
        s3 = _client(cred)
        resp = s3.get_object(Bucket=params["bucket"], Key=params["key"])
        content = resp["Body"].read().decode("utf-8", errors="replace")
        return {
            "bucket": params["bucket"],
            "key": params["key"],
            "content": content,
            "content_type": resp.get("ContentType", ""),
            "size": resp["ContentLength"],
        }
    return await asyncio.to_thread(_run)


async def s3_delete_object(cred: str, params: dict[str, Any]) -> dict:
    """Delete an object from S3."""
    def _run():
        s3 = _client(cred)
        s3.delete_object(Bucket=params["bucket"], Key=params["key"])
        return {"bucket": params["bucket"], "key": params["key"], "status": "deleted"}
    return await asyncio.to_thread(_run)


async def s3_copy_object(cred: str, params: dict[str, Any]) -> dict:
    """Copy an object within S3 (same or different bucket)."""
    def _run():
        s3 = _client(cred)
        copy_source = {"Bucket": params["source_bucket"], "Key": params["source_key"]}
        s3.copy_object(
            CopySource=copy_source,
            Bucket=params["dest_bucket"],
            Key=params["dest_key"],
        )
        return {
            "source": f"{params['source_bucket']}/{params['source_key']}",
            "destination": f"{params['dest_bucket']}/{params['dest_key']}",
            "status": "copied",
        }
    return await asyncio.to_thread(_run)


async def s3_move_object(cred: str, params: dict[str, Any]) -> dict:
    """Move an object (copy + delete source) within S3."""
    await s3_copy_object(cred, params)
    await s3_delete_object(cred, {
        "bucket": params["source_bucket"],
        "key": params["source_key"],
    })
    return {
        "source": f"{params['source_bucket']}/{params['source_key']}",
        "destination": f"{params['dest_bucket']}/{params['dest_key']}",
        "status": "moved",
    }


async def s3_get_object_metadata(cred: str, params: dict[str, Any]) -> dict:
    """Get metadata (size, content-type, ETag, last-modified) for an S3 object."""
    def _run():
        s3 = _client(cred)
        resp = s3.head_object(Bucket=params["bucket"], Key=params["key"])
        return {
            "bucket": params["bucket"],
            "key": params["key"],
            "size": resp.get("ContentLength"),
            "content_type": resp.get("ContentType"),
            "etag": resp.get("ETag"),
            "last_modified": str(resp.get("LastModified", "")),
            "metadata": resp.get("Metadata", {}),
        }
    return await asyncio.to_thread(_run)


# ── Listing ───────────────────────────────────────────────────────────────────

async def s3_list_objects(cred: str, params: dict[str, Any]) -> dict:
    """List objects in a bucket, optionally filtered by prefix."""
    def _run():
        s3 = _client(cred)
        kwargs = {
            "Bucket": params["bucket"],
            "MaxKeys": params.get("max_keys", 100),
        }
        if params.get("prefix"):
            kwargs["Prefix"] = params["prefix"]
        if params.get("delimiter"):
            kwargs["Delimiter"] = params["delimiter"]
        resp = s3.list_objects_v2(**kwargs)
        objects = [
            {"key": o["Key"], "size": o["Size"], "last_modified": str(o["LastModified"])}
            for o in resp.get("Contents", [])
        ]
        return {
            "bucket": params["bucket"],
            "count": resp.get("KeyCount", 0),
            "truncated": resp.get("IsTruncated", False),
            "objects": objects,
        }
    return await asyncio.to_thread(_run)


async def s3_list_buckets(cred: str, params: dict[str, Any]) -> dict:
    """List all S3 buckets in the account."""
    def _run():
        s3 = _client(cred)
        resp = s3.list_buckets()
        buckets = [
            {"name": b["Name"], "created": str(b["CreationDate"])}
            for b in resp.get("Buckets", [])
        ]
        return {"count": len(buckets), "buckets": buckets}
    return await asyncio.to_thread(_run)


# ── Presigned URLs ────────────────────────────────────────────────────────────

async def s3_generate_presigned_url(cred: str, params: dict[str, Any]) -> dict:
    """Generate a presigned GET URL for temporary public access to an object."""
    def _run():
        s3 = _client(cred)
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": params["bucket"], "Key": params["key"]},
            ExpiresIn=params.get("expires_in", 3600),
        )
        return {"url": url, "expires_in": params.get("expires_in", 3600)}
    return await asyncio.to_thread(_run)


async def s3_generate_presigned_post(cred: str, params: dict[str, Any]) -> dict:
    """Generate a presigned POST URL for browser-direct file uploads."""
    def _run():
        s3 = _client(cred)
        result = s3.generate_presigned_post(
            Bucket=params["bucket"],
            Key=params["key"],
            ExpiresIn=params.get("expires_in", 3600),
        )
        return result
    return await asyncio.to_thread(_run)


# ── Bucket Management ─────────────────────────────────────────────────────────

async def s3_create_bucket(cred: str, params: dict[str, Any]) -> dict:
    """Create a new S3 bucket."""
    def _run():
        import json as _json
        c = _json.loads(cred)
        region = c.get("region", "us-east-1")
        s3 = _client(cred)
        kwargs = {"Bucket": params["bucket"]}
        if region != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
        s3.create_bucket(**kwargs)
        return {"bucket": params["bucket"], "region": region, "status": "created"}
    return await asyncio.to_thread(_run)


async def s3_delete_bucket(cred: str, params: dict[str, Any]) -> dict:
    """Delete an S3 bucket (must be empty first)."""
    def _run():
        s3 = _client(cred)
        s3.delete_bucket(Bucket=params["bucket"])
        return {"bucket": params["bucket"], "status": "deleted"}
    return await asyncio.to_thread(_run)


async def s3_get_bucket_location(cred: str, params: dict[str, Any]) -> dict:
    """Get the AWS region where a bucket is located."""
    def _run():
        s3 = _client(cred)
        resp = s3.get_bucket_location(Bucket=params["bucket"])
        region = resp.get("LocationConstraint") or "us-east-1"
        return {"bucket": params["bucket"], "region": region}
    return await asyncio.to_thread(_run)


# ── Access Control ────────────────────────────────────────────────────────────

async def s3_get_object_acl(cred: str, params: dict[str, Any]) -> dict:
    """Get the ACL (access control list) of an S3 object."""
    def _run():
        s3 = _client(cred)
        resp = s3.get_object_acl(Bucket=params["bucket"], Key=params["key"])
        return {
            "bucket": params["bucket"],
            "key": params["key"],
            "owner": resp.get("Owner", {}),
            "grants": resp.get("Grants", []),
        }
    return await asyncio.to_thread(_run)


async def s3_put_object_acl(cred: str, params: dict[str, Any]) -> dict:
    """Set the ACL of an S3 object (private, public-read, etc.)."""
    def _run():
        s3 = _client(cred)
        s3.put_object_acl(
            Bucket=params["bucket"],
            Key=params["key"],
            ACL=params.get("acl", "private"),
        )
        return {"bucket": params["bucket"], "key": params["key"], "acl": params.get("acl", "private")}
    return await asyncio.to_thread(_run)


# ── Versioning ────────────────────────────────────────────────────────────────

async def s3_get_bucket_versioning(cred: str, params: dict[str, Any]) -> dict:
    """Get versioning status of a bucket."""
    def _run():
        s3 = _client(cred)
        resp = s3.get_bucket_versioning(Bucket=params["bucket"])
        return {"bucket": params["bucket"], "status": resp.get("Status", "Disabled")}
    return await asyncio.to_thread(_run)


async def s3_put_bucket_versioning(cred: str, params: dict[str, Any]) -> dict:
    """Enable or suspend versioning on a bucket."""
    def _run():
        status = "Enabled" if params.get("enable", True) else "Suspended"
        s3 = _client(cred)
        s3.put_bucket_versioning(
            Bucket=params["bucket"],
            VersioningConfiguration={"Status": status},
        )
        return {"bucket": params["bucket"], "versioning": status}
    return await asyncio.to_thread(_run)


async def s3_list_object_versions(cred: str, params: dict[str, Any]) -> dict:
    """List all versions of objects in a bucket (or a specific key)."""
    def _run():
        s3 = _client(cred)
        kwargs = {"Bucket": params["bucket"]}
        if params.get("prefix"):
            kwargs["Prefix"] = params["prefix"]
        resp = s3.list_object_versions(**kwargs)
        versions = [
            {
                "key": v["Key"],
                "version_id": v["VersionId"],
                "is_latest": v["IsLatest"],
                "last_modified": str(v["LastModified"]),
                "size": v["Size"],
            }
            for v in resp.get("Versions", [])
        ]
        return {"bucket": params["bucket"], "count": len(versions), "versions": versions}
    return await asyncio.to_thread(_run)


# ── Tags ──────────────────────────────────────────────────────────────────────

async def s3_get_object_tags(cred: str, params: dict[str, Any]) -> dict:
    """Get tags on an S3 object."""
    def _run():
        s3 = _client(cred)
        resp = s3.get_object_tagging(Bucket=params["bucket"], Key=params["key"])
        return {"tags": {t["Key"]: t["Value"] for t in resp.get("TagSet", [])}}
    return await asyncio.to_thread(_run)


async def s3_put_object_tags(cred: str, params: dict[str, Any]) -> dict:
    """Set tags on an S3 object. Provide tags as {key: value} dict."""
    def _run():
        s3 = _client(cred)
        tag_set = [{"Key": k, "Value": v} for k, v in params["tags"].items()]
        s3.put_object_tagging(
            Bucket=params["bucket"],
            Key=params["key"],
            Tagging={"TagSet": tag_set},
        )
        return {"status": "tags updated", "tags": params["tags"]}
    return await asyncio.to_thread(_run)


async def s3_delete_object_tags(cred: str, params: dict[str, Any]) -> dict:
    """Remove all tags from an S3 object."""
    def _run():
        s3 = _client(cred)
        s3.delete_object_tagging(Bucket=params["bucket"], Key=params["key"])
        return {"status": "tags deleted"}
    return await asyncio.to_thread(_run)


# ── Static Website ────────────────────────────────────────────────────────────

async def s3_put_bucket_website(cred: str, params: dict[str, Any]) -> dict:
    """Configure a bucket for static website hosting."""
    def _run():
        s3 = _client(cred)
        s3.put_bucket_website(
            Bucket=params["bucket"],
            WebsiteConfiguration={
                "IndexDocument": {"Suffix": params.get("index_document", "index.html")},
                "ErrorDocument": {"Key": params.get("error_document", "error.html")},
            },
        )
        return {
            "bucket": params["bucket"],
            "website_url": f"http://{params['bucket']}.s3-website.amazonaws.com",
        }
    return await asyncio.to_thread(_run)


async def s3_get_bucket_website(cred: str, params: dict[str, Any]) -> dict:
    """Get the static website configuration of a bucket."""
    def _run():
        s3 = _client(cred)
        resp = s3.get_bucket_website(Bucket=params["bucket"])
        return {
            "index_document": resp.get("IndexDocument", {}).get("Suffix"),
            "error_document": resp.get("ErrorDocument", {}).get("Key"),
        }
    return await asyncio.to_thread(_run)


async def s3_delete_bucket_website(cred: str, params: dict[str, Any]) -> dict:
    """Remove the static website configuration from a bucket."""
    def _run():
        s3 = _client(cred)
        s3.delete_bucket_website(Bucket=params["bucket"])
        return {"bucket": params["bucket"], "status": "website config removed"}
    return await asyncio.to_thread(_run)
