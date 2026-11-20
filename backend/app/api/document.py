from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_admin
from app.models.user import User
from app.services import document_service

# All routes use the /documents prefix; each endpoint still declares its own administrator authentication dependency.
router = APIRouter(prefix="/documents", tags=["Document management"])


@router.get(
    "",
    summary="List documents",
    description="Administrators can view all course documents, returned in descending ID order.",
)
def list_documents(
    _current_user: Annotated[User, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return Response.success(data=document_service.list_documents(db))


@router.post(
    "",
    summary="Upload documents in a batch",
    description="Administrators can upload multiple documents in one request; if any file fails, the entire batch is rolled back.",
)
def upload_documents(
    files: Annotated[list[UploadFile], File(description="Document files to upload in this batch")],
    _current_user: Annotated[User, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return Response.success(data=document_service.upload_documents(db, files))


@router.delete(
    "/{doc_id}",
    summary="Delete document",
    description="Administrators can delete a document record and its stored file by document ID.",
)
def delete_document(
    doc_id: int,
    _current_user: Annotated[User, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    document_service.delete_document(db, doc_id)
    return Response.success()


@router.get(
    "/{doc_id}/preview",
    summary="Preview document text",
    description="Administrators can extract and view plain text from a document by document ID.",
)
def preview_document(
    doc_id: int,
    _current_user: Annotated[User, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return Response.success(data=document_service.preview_document(db, doc_id))
