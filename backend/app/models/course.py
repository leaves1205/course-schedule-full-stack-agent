from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from app.database import Base


class Course(Base):
    __tablename__ = "course"
    __table_args__ = {"comment": "Course information table"}

    name: Mapped[str] = mapped_column(String(50), comment="Course name", nullable=False)
    code: Mapped[str] = mapped_column(
        String(50), comment="Course code", unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(
        String(255), comment="Course description", nullable=False
    )
    status: Mapped[int] = mapped_column(default=1, comment="Status: 0 = inactive, 1 = active")
