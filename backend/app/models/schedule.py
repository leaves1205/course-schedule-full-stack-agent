from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Integer, Date
from app.database import Base
from datetime import date


class Schedule(Base):
    __tablename__ = "schedules"
    __table_args__ = {"comment": "Class schedule table"}

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
