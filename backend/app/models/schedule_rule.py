from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ScheduleRule(Base):
    __tablename__ = "schedule_rules"
    __table_args__ = (
        UniqueConstraint(
            "semester_id", "user_id", "course_id", "weekday", "start_week", "end_week",
            "start_period", "end_period", name="uq_schedule_rule_pattern",
        ),
    )

    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_week: Mapped[int] = mapped_column(Integer, nullable=False)
    end_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_period: Mapped[int] = mapped_column(Integer, nullable=False)
    end_period: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False, default="")
