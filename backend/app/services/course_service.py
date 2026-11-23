from app.models.schedule import Schedule
from app.schemas.course import CourseCreateRequest, CourseResponse, CourseUpdateRequest
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.common.exceptions import BusinessException
from app.models.course import Course


def list_courses(db: Session, keywords: str | None = None) -> list[CourseResponse]:
    """List courses."""
    query = db.query(Course)
    if keywords and keywords.strip():
        kw = f"%{keywords.strip()}%"
        query = query.filter(
            or_(
                Course.name.ilike(kw),
                Course.code.ilike(kw),
                Course.description.ilike(kw),
            )
        )
    rows = query.order_by(Course.id.desc()).all()
    return [CourseResponse.model_validate(row) for row in rows]


def create_course(db: Session, data: CourseCreateRequest) -> CourseResponse:
    """create course"""
    if not data.code.strip():
        raise BusinessException(message="course code is required")
    exist = db.query(Course).filter(Course.code == data.code.strip()).first()
    if exist:
        raise BusinessException(message="course code already exists", code=409)
    course = Course(
        name=data.name.strip(),
        code=data.code.strip(),
        # The description column is NOT NULL, so "no description" is stored as an empty string.
        description=(data.description or "").strip(),
        status=data.status if data.status in (0, 1) else 1,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return CourseResponse.model_validate(course)


def update_course(
    db: Session, course_id: int, data: CourseUpdateRequest
) -> CourseResponse:
    """update course"""
    row = db.query(Course).filter(Course.id == course_id).first()
    if not row:
        raise BusinessException(message="course not found", code=404)
    payload = data.model_dump(exclude_none=True)
    if "name" in payload:
        payload["name"] = payload["name"].strip()
    if "code" in payload:
        code = payload["code"].strip()
        conflict = (
            db.query(Course).filter(Course.code == code, Course.id != course_id).first()
        )
        if conflict:
            raise BusinessException(message="course code already exists", code=409)
        payload["code"] = code
    if "description" in payload:
        payload["description"] = (payload["description"] or "").strip()
    for field, value in payload.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return CourseResponse.model_validate(row)


def delete_course(db: Session, course_id: int) -> None:
    """delete course"""
    row = db.query(Course).filter(Course.id == course_id).first()
    if not row:
        raise BusinessException(message="course not found", code=404)
    linked = db.query(Schedule).filter(Schedule.course_id == course_id).first()
    if linked:
        raise BusinessException(
            message="course is linked to a schedule and cannot be deleted", code=409
        )
    db.delete(row)
    db.commit()
