"""
Supabase Storage abstraction for photo uploads.
"""

import io
import logging
import uuid
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

BUCKET_NAME = "photos"


def _get_supabase_client():
    """Get a Supabase client instance."""
    from supabase import create_client
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


import base64
import os

async def upload_photo(
    image_bytes: bytes,
    original_filename: str,
    site_id: str,
    content_type: str = "image/jpeg",
) -> dict:
    """
    Upload a photo to Supabase Storage, with automatic local fallback if unconfigured.
    """
    ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    storage_key = f"{site_id}/{filename}"

    if is_storage_configured():
        try:
            client = _get_supabase_client()
            try:
                client.storage.create_bucket(
                    BUCKET_NAME,
                    options={"public": True, "file_size_limit": 25 * 1024 * 1024},
                )
            except Exception:
                pass

            client.storage.from_(BUCKET_NAME).upload(
                path=storage_key,
                file=image_bytes,
                file_options={"content-type": content_type},
            )
            public_url = client.storage.from_(BUCKET_NAME).get_public_url(storage_key)
            return {
                "storage_path": f"{BUCKET_NAME}/{storage_key}",
                "public_url": public_url,
            }
        except Exception as e:
            logger.warning(f"Supabase upload failed, falling back to local storage: {e}")

    # Local storage fallback
    local_dir = os.path.join("data", "photos", site_id)
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, filename)
    with open(local_path, "wb") as f:
        f.write(image_bytes)

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    public_url = f"data:{content_type};base64,{b64}"

    return {
        "storage_path": f"local/{storage_key}",
        "public_url": public_url,
    }


async def delete_photo(storage_path: str) -> bool:
    """Delete a photo from Supabase Storage."""
    try:
        client = _get_supabase_client()
        # storage_path is "bucket/key" — split it
        parts = storage_path.split("/", 1)
        if len(parts) != 2:
            return False
        bucket, key = parts
        client.storage.from_(bucket).remove([key])
        return True
    except Exception as e:
        logger.error(f"Photo deletion failed: {e}")
        return False


async def get_photo_bytes(storage_path: str) -> Optional[bytes]:
    """Download photo bytes from Supabase Storage."""
    try:
        client = _get_supabase_client()
        parts = storage_path.split("/", 1)
        if len(parts) != 2:
            return None
        bucket, key = parts
        data = client.storage.from_(bucket).download(key)
        return data
    except Exception as e:
        logger.error(f"Photo download failed: {e}")
        return None


def is_storage_configured() -> bool:
    """Check if Supabase Storage credentials are configured."""
    return bool(settings.supabase_url and settings.supabase_service_role_key)
