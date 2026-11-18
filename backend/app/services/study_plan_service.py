from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.study_plan import StudyPlan
from app.models.user import User
from app.schemas.study_plan import StudyPlanCreateRequest, StudyPlanResponse
from app.config import STUDY_PLAN_MAX_LENGTH


def list_page_plans(
    db: Session, current_user: User, page: int = 1, page_size: int = 10
) -> PageResponse:
    """List study plans with pagination."""
    query = db.query(StudyPlan).filter(StudyPlan.user_id == current_user.id)
    total = query.count()
    rows = (
        query.order_by(StudyPlan.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[StudyPlanResponse.model_validate(row) for row in rows], total=total
    )


def create_study_plan(
    db: Session, current_user: User, data: StudyPlanCreateRequest
) -> StudyPlanResponse:
    """Create a study plan."""
    if not data.content:
        raise BusinessException(message="Please enter study plan content.")
    if len(data.content) > STUDY_PLAN_MAX_LENGTH:
        raise BusinessException(message=f"Study plan content must not exceed {STUDY_PLAN_MAX_LENGTH}")
    row = StudyPlan(user_id=current_user.id, content=data.content)
    db.add(row)
    db.commit()
    db.refresh(row)
    return StudyPlanResponse.model_validate(row)


def delete_study_plan(db: Session, current_user: User, plan_id: int) -> None:
    """Delete a study plan owned by the current user."""
    row = (
        db.query(StudyPlan)
        .filter(StudyPlan.id == plan_id, StudyPlan.user_id == current_user.id)
        .first()
    )
    if not row:
        raise BusinessException(message="Study plan not found.")
    db.delete(row)
    db.commit()
