import os
import time
from pathlib import Path
import uuid
from fastapi import APIRouter, Depends, File, UploadFile

from app.common.exceptions import BusinessException
from app.common.response import Response
from app.config import IMAGE_EXTENSIONS, MAX_UPLOAD_SIZE, UPLOAD_DIR
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.file import FileResponse

router = APIRouter(prefix="/files", tags=["File management"])

CHUNK_SIZE = 64 * 1024


@router.post("/upload")
def upload(
    file: UploadFile = File(...), current_user: User = Depends(get_current_user)
):
    """Upload an avatar image. Uploads are public under /uploads, so only small images are accepted."""
    if not file.filename:
        raise BusinessException(message="File name cannot be empty.")

    # Original file name, for example avatar.jpg.
    original_name = os.path.basename(file.filename)
    # File extension, for example .jpg.
    ext = Path(original_name).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        raise BusinessException(
            message=f"Unsupported file extension: {ext or '(none)'}. Upload a JPG, PNG, GIF or WebP image."
        )
    # Generate a unique file name, for example 199323213213_ddadaqwerq.jpg.
    disk_name = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}{ext}"
    # Actual storage path.
    save_path = UPLOAD_DIR / disk_name

    # The declared size is client-controlled, so enforce the limit on the bytes actually received.
    size = 0
    try:
        with save_path.open("xb") as target:
            while chunk := file.file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > MAX_UPLOAD_SIZE:
                    raise BusinessException(
                        message=f"File size must not exceed {MAX_UPLOAD_SIZE // 1024 // 1024}MB",
                        code=413,
                    )
                target.write(chunk)
        if size == 0:
            raise BusinessException(message="File must not be empty.")
    except Exception:
        # Never leave a partial or rejected upload behind.
        save_path.unlink(missing_ok=True)
        raise

    return Response.success(
        data=FileResponse(
            original_name=original_name,
            disk_name=disk_name,
            size=size,
            url=f"/uploads/{disk_name}",
        )
    )
