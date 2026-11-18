from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_admin
from app.models.user import User
from app.schemas.semester import SemesterRequest
from app.services import semester_service

router = APIRouter(prefix="/semesters", tags=["Semester management"])


@router.get("")
def list_semesters(_: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=semester_service.list_semesters(db))


@router.post("")
def create_semester(data: SemesterRequest, _: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=semester_service.save_semester(db, data))


@router.put("/{semester_id}")
def update_semester(semester_id: int, data: SemesterRequest, _: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=semester_service.save_semester(db, data, semester_id))


@router.delete("/{semester_id}")
def delete_semester(semester_id: int, _: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    semester_service.delete_semester(db, semester_id)
    return Response.success()
