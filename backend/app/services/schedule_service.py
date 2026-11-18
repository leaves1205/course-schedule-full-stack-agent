from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.schedule import Schedule
from app.models.user import User
from app.models.course import Course
from app.schemas.schedule import (
    ScheduleCreateRequest,
    ScheduleResponse,
    ScheduleUpdateRequest,
)
from sqlalchemy.orm import Session
from datetime import date


def _to_response(
    row: Schedule,
    username: str,
    user_name: str,
    course_name: str,
) -> ScheduleResponse:
    """Build a response from the schedule record and joined fields."""
    return ScheduleResponse(
        id=row.id,
        user_id=row.user_id,
        username=username,
        user_name=user_name,
        class_date=row.class_date,
        period=row.period,
        course_id=row.course_id,
        course_name=course_name,
        location=row.location,
    )


def _base_query(
    db: Session,
    user_id: int | None,
    class_date: date | None,
) -> Session:
    query = (
        db.query(Schedule, User.username, User.name, Course.name)
        .join(User, Schedule.user_id == User.id)
        .join(Course, Schedule.course_id == Course.id)
    )
    if user_id is not None:
        query = query.filter(Schedule.user_id == user_id)
    if class_date is not None:
        query = query.filter(Schedule.class_date == class_date)
    return query


def list_page_schedules(
    db: Session,
    user_id: int | None,
    class_date: date | None = None,
    page: int = 1,
    page_size: int = 10,
) -> PageResponse:
    """page query for schedules based on user ID and class date."""

    query = _base_query(db, user_id, class_date)
    total = query.count()
    rows = (
        query.order_by(Schedule.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[
            _to_response(
                row, username=username, user_name=user_name, course_name=course_name
            )
            for row, username, user_name, course_name in rows
        ],
        total=total,
    )


def list_schedules(
    db: Session,
    user_id: int | None,
    class_date: date | None = None,
) -> PageResponse:
    """list query for schedules based on user ID and class date."""

    rows = _base_query(db, user_id, class_date).order_by(Schedule.id.desc()).all()
    return PageResponse(
        list=[
            _to_response(
                row=row,
                username=username,
                user_name=user_name,
                course_name=course_name,
            )
            for row, username, user_name, course_name in rows
        ]
    )


def list_schedules_as_dict(
    db: Session,
    user_id: int | None = None,
    date_str: str | None = None,  # YYYY-MM-dd
) -> list[dict]:
    """Return all schedules as dictionaries for MCP tools."""
    date_text = (date_str or "").strip()
    class_date = date.fromisoformat(date_text) if date_text else None
    items = list_schedules(db, user_id, class_date)
    return [
        {
            "date": item.class_date.isoformat(),  # date -> str: YYYY-MM-DD
            "period": item.period,
            "course_id": item.course_id,
            "course_name": item.course_name,
            "location": item.location,
        }
        for item in items.list
    ]


def create_schedule(db: Session, data: ScheduleCreateRequest) -> ScheduleResponse:
    """create a new schedule."""
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise BusinessException(message="User not found")
    if user.role != "student":
        raise BusinessException(message="Only students can create schedules")
    course = db.query(Course).filter(Course.id == data.course_id).first()
    if not course:
        raise BusinessException(message="Course not found")
    row = Schedule(**data.model_dump())  # {} -> key1 = value1, key2 = value2, ...
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(
        row,
        user.username,
        user.name,
        course.name,
    )


def update_schedule(
    db: Session, schedule_id: int, data: ScheduleUpdateRequest
) -> ScheduleResponse:
    """update an existing schedule."""
    row = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not row:
        raise BusinessException(message="Schedule not found")
    payload = data.model_dump(exclude_none=True)
    user_id = payload.get("user_id", row.user_id)
    course_id = payload.get("course_id", row.course_id)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="User not found")
    if user.role != "student":
        raise BusinessException(message="Only students can create schedules")
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise BusinessException(message="Course not found")
    for field, value in payload.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return _to_response(
        row,
        user.username,
        user.name,
        course.name,
    )


def delete_schedule(db: Session, schedule_id: int) -> None:
    """delete an existing schedule."""
    row = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not row:
        raise BusinessException(message="Schedule not found")
    db.delete(row)
    db.commit()
