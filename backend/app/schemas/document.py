from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KbDocumentResponse(BaseModel):
    """Document record shared by upload results and document lists."""

    id: int
    original_name: str  # Filename provided at upload, displayed on the page
    disk_name: str  # Filename generated for disk storage to avoid duplicates
    rel_path: str  # Storage path relative to data/kb
    size: int  # File size in bytes
    ext: str  # Lowercase extension, such as .pdf
    create_time: datetime  # Creation time of the document record

    # Allow reading model attributes directly when the list and upload services return ORM records.
    model_config = ConfigDict(from_attributes=True)


class DocumentPreviewResponse(BaseModel):
    """Document metadata and extracted plain text returned by the preview endpoint."""

    id: int
    original_name: str
    ext: str
    text: str  # Plain text extracted from the file for preview on the page
    char_count: int  # Number of characters in text, not the original file's byte count
