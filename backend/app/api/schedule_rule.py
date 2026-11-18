from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_admin
from app.models.user import User
from app.services import schedule_rule_service

router = APIRouter(prefix="/schedule-rules", tags=["Weekly schedule rules"])


@router.get("")
def list_rules(
    semester_id: int | None = Query(default=None, gt=0), user_id: int | None = Query(default=None, gt=0),
    page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1, le=100),
    _: User = Depends(get_current_admin), db: Session = Depends(get_db),
):
    return Response.success(data=schedule_rule_service.list_rules(db, semester_id, user_id, page, page_size))


@router.post("/{rule_id}/generate")
def regenerate_rule(rule_id: int, _: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return Response.success(data=schedule_rule_service.regenerate_rule(db, rule_id))
