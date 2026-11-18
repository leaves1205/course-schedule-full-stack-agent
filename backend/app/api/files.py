import os
import time
from pathlib import Path
import uuid
import shutil
from fastapi import APIRouter, Depends, File, UploadFile

from app.common.exceptions import BusinessException
from app.common.response import Response
from app.config import ALLOWED_EXTENSIONS, BASE_DIR, MAX_FILE_SIZE, UPLOAD_DIR
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.file import FileResponse

router = APIRouter(prefix="/files", tags=["File management"])


@router.post("/upload")
def upload(
    file: UploadFile = File(...), current_user: User = Depends(get_current_user)
):
    """File upload endpoint."""
    if not file.filename:
        raise BusinessException(message="File name cannot be empty.")

    # Original file name, for example avatar.jpg.
    orignal_name = os.path.basename(file.filename)
    # File extension, for example .jpg.
    ext = Path(orignal_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BusinessException(message=f"Unsupported file extension: {ext}")
    # Validate file size.
    if file.size and file.size > MAX_FILE_SIZE:
        raise BusinessException(
            message=f"File size must not exceed {MAX_FILE_SIZE // 1024 // 1024}MB"
        )
    # Generate a unique file name, for example 199323213213_ddadaqwerq.jpg.
    disk_name = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}{ext}"
    # Actual storage path.
    save_path = UPLOAD_DIR / disk_name

    # Write the file in chunks.
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return Response.success(
        data=FileResponse(
            original_name=orignal_name,
            disk_name=disk_name,
            size=file.size,
            url=f"/uploads/{disk_name}",
        )
    )
