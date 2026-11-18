from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from app.common.response import Response
from app.database import get_db
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.schemas.study_plan import StudyPlanCreateRequest
from app.services import study_plan_service

router = APIRouter(prefix="/study-plans", tags=["study-plans api router"])


@router.get("")
def get_my_page_plans(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = study_plan_service.list_page_plans(db, current_user, page, page_size)

    return Response.success(data=data)


@router.post("")
def create_study_plan(
    data: StudyPlanCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    created_plan = study_plan_service.create_study_plan(db, current_user, data)

    return Response.success(data=created_plan)


@router.delete("/{plan_id}")  # /api/list?user_id = xx. /api/course/
def delete_study_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = study_plan_service.delete_study_plan(db, current_user, plan_id)
    return Response.success()
