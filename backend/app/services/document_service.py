import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.config import KB_DIR, MAX_FILE_SIZE
from app.models.kb_document import KbDocument
from app.schemas.document import KbDocumentResponse
from app.schemas.document import DocumentPreviewResponse
from app.services.rag_service import extract_document_text

logger = logging.getLogger(__name__)
DOC_EXTS = {".txt", ".md", ".pdf", ".docx"}


def list_documents(db: Session) -> list[KbDocumentResponse]:
    rows = db.scalars(select(KbDocument).order_by(KbDocument.id.desc())).all()
    return [KbDocumentResponse.model_validate(row) for row in rows]


def upload_documents(db: Session, files: list[UploadFile]) -> list[KbDocumentResponse]:
    """Commit only after all files in the request succeed; clean up this batch's files on failure."""
    # Reject requests without files because there are no records to save.
    if not files:
        raise BusinessException(message="Please upload at least one file", code=400)

    saved_paths: list[Path] = []  # Paths created in this batch, deleted individually on failure
    rows: list[KbDocument] = []  # Database records added in this batch, converted to response data before commit
    names: set[str] = set()  # Original filenames processed in this batch, used to detect duplicates
    try:
        for upload in files:
            original = Path(upload.filename or "").name
            # Filenames are displayed in the list; empty or overly long names cannot be stored in the table.
            if not original or len(original) > 255:
                raise BusinessException(
                    message="Filename must not be empty or exceed 255 characters", code=400
                )
            ext = Path(original).suffix.lower()
            # The file picker's accept attribute can be bypassed, so the backend still enforces format restrictions.
            if ext not in DOC_EXTS:
                raise BusinessException(
                    message="Only .txt / .md / .pdf / .docx files are supported", code=400
                )
            exists = db.scalar(
                select(KbDocument.id).where(KbDocument.original_name == original)
            )
            # names checks duplicates within this batch; the database query checks previously uploaded filenames.
            if original in names or exists is not None:
                raise BusinessException(message=f"A document with this filename already exists: {original}", code=400)
            names.add(original)

            disk_name = f"{uuid.uuid4().hex}{ext}"
            path = KB_DIR / disk_name
            size = 0
            with path.open("xb") as target:
                # Track only files created in this request so failures do not delete existing documents.
                saved_paths.append(path)
                while True:
                    chunk = upload.file.read(64 * 1024)
                    # An empty byte string marks the end of the file, when writing can stop.
                    if not chunk:
                        break
                    size += len(chunk)
                    # Limit each file by the actual bytes read; the outer handler rolls back the batch if the limit is exceeded.
                    if size > MAX_FILE_SIZE:
                        raise BusinessException(
                            message="Each file must not exceed 100 MiB", code=400
                        )
                    target.write(chunk)
            # Zero-byte files have no document content, so roll back the entire upload batch.
            if size == 0:
                raise BusinessException(message=f"File must not be empty: {original}", code=400)

            row = KbDocument(
                original_name=original,
                disk_name=disk_name,
                rel_path=disk_name,
                size=size,
                ext=ext,
            )
            db.add(row)
            rows.append(row)

        # flush executes INSERTs and retrieves IDs without committing, so the entire batch can still be rolled back.
        db.flush()
        result = [KbDocumentResponse.model_validate(row) for row in rows]
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        for path in saved_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.exception("Failed to clean up file from this upload batch: %s", path)
        # Preserve specific input errors; log disk or database exceptions and return a generic message.
        if isinstance(exc, BusinessException):
            raise
        logger.exception("Batch document upload failed")
        raise BusinessException(message="Upload failed. Please check the backend logs", code=500) from exc


def get_document(db: Session, doc_id: int) -> KbDocument:
    row = db.get(KbDocument, doc_id)
    # Both preview and deletion must first verify that the target record exists.
    if not row:
        raise BusinessException(message="Document not found", code=404)
    return row


def document_path(rel_path: str) -> Path:
    path = (KB_DIR / rel_path).resolve()
    # Allow reading and deleting files only within the document directory; paths must not escape its boundary.
    if not path.is_relative_to(KB_DIR.resolve()):
        raise BusinessException(message="Invalid document path", code=400)
    return path


def delete_document(db: Session, doc_id: int) -> None:
    row = get_document(db, doc_id)
    path = document_path(row.rel_path)
    try:
        # Allow administrators to delete the remaining record even if the original file is missing.
        path.unlink(missing_ok=True)
        db.delete(row)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to delete document, doc_id=%s", doc_id)
        raise BusinessException(message="Deletion failed. Please check the backend logs", code=500) from exc


def preview_document(db: Session, doc_id: int) -> DocumentPreviewResponse:
    row = get_document(db, doc_id)
    text = extract_document_text(document_path(row.rel_path))
    return DocumentPreviewResponse(
        id=row.id,
        original_name=row.original_name,
        ext=row.ext,
        text=text,
        char_count=len(text),
    )
