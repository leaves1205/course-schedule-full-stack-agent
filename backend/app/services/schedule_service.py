from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models import Course, Schedule, ScheduleRule, Semester, User
from app.schemas.schedule import ScheduleCreateRequest, ScheduleResponse, ScheduleUpdateRequest
from app.services.schedule_validation import check_conflicts, lock_students, parse_period, schedule_transaction


def _base_query(db, user_id=None, class_date=None, semester_id=None, include_cancelled=False):
    query = db.query(Schedule, User.username, User.name, Course.name, Semester.id, Semester.name).join(
        User, Schedule.user_id == User.id
    ).join(Course, Schedule.course_id == Course.id).outerjoin(
        ScheduleRule, Schedule.rule_id == ScheduleRule.id
    ).outerjoin(Semester, ScheduleRule.semester_id == Semester.id)
    if user_id is not None:
        query = query.filter(Schedule.user_id == user_id)
    if class_date is not None:
        query = query.filter(Schedule.class_date == class_date)
    if semester_id is not None:
        query = query.filter(Semester.id == semester_id)
    if not include_cancelled:
        query = query.filter(Schedule.is_cancelled.is_(False))
    return query


def _to_response(row, username, user_name, course_name, semester_id=None, semester_name=None):
    return ScheduleResponse(
        **{key: getattr(row, key) for key in (
            "id", "user_id", "class_date", "period", "course_id", "location", "rule_id", "source_date",
            "start_period", "end_period", "is_exception", "is_cancelled",
        )}, username=username, user_name=user_name, course_name=course_name,
        semester_id=semester_id, semester_name=semester_name,
    )


def _response_for_id(db, schedule_id):
    return _to_response(*_base_query(db, include_cancelled=True).filter(Schedule.id == schedule_id).one())


def list_page_schedules(db, user_id, class_date=None, page=1, page_size=10, semester_id=None, include_cancelled=False):
    query = _base_query(db, user_id, class_date, semester_id, include_cancelled)
    total = query.count()
    rows = query.order_by(Schedule.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PageResponse(list=[_to_response(*row) for row in rows], total=total)


def list_schedules(db: Session, user_id: int | None, class_date: date | None = None) -> PageResponse:
    rows = _base_query(db, user_id, class_date).order_by(Schedule.id.desc()).all()
    return PageResponse(list=[_to_response(*row) for row in rows], total=len(rows))


def list_schedules_as_dict(db: Session, user_id: int | None = None, date_str: str | None = None) -> list[dict]:
    """Keep the existing MCP result format and omit cancelled occurrences."""
    date_text = (date_str or "").strip()
    class_date = date.fromisoformat(date_text) if date_text else None
    items = list_schedules(db, user_id, class_date)
    return [{
        "date": item.class_date.isoformat(), "period": item.period,
        "course_id": item.course_id, "course_name": item.course_name, "location": item.location,
    } for item in items.list]


def _course(db, course_id):
    if not db.get(Course, course_id):
        raise BusinessException("Course not found.", code=404)


def create_schedule(db: Session, data: ScheduleCreateRequest) -> ScheduleResponse:
    with schedule_transaction(db):
        lock_students(db, [data.user_id])
        _course(db, data.course_id)
        start, end = parse_period(data.period)
        check_conflicts(db, [{
            "user_id": data.user_id, "class_date": data.class_date, "start_period": start, "end_period": end,
        }])
        row = Schedule(**{**data.model_dump(), "period": f"{start}-{end}"}, start_period=start, end_period=end)
        db.add(row)
        db.flush()
        result = _response_for_id(db, row.id)
    return result


def _lock_schedule(db, schedule_id, target_user_id=None):
    row = db.get(Schedule, schedule_id)
    if not row:
        raise BusinessException("Schedule not found.", code=404)
    original_user = row.user_id
    users = lock_students(db, [original_user, target_user_id or original_user])
    row = db.scalar(select(Schedule).where(Schedule.id == schedule_id).with_for_update().execution_options(populate_existing=True))
    if not row or row.user_id not in users:
        raise BusinessException("The schedule changed. Refresh and try again.", code=409)
    return row


def update_schedule(db: Session, schedule_id: int, data: ScheduleUpdateRequest) -> ScheduleResponse:
    with schedule_transaction(db):
        payload = data.model_dump(exclude_none=True)
        row = _lock_schedule(db, schedule_id, payload.get("user_id"))
        if row.is_cancelled:
            raise BusinessException("Restore this cancelled class before editing it.", code=409)
        if row.rule_id and (payload.get("user_id", row.user_id) != row.user_id or payload.get("course_id", row.course_id) != row.course_id):
            raise BusinessException("A generated class must keep its original student and course.", code=400)
        _course(db, payload.get("course_id", row.course_id))
        start, end = parse_period(payload.get("period", row.period))
        target_date = payload.get("class_date", row.class_date)
        if row.rule_id and db.scalar(select(Schedule.id).where(
            Schedule.rule_id == row.rule_id, Schedule.class_date == target_date,
            Schedule.id != row.id,
        ).with_for_update()) is not None:
            raise BusinessException("This weekly rule already has a class on that date. Choose a different date.", code=409)
        check_conflicts(db, [{
            "user_id": payload.get("user_id", row.user_id),
            "class_date": target_date, "start_period": start, "end_period": end,
        }], exclude_ids={row.id})
        for field, value in payload.items():
            setattr(row, field, value)
        row.period, row.start_period, row.end_period = f"{start}-{end}", start, end
        if row.rule_id:
            row.is_exception = True
        db.flush()
        result = _response_for_id(db, row.id)
    return result


def delete_schedule(db: Session, schedule_id: int) -> None:
    with schedule_transaction(db):
        row = _lock_schedule(db, schedule_id)
        if row.rule_id:
            row.is_cancelled = True
            row.is_exception = True
        else:
            db.delete(row)


def restore_schedule(db: Session, schedule_id: int):
    with schedule_transaction(db):
        row = _lock_schedule(db, schedule_id)
        if not row.is_cancelled:
            raise BusinessException("This class is not cancelled.", code=400)
        start, end = parse_period(row.period)
        check_conflicts(db, [{
            "user_id": row.user_id, "class_date": row.class_date, "start_period": start, "end_period": end,
        }], exclude_ids={row.id})
        row.is_cancelled = False
        row.is_exception = True
        db.flush()
        result = _response_for_id(db, row.id)
    return result
