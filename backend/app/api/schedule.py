from fastapi import APIRouter, Query, Depends
from datetime import date as Date
from app.common.response import Response
from app.dependencies.auth import get_current_admin, get_current_user
from app.models.user import User
from app.database import get_db
from sqlalchemy.orm import Session
from app.services import schedule_service as schedule_service
from app.schemas.schedule import (
    ScheduleResponse,
    ScheduleCreateRequest,
    ScheduleUpdateRequest,
)
from app.schemas.schedule_rule import ScheduleGenerateRequest
from app.services import schedule_rule_service

router = APIRouter(prefix="/schedules", tags=["Schedule table"])


@router.get("")
def list_page_schedules(
    user_id: int | None = Query(
        default=None, description="only admin using user id filter"
    ),
    date: Date | None = Query(
        default=None, description="filter by date in YYYY-MM-DD format"
    ),
    page: int = Query(default=1, description="page number", ge=1),
    page_size: int = Query(default=10, description="page size", ge=1, le=100),
    semester_id: int | None = Query(default=None, gt=0),
    include_cancelled: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        user_id = current_user.id
        include_cancelled = False
    data = schedule_service.list_page_schedules(db, user_id, date, page, page_size, semester_id, include_cancelled)
    return Response.success(data=data)


@router.post("")
def create_schedule(
    data: ScheduleCreateRequest,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = schedule_service.create_schedule(db, data)
    return Response.success(data=res)


@router.post("/generate")
def generate_schedules(
    data: ScheduleGenerateRequest,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return Response.success(data=schedule_rule_service.generate_schedules(db, data))


@router.post("/{schedule_id}/restore")
def restore_schedule(schedule_id: int, _: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=schedule_service.restore_schedule(db, schedule_id))


@router.put("/{schedule_id}")
def update_schedule(
    schedule_id: int,
    data: ScheduleUpdateRequest,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = schedule_service.update_schedule(db, schedule_id, data)
    return Response.success(data=res)


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    schedule_service.delete_schedule(db, schedule_id)
    return Response.success()
