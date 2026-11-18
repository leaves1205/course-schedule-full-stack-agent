from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.models.semester import Semester
from app.models.schedule_rule import ScheduleRule
from app.schemas.semester import SemesterRequest, SemesterResponse
from app.services.schedule_validation import schedule_transaction


def _response(row: Semester, rule_count: int = 0) -> SemesterResponse:
    return SemesterResponse(
        id=row.id, name=row.name, first_monday=row.first_monday, total_weeks=row.total_weeks,
        end_date=row.first_monday + timedelta(weeks=row.total_weeks, days=-1), rule_count=rule_count,
    )


def list_semesters(db: Session) -> list[SemesterResponse]:
    rows = db.query(Semester, func.count(ScheduleRule.id)).outerjoin(
        ScheduleRule, ScheduleRule.semester_id == Semester.id
    ).group_by(Semester.id).order_by(Semester.first_monday.desc()).all()
    return [_response(row, count) for row, count in rows]


def save_semester(db: Session, data: SemesterRequest, semester_id: int | None = None):
    with schedule_transaction(db):
        row = db.scalar(select(Semester).where(Semester.id == semester_id).with_for_update()) if semester_id else None
        if semester_id and not row:
            raise BusinessException("Semester not found.", code=404)
        rules = db.scalars(select(ScheduleRule.id).where(
            ScheduleRule.semester_id == semester_id
        ).with_for_update()).all() if row else []
        if row and rules and (row.first_monday != data.first_monday or row.total_weeks != data.total_weeks):
            raise BusinessException(
                "This semester already has weekly rules. Its start date and week count cannot be changed.", code=409
            )
        duplicate = db.scalar(select(Semester.id).where(Semester.name == data.name))
        if duplicate is not None and duplicate != semester_id:
            raise BusinessException("A semester with this name already exists.", code=409)
        if row is None:
            row = Semester(**data.model_dump())
            db.add(row)
        else:
            for key, value in data.model_dump().items():
                setattr(row, key, value)
        db.flush()
        result = _response(row, len(rules))
    return result


def delete_semester(db: Session, semester_id: int):
    with schedule_transaction(db):
        row = db.scalar(select(Semester).where(Semester.id == semester_id).with_for_update())
        if not row:
            raise BusinessException("Semester not found.", code=404)
        if db.scalars(select(ScheduleRule.id).where(
            ScheduleRule.semester_id == semester_id
        ).with_for_update()).first() is not None:
            raise BusinessException("A semester with saved weekly rules cannot be deleted.", code=409)
        db.delete(row)
