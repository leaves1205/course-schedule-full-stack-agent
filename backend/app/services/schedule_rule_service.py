from datetime import timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models import Course, Schedule, ScheduleRule, Semester, User
from app.schemas.schedule_rule import GenerationResponse, ScheduleGenerateRequest, ScheduleRuleResponse, WeeklyMeeting
from app.services.schedule_validation import check_conflicts, lock_students, schedule_transaction


def list_rules(db: Session, semester_id=None, user_id=None, page=1, page_size=10):
    query = db.query(ScheduleRule, Semester.name, User.name, User.username, Course.name).join(
        Semester, Semester.id == ScheduleRule.semester_id
    ).join(User, User.id == ScheduleRule.user_id).join(Course, Course.id == ScheduleRule.course_id)
    if semester_id is not None:
        query = query.filter(ScheduleRule.semester_id == semester_id)
    if user_id is not None:
        query = query.filter(ScheduleRule.user_id == user_id)
    total = query.count()
    rows = query.order_by(ScheduleRule.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    ids = [row.id for row, *_ in rows]
    counts = db.query(
        Schedule.rule_id, func.count(Schedule.id),
        func.sum(case((Schedule.is_exception.is_(True), 1), else_=0)),
        func.sum(case((Schedule.is_cancelled.is_(True), 1), else_=0)),
    ).filter(Schedule.rule_id.in_(ids)).group_by(Schedule.rule_id).all() if ids else []
    totals = {rule_id: (sessions, exceptions, cancelled) for rule_id, sessions, exceptions, cancelled in counts}
    items = []
    for row, semester_name, user_name, username, course_name in rows:
        sessions, exceptions, cancelled = totals.get(row.id, (0, 0, 0))
        items.append(ScheduleRuleResponse(
            **{key: getattr(row, key) for key in (
                "id", "semester_id", "user_id", "course_id", "weekday", "start_week", "end_week",
                "start_period", "end_period", "location",
            )}, semester_name=semester_name, user_name=user_name, username=username, course_name=course_name,
            session_count=sessions, exception_count=exceptions, cancelled_count=cancelled,
        ))
    return PageResponse(list=items, total=total)


def generate_schedules(db: Session, data: ScheduleGenerateRequest) -> GenerationResponse:
    with schedule_transaction(db):
        semester = db.scalar(select(Semester).where(Semester.id == data.semester_id).with_for_update())
        if not semester:
            raise BusinessException("Semester not found.", code=404)
        if data.end_week > semester.total_weeks:
            raise BusinessException("The selected week range exceeds this semester.", code=400)
        slots = [(item.weekday, item.start_period, item.end_period) for item in data.meetings]
        if len(set(slots)) != len(slots):
            raise BusinessException("The same weekday and period range appears more than once. Remove the duplicate row.", code=400)
        lock_students(db, [data.user_id])
        if not db.get(Course, data.course_id):
            raise BusinessException("Course not found.", code=404)
        patterns = db.scalars(select(ScheduleRule).where(
            ScheduleRule.semester_id == data.semester_id, ScheduleRule.user_id == data.user_id,
            ScheduleRule.course_id == data.course_id, ScheduleRule.start_week == data.start_week,
            ScheduleRule.end_week == data.end_week,
        ).with_for_update()).all()
        existing_rules = {(rule.weekday, rule.start_period, rule.end_period): rule for rule in patterns}
        rules = []
        for meeting in data.meetings:
            row = existing_rules.get((meeting.weekday, meeting.start_period, meeting.end_period))
            if row and row.location != meeting.location:
                raise BusinessException("This weekly rule already exists with a different location.", code=409)
            if row is None:
                row = ScheduleRule(
                    semester_id=data.semester_id, user_id=data.user_id, course_id=data.course_id,
                    start_week=data.start_week, end_week=data.end_week, **meeting.model_dump(),
                )
            rules.append(row)
        ids = [rule.id for rule in rules if rule.id is not None]
        existing = db.scalars(select(Schedule).where(Schedule.rule_id.in_(ids)).with_for_update()).all() if ids else []
        saved_slots = {(row.rule_id, row.source_date or row.class_date) for row in existing}
        candidates = []
        preserved = 0
        for rule in rules:
            for week in range(rule.start_week, rule.end_week + 1):
                class_date = semester.first_monday + timedelta(weeks=week - 1, days=rule.weekday - 1)
                if rule.id is not None and (rule.id, class_date) in saved_slots:
                    preserved += 1
                    continue
                candidates.append({
                    "user_id": data.user_id, "class_date": class_date,
                    "start_period": rule.start_period, "end_period": rule.end_period, "rule": rule,
                })
        check_conflicts(db, candidates)
        # All conflicts are checked before inserting any new rules or sessions.
        db.add_all([rule for rule in rules if rule.id is None])
        db.flush()
        for item in candidates:
            rule = item["rule"]
            db.add(Schedule(
                user_id=data.user_id, course_id=data.course_id, rule_id=rule.id,
                class_date=item["class_date"], source_date=item["class_date"],
                start_period=item["start_period"], end_period=item["end_period"],
                period=f'{item["start_period"]}-{item["end_period"]}', location=rule.location,
            ))
        db.flush()
        result = GenerationResponse(created_count=len(candidates), preserved_count=preserved, rule_ids=[rule.id for rule in rules])
    return result


def regenerate_rule(db: Session, rule_id: int):
    rule = db.get(ScheduleRule, rule_id)
    if not rule:
        raise BusinessException("Weekly rule not found.", code=404)
    return generate_schedules(db, ScheduleGenerateRequest(
        semester_id=rule.semester_id, user_id=rule.user_id, course_id=rule.course_id,
        start_week=rule.start_week, end_week=rule.end_week,
        meetings=[WeeklyMeeting(weekday=rule.weekday, start_period=rule.start_period, end_period=rule.end_period, location=rule.location)],
    ))
