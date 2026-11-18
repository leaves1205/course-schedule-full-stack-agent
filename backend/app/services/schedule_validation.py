import re
from contextlib import contextmanager
from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.models.user import User


PERIOD_PATTERN = re.compile(r"^(\d{1,2})(?:\s*[-–—]\s*(\d{1,2}))?$")


def parse_period(value: str) -> tuple[int, int]:
    match = PERIOD_PATTERN.fullmatch(value.strip())
    if not match:
        raise BusinessException("Use a period such as 1-2 or 3, with values between 1 and 30.", code=400)
    start, end = int(match[1]), int(match[2] or match[1])
    if not 1 <= start <= end <= 30:
        raise BusinessException("Periods must be between 1 and 30, with start <= end.", code=400)
    return start, end


def lock_students(db: Session, user_ids: list[int]) -> dict[int, User]:
    """Serialize schedule writes per student, including concurrent generation requests."""
    rows = db.scalars(
        select(User).where(User.id.in_(set(user_ids))).order_by(User.id).with_for_update()
    ).all()
    users = {user.id: user for user in rows}
    for user_id in user_ids:
        if user_id not in users:
            raise BusinessException("Student not found.", code=404)
        if users[user_id].role != "student":
            raise BusinessException("Schedules can only be assigned to students.", code=400)
    return users


@contextmanager
def schedule_transaction(db: Session):
    try:
        yield
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise BusinessException(
            "The schedule changed concurrently or already exists. Refresh and try again.", code=409
        ) from exc
    except Exception:
        db.rollback()
        raise


def check_conflicts(db: Session, candidates: list[dict], exclude_ids: set[int] | None = None):
    """Check the whole batch before saving anything, with inclusive period boundaries."""
    from app.models.schedule import Schedule

    if not candidates:
        return
    existing = db.scalars(select(Schedule).where(
        Schedule.user_id.in_({item["user_id"] for item in candidates}),
        Schedule.class_date.in_({item["class_date"] for item in candidates}),
        Schedule.is_cancelled.is_(False),
    ).with_for_update()).all()
    by_slot: dict[tuple[int, date], list] = {}
    for row in existing:
        if exclude_ids and row.id in exclude_ids:
            continue
        by_slot.setdefault((row.user_id, row.class_date), []).append(row)
    pending: dict[tuple[int, date], list[dict]] = {}
    conflicts = []
    for item in candidates:
        slot = (item["user_id"], item["class_date"])
        for row in by_slot.get(slot, []):
            try:
                start, end = parse_period(row.period)
            except BusinessException:
                # A legacy period that cannot be parsed must be resolved before adding overlapping dates.
                start, end = 1, 30
            if item["start_period"] <= end and start <= item["end_period"]:
                conflicts.append({
                    "date": item["class_date"].isoformat(),
                    "requested_period": f'{item["start_period"]}-{item["end_period"]}',
                    "existing_period": row.period, "schedule_id": row.id,
                    "message": "Conflicts with an existing class.",
                })
        for other in pending.get(slot, []):
            if item["start_period"] <= other["end_period"] and other["start_period"] <= item["end_period"]:
                conflicts.append({
                    "date": item["class_date"].isoformat(),
                    "requested_period": f'{item["start_period"]}-{item["end_period"]}',
                    "existing_period": f'{other["start_period"]}-{other["end_period"]}',
                    "schedule_id": None, "message": "Two rows in this batch overlap.",
                })
        pending.setdefault(slot, []).append(item)
    if conflicts:
        raise BusinessException(
            f"Found {len(conflicts)} period conflicts. No classes were saved.", code=409,
            data={"conflicts": conflicts[:100], "conflict_count": len(conflicts)},
        )
