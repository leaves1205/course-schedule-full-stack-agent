from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Semester(Base):
    __tablename__ = "semesters"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    first_monday: Mapped[date] = mapped_column(Date, nullable=False)
    total_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
