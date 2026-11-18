from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Integer, Date, Boolean, Index, false
from app.database import Base
from datetime import date


class Schedule(Base):
    __tablename__ = "schedules"
    __table_args__ = (
        Index("uq_schedule_rule_date", "rule_id", "class_date", unique=True),
        Index("uq_schedule_rule_source", "rule_id", "source_date", unique=True),
        Index("ix_schedule_student_date", "user_id", "class_date"),
        {"comment": "Class schedule table"},
    )

    rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("schedule_rules.id", name="fk_schedule_rule"), nullable=True
    )
    # source_date remains unchanged when one occurrence is moved or cancelled.
    source_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_period: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_period: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_exception: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), comment="student ID", nullable=False
    )
    class_date: Mapped[date] = mapped_column(
        Date, comment="course date", nullable=False
    )
    period: Mapped[str] = mapped_column(
        String(50), comment="course period", nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("course.id"), comment="course ID", nullable=False
    )
    location: Mapped[str] = mapped_column(
        String(100), comment="course location", nullable=True
    )
