import os
import time
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile

# Where uploaded files are stored (served by nginx / Next.js public)
UPLOAD_ROOT = Path("/var/www/rockmartialarts-fe/public/uploads")

ALLOWED_IMAGES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEOS = {"video/mp4", "video/webm"}
ALLOWED_DOCS = {"application/pdf"}

MAX_IMAGE_SIZE = 10 * 1024 * 1024   # 10 MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_DOC_SIZE = 20 * 1024 * 1024     # 20 MB


def _safe_filename(original: str) -> str:
    """Return a filesystem-safe version of the original filename."""
    name = Path(original).stem[:60]
    ext = Path(original).suffix.lower()
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{safe}{ext}"


class UploadController:
    @staticmethod
    async def upload_file(file: UploadFile, current_user: dict):
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        content_type = file.content_type or ""
        filename = file.filename or "file"

        # Determine category and size limit
        if content_type in ALLOWED_IMAGES:
            sub = "images"
            max_size = MAX_IMAGE_SIZE
        elif content_type in ALLOWED_VIDEOS:
            sub = "videos"
            max_size = MAX_VIDEO_SIZE
        elif content_type in ALLOWED_DOCS:
            sub = "documents"
            max_size = MAX_DOC_SIZE
        else:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{content_type}' not allowed. Accepted: images (jpg/png/webp), videos (mp4/webm), documents (pdf)."
            )

        # Read file
        data = await file.read()
        if len(data) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({len(data)/(1024*1024):.1f} MB). Max for {sub}: {max_size/(1024*1024):.0f} MB."
            )

        dest_dir = UPLOAD_ROOT / sub
        dest_dir.mkdir(parents=True, exist_ok=True)

        safe_name = _safe_filename(filename)
        dest_path = dest_dir / safe_name
        dest_path.write_bytes(data)

        file_url = f"/uploads/{sub}/{safe_name}"

        return {
            "message": "File uploaded successfully",
            "file_url": file_url,
            "filename": safe_name,
            "content_type": content_type,
            "size": len(data),
        }
