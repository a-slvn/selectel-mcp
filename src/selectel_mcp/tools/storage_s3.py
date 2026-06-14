"""Object storage tools — S3-compatible buckets and objects."""

from __future__ import annotations

import os


def register(mcp, clients) -> None:
    @mcp.tool()
    def list_buckets() -> list[dict]:
        """List S3 buckets (containers) in the object storage."""
        s3 = clients.s3()
        resp = s3.list_buckets()
        return [
            {"name": b["Name"], "created_at": b["CreationDate"].isoformat()}
            for b in resp.get("Buckets", [])
        ]

    @mcp.tool()
    def list_objects(bucket: str, prefix: str = "", max_keys: int = 100) -> dict:
        """List objects in a bucket, optionally filtered by key prefix."""
        s3 = clients.s3()
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=max_keys)
        objects = [
            {
                "key": o["Key"],
                "size_bytes": o["Size"],
                "last_modified": o["LastModified"].isoformat(),
                "storage_class": o.get("StorageClass"),
            }
            for o in resp.get("Contents", [])
        ]
        return {
            "bucket": bucket,
            "prefix": prefix,
            "count": len(objects),
            "is_truncated": resp.get("IsTruncated", False),
            "objects": objects,
        }

    @mcp.tool()
    def create_bucket(bucket: str) -> dict:
        """Create a new S3 bucket."""
        s3 = clients.s3()
        s3.create_bucket(Bucket=bucket)
        return {"bucket": bucket, "status": "created"}

    @mcp.tool()
    def upload_object(bucket: str, key: str, local_path: str) -> dict:
        """Upload a local file to a bucket under the given key."""
        s3 = clients.s3()
        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"No such file: {local_path}")
        s3.upload_file(local_path, bucket, key)
        return {"bucket": bucket, "key": key, "status": "uploaded"}

    @mcp.tool()
    def download_object(bucket: str, key: str, local_path: str) -> dict:
        """Download an object from a bucket to a local file path."""
        s3 = clients.s3()
        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
        s3.download_file(bucket, key, local_path)
        return {"bucket": bucket, "key": key, "local_path": local_path, "status": "downloaded"}

    @mcp.tool()
    def delete_object(bucket: str, key: str, confirm: bool = False) -> dict:
        """Delete an object from a bucket. DESTRUCTIVE — must pass confirm=True."""
        if not confirm:
            return {
                "would_delete": {"bucket": bucket, "key": key},
                "note": "Re-run with confirm=True to actually delete this object.",
            }
        s3 = clients.s3()
        s3.delete_object(Bucket=bucket, Key=key)
        return {"bucket": bucket, "key": key, "status": "deleted"}
